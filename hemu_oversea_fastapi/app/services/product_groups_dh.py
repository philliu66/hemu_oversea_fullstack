"""敦煌产品分组入库（product_group_dh）。

策略：按供应商下各敦煌店铺调用 dh.item.group.list，边拉边入库并立刻 commit；
同一店铺下已存在的 group_id 跳过。含子分组时扁平化写入，parent_group_id 记录层级。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, not_found
from app.core.store_types import StoreType
from app.models.product_group_dh import ProductGroupDh
from app.models.store import Store
from app.models.supplier import Supplier
from app.services.commerce.multi_store import resolve_stores_by_supplier
from app.services.dhgate.client import DhgateClient
from app.services.dhgate.items import list_item_groups
from app.services.dhgate.store_context import get_dhgate_client

_PAGE_SIZE = 200
_MAX_PAGES = 100


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_int(value: Any) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _normalize_group_row(
    item: dict[str, Any],
    *,
    supplier_id: int,
    store_id: int,
    parent_group_id: str | None = None,
) -> dict[str, Any] | None:
    group_id = _as_str(item.get("groupId"))
    if not group_id:
        return None
    parent = parent_group_id or _as_str(item.get("parentGroupId"))
    show = item.get("showInStore")
    return {
        "supplier_id": supplier_id,
        "store_id": store_id,
        "group_id": group_id,
        "parent_group_id": parent,
        # 官方文档筛选参数用 groupCnName；列表项常见 groupName / groupCnName 两种
        "group_name": _as_str(item.get("groupName"))
        or _as_str(item.get("groupCnName")),
        "group_en_name": _as_str(item.get("groupEnName")),
        "remark": _as_str(item.get("remark")),
        "item_count": _as_int(item.get("itemCount")),
        "show_in_store": None if show is None else str(show).strip(),
        "update_date": _as_str(item.get("updateDate")),
    }


def _load_existing_group_ids(db: Session, *, store_id: int) -> set[str]:
    rows = db.scalars(
        select(ProductGroupDh.group_id).where(ProductGroupDh.store_id == store_id)
    ).all()
    return {str(gid) for gid in rows}


def _insert_one_group(db: Session, row: dict[str, Any]) -> None:
    db.add(ProductGroupDh(**row))
    db.commit()


def _walk_and_insert(
    db: Session,
    *,
    supplier_id: int,
    store_id: int,
    items: list[Any],
    existing: set[str],
    parent_group_id: str | None = None,
) -> tuple[int, int, list[dict[str, Any]]]:
    inserted = 0
    skipped = 0
    inserted_items: list[dict[str, Any]] = []

    for raw in items:
        if not isinstance(raw, dict):
            continue
        row = _normalize_group_row(
            raw,
            supplier_id=supplier_id,
            store_id=store_id,
            parent_group_id=parent_group_id,
        )
        if row is None:
            continue
        group_id = row["group_id"]
        if group_id in existing:
            skipped += 1
        else:
            _insert_one_group(db, row)
            existing.add(group_id)
            inserted += 1
            inserted_items.append(raw)

        children = raw.get("itemChildGroupList")
        if isinstance(children, list) and children:
            child_inserted, child_skipped, child_items = _walk_and_insert(
                db,
                supplier_id=supplier_id,
                store_id=store_id,
                items=children,
                existing=existing,
                parent_group_id=group_id,
            )
            inserted += child_inserted
            skipped += child_skipped
            inserted_items.extend(child_items)

    return inserted, skipped, inserted_items


def sync_store_product_groups_dh(
    db: Session,
    *,
    store: Store,
    client: DhgateClient | None = None,
) -> dict[str, Any]:
    """单店铺拉取产品分组并边查边入库。"""
    if store.supplier_id is None:
        raise bad_request(f"店铺未绑定供应商：store_id={store.id}")

    dh_client = client or get_dhgate_client(db, store.id)
    existing = _load_existing_group_ids(db, store_id=store.id)
    inserted = 0
    skipped = 0
    inserted_items: list[dict[str, Any]] = []
    pages = 0

    page = 1
    while page <= _MAX_PAGES:
        data = list_item_groups(
            dh_client,
            page_no=page,
            page_size=_PAGE_SIZE,
            contain_child_group=True,
        )
        pages += 1
        raw_list = data.get("itemGroupList") if isinstance(data, dict) else None
        if not isinstance(raw_list, list) or not raw_list:
            break

        page_inserted, page_skipped, page_items = _walk_and_insert(
            db,
            supplier_id=store.supplier_id,
            store_id=store.id,
            items=raw_list,
            existing=existing,
        )
        inserted += page_inserted
        skipped += page_skipped
        inserted_items.extend(page_items)

        page_total = _as_int(data.get("pageTotal")) if isinstance(data, dict) else 0
        if page_total and page >= page_total:
            break
        if len(raw_list) < _PAGE_SIZE:
            break
        page += 1

    return {
        "store_id": store.id,
        "store_name": store.name,
        "inserted": inserted,
        "skipped": skipped,
        "pages": pages,
        "total_in_db": len(existing),
        "list": inserted_items,
        "count": len(inserted_items),
    }


def sync_supplier_product_groups_dh(
    db: Session,
    *,
    supplier_id: int,
) -> dict[str, Any]:
    """按供应商同步其下全部已授权敦煌店铺的产品分组。任一店铺敦煌调用失败则整次失败。"""
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise not_found("供应商不存在")

    stores = resolve_stores_by_supplier(
        db,
        supplier_id=supplier_id,
        store_type=StoreType.DHGATE,
        require_oauth=True,
    )
    if not stores:
        raise bad_request("该供应商下没有已授权的敦煌店铺")

    store_results: list[dict[str, Any]] = []
    inserted_total = 0
    skipped_total = 0

    for store in stores:
        result = sync_store_product_groups_dh(db, store=store)
        store_results.append(result)
        inserted_total += int(result.get("inserted") or 0)
        skipped_total += int(result.get("skipped") or 0)

    return {
        "supplier_id": supplier_id,
        "store_count": len(stores),
        "success_store_count": len(store_results),
        "fail_store_count": 0,
        "inserted": inserted_total,
        "skipped": skipped_total,
        "stores": store_results,
        "errors": [],
    }
