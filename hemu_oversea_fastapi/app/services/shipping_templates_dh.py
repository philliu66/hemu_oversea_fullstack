"""敦煌运费模板入库（shipping_template_dh）。

策略：按供应商下各敦煌店铺调用 dh.shipping.template.list，边拉边入库并立刻 commit；
同一店铺下已存在的 shipping_temp_id 跳过。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, not_found
from app.core.store_types import StoreType
from app.models.shipping_template_dh import ShippingTemplateDh
from app.models.store import Store
from app.models.supplier import Supplier
from app.services.commerce.multi_store import resolve_stores_by_supplier
from app.services.dhgate.client import DhgateClient
from app.services.dhgate.logistics import list_shipping_templates
from app.services.dhgate.store_context import get_dhgate_client


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_template_row(
    item: dict[str, Any],
    *,
    supplier_id: int,
    store_id: int,
) -> dict[str, Any] | None:
    shipping_temp_id = _as_str(
        item.get("shippingTempId") or item.get("shippingModelId")
    )
    if not shipping_temp_id:
        return None
    return {
        "supplier_id": supplier_id,
        "store_id": store_id,
        "shipping_temp_id": shipping_temp_id,
        "model_name": _as_str(
            item.get("modelName")
            or item.get("shippingModelName")
            or item.get("name")
            or item.get("templateName")
        ),
        "model_desc": _as_str(item.get("modelDesc")),
        "create_date": _as_str(item.get("createDate")),
        "model_type": _as_str(item.get("modelType")),
    }


def _load_existing_temp_ids(db: Session, *, store_id: int) -> set[str]:
    rows = db.scalars(
        select(ShippingTemplateDh.shipping_temp_id).where(
            ShippingTemplateDh.store_id == store_id
        )
    ).all()
    return {str(tid) for tid in rows}


def _insert_one_template(db: Session, row: dict[str, Any]) -> None:
    db.add(ShippingTemplateDh(**row))
    db.commit()


def sync_store_shipping_templates_dh(
    db: Session,
    *,
    store: Store,
    client: DhgateClient | None = None,
) -> dict[str, Any]:
    """单店铺拉取运费模板并边查边入库。"""
    if store.supplier_id is None:
        raise bad_request(f"店铺未绑定供应商：store_id={store.id}")

    dh_client = client or get_dhgate_client(db, store.id)
    existing = _load_existing_temp_ids(db, store_id=store.id)
    inserted = 0
    skipped = 0
    inserted_items: list[dict[str, Any]] = []

    data = list_shipping_templates(dh_client)
    raw_list = data.get("shippingModelList") if isinstance(data, dict) else None
    if not isinstance(raw_list, list):
        raw_list = []

    for raw in raw_list:
        if not isinstance(raw, dict):
            continue
        row = _normalize_template_row(
            raw,
            supplier_id=store.supplier_id,
            store_id=store.id,
        )
        if row is None:
            continue
        temp_id = row["shipping_temp_id"]
        if temp_id in existing:
            skipped += 1
            continue
        _insert_one_template(db, row)
        existing.add(temp_id)
        inserted += 1
        inserted_items.append(raw)

    return {
        "store_id": store.id,
        "store_name": store.name,
        "inserted": inserted,
        "skipped": skipped,
        "total_in_db": len(existing),
        "list": inserted_items,
        "count": len(inserted_items),
    }


def sync_supplier_shipping_templates_dh(
    db: Session,
    *,
    supplier_id: int,
) -> dict[str, Any]:
    """
    按供应商同步其下全部已授权敦煌店铺的运费模板。

    单店失败不中断其余店铺。
    """
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
    errors: list[dict[str, Any]] = []
    inserted_total = 0
    skipped_total = 0

    for store in stores:
        try:
            result = sync_store_shipping_templates_dh(db, store=store)
            store_results.append(result)
            inserted_total += int(result.get("inserted") or 0)
            skipped_total += int(result.get("skipped") or 0)
        except Exception as exc:  # noqa: BLE001 — 联调汇总单店失败
            message = getattr(exc, "message", None) or str(exc)
            errors.append(
                {
                    "store_id": store.id,
                    "store_name": store.name,
                    "message": message,
                }
            )

    return {
        "supplier_id": supplier_id,
        "store_count": len(stores),
        "success_store_count": len(store_results),
        "fail_store_count": len(errors),
        "inserted": inserted_total,
        "skipped": skipped_total,
        "stores": store_results,
        "errors": errors,
    }
