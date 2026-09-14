"""敦煌发布类目入库（product_category_dh）。

策略：每拉到一个新类目立即入库并 commit；已存在的 cate_pub_id 直接跳过（不再下钻）。
中断后重跑可续传；若某非叶子已入库但子类未拉完，需删掉该条父类目后再跑，或清空后重同步。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product_category_dh import ProductCategoryDh
from app.services.dhgate.categories import list_child_categories
from app.services.dhgate.client import DhgateClient
from app.services.dhgate.store_context import get_dhgate_client


def _normalize_category_row(item: dict[str, Any]) -> dict[str, Any] | None:
    cate_pub_id = str(item.get("catePubId") or "").strip()
    if not cate_pub_id:
        return None
    leaf = str(item.get("leaf") if item.get("leaf") is not None else "").strip()
    if leaf == "":
        leaf = "0"
    pub_name = str(item.get("pubName") or "").strip()
    pub_name_cn = item.get("pubNameCn")
    remark = item.get("remark")
    pare = item.get("pareCatePubId")
    return {
        "cate_pub_id": cate_pub_id,
        "pub_name": pub_name or cate_pub_id,
        "pub_name_cn": None if pub_name_cn is None else str(pub_name_cn),
        "remark": None if remark is None else str(remark),
        "leaf": leaf,
        "pare_cate_pub_id": None if pare is None else str(pare),
    }


def _load_existing_cate_pub_ids(db: Session) -> set[str]:
    rows = db.scalars(select(ProductCategoryDh.cate_pub_id)).all()
    return {str(cid) for cid in rows}


def _insert_one_category(db: Session, row: dict[str, Any]) -> None:
    db.add(
        ProductCategoryDh(
            cate_pub_id=row["cate_pub_id"],
            pub_name=row["pub_name"],
            pub_name_cn=row["pub_name_cn"],
            remark=row["remark"],
            leaf=row["leaf"],
            pare_cate_pub_id=row["pare_cate_pub_id"],
        )
    )
    db.commit()


def sync_product_categories_dh(
    db: Session,
    *,
    store_id: int,
    client: DhgateClient | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    边拉边入库：新类目立刻 commit；库中已存在的类目跳过（含不再递归其子类）。

    返回 (本次新入库的类目列表, 统计)。
    """
    dh_client = client or get_dhgate_client(db, store_id)
    existing = _load_existing_cate_pub_ids(db)
    inserted_items: list[dict[str, Any]] = []
    inserted = 0
    skipped = 0

    def walk(parent_id: str | None) -> None:
        nonlocal inserted, skipped
        children = list_child_categories(dh_client, parent_id=parent_id)
        for item in children:
            row = _normalize_category_row(item)
            if row is None:
                continue
            cate_id = row["cate_pub_id"]

            if cate_id in existing:
                skipped += 1
                continue

            _insert_one_category(db, row)
            existing.add(cate_id)
            inserted += 1
            inserted_items.append(item)

            if row["leaf"] == "1":
                continue
            walk(cate_id)

    walk(None)
    return inserted_items, {
        "inserted": inserted,
        "skipped": skipped,
        "total_in_db": len(existing),
    }
