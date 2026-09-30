"""敦煌类目佣金率入库（commissions_rate_dh）。

策略：调用 dh.categorys.commissions，清空本地表后按类目全量写入最新数据。
佣金率跟类目走，不绑定店铺；store_id 仅用于取 access_token。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.models.commission_rate_dh import CommissionRateDh
from app.schemas.product import DhCommissionRatePublic, DhCommissionUnitPublic
from app.services.dhgate.categories import list_category_commissions
from app.services.dhgate.client import DhgateClient
from app.services.dhgate.store_context import get_dhgate_client


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes"}:
        return True
    if text in {"0", "false", "no"}:
        return False
    return None


def _normalize_unit(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "left_bound": _as_str(item.get("leftBound")),
        "right_bound": _as_str(item.get("rightBound")),
        "left_bound_close": _as_bool(item.get("leftBoundClose")),
        "right_bound_close": _as_bool(item.get("rightBoundClose")),
        "commission_rate": _as_str(item.get("commissionRate")),
    }


def _normalize_rate_row(item: dict[str, Any]) -> dict[str, Any] | None:
    cate_id = _as_str(item.get("cateId"))
    if not cate_id:
        return None
    raw_units = item.get("unitList")
    units: list[dict[str, Any]] = []
    if isinstance(raw_units, list):
        for unit in raw_units:
            if isinstance(unit, dict):
                units.append(_normalize_unit(unit))
    return {
        "cate_id": cate_id,
        "unit_list": units,
    }


def _to_public(row: CommissionRateDh) -> DhCommissionRatePublic:
    units: list[DhCommissionUnitPublic] = []
    raw_units = row.unit_list if isinstance(row.unit_list, list) else []
    for unit in raw_units:
        if not isinstance(unit, dict):
            continue
        units.append(
            DhCommissionUnitPublic(
                left_bound=unit.get("left_bound"),
                right_bound=unit.get("right_bound"),
                left_bound_close=unit.get("left_bound_close"),
                right_bound_close=unit.get("right_bound_close"),
                commission_rate=unit.get("commission_rate"),
            )
        )
    return DhCommissionRatePublic(cate_id=row.cate_id, unit_list=units)


def sync_commission_rates_dh(
    db: Session,
    *,
    store_id: int,
    client: DhgateClient | None = None,
) -> dict[str, Any]:
    """
    拉取全部类目佣金率并全量覆盖本地 commissions_rate_dh。

    store_id 仅用于敦煌授权；数据按 cate_id 全局存储，不按店铺隔离。
    """
    dh_client = client or get_dhgate_client(db, store_id)
    data = list_category_commissions(dh_client)
    raw_list = data.get("list") if isinstance(data, dict) else None
    if not isinstance(raw_list, list):
        raw_list = []

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_list:
        if not isinstance(raw, dict):
            continue
        row = _normalize_rate_row(raw)
        if row is None:
            continue
        cate_id = row["cate_id"]
        if cate_id in seen:
            continue
        seen.add(cate_id)
        rows.append(row)

    db.execute(delete(CommissionRateDh))
    for row in rows:
        db.add(CommissionRateDh(**row))
    db.commit()

    return {
        "count": len(rows),
        "list": [
            DhCommissionRatePublic(
                cate_id=item["cate_id"],
                unit_list=[
                    DhCommissionUnitPublic(**unit)
                    for unit in (item.get("unit_list") or [])
                ],
            )
            for item in rows
        ],
    }


def get_commission_rate_by_cate_id(
    db: Session,
    *,
    cate_id: str,
) -> DhCommissionRatePublic:
    """按类目 ID 查询本地佣金率。"""
    cate = (cate_id or "").strip()
    if not cate:
        raise not_found("类目佣金率不存在")
    row = db.scalars(
        select(CommissionRateDh).where(CommissionRateDh.cate_id == cate)
    ).first()
    if row is None:
        raise not_found("类目佣金率不存在")
    return _to_public(row)
