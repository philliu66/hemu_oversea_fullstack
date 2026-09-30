"""敦煌计件单位入库（measures_unit_dh）。

策略：调用 dh.base.measures.get，清空本地表后全量写入最新数据。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.measures_unit_dh import MeasuresUnitDh
from app.schemas.product import DhMeasuresUnitPublic
from app.services.dhgate.base import list_measures
from app.services.dhgate.client import DhgateClient
from app.services.dhgate.store_context import get_dhgate_client


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_measure_row(item: dict[str, Any]) -> dict[str, Any] | None:
    measure_id = _as_str(item.get("measureid") or item.get("measureId"))
    if not measure_id:
        return None
    return {
        "measure_id": measure_id,
        "name": _as_str(item.get("name")),
        "description": _as_str(item.get("description")),
        "valid": _as_str(item.get("valid")),
        "cname": _as_str(item.get("cname")),
        "short_name": _as_str(item.get("shortname") or item.get("shortName")),
        "plural": _as_str(item.get("plural")),
    }


def _to_public(row: MeasuresUnitDh) -> DhMeasuresUnitPublic:
    return DhMeasuresUnitPublic(
        measure_id=row.measure_id,
        name=row.name,
        description=row.description,
        valid=row.valid,
        cname=row.cname,
        short_name=row.short_name,
        plural=row.plural,
    )


def sync_measures_units_dh(
    db: Session,
    *,
    store_id: int,
    client: DhgateClient | None = None,
) -> dict[str, Any]:
    """
    拉取敦煌计件单位并全量覆盖本地 measures_unit_dh。

    每次调用先清空再写入，保证与平台最新列表一致。
    """
    dh_client = client or get_dhgate_client(db, store_id)
    data = list_measures(dh_client)
    raw_list = data.get("meauserList") if isinstance(data, dict) else None
    if not isinstance(raw_list, list):
        # 容错：若平台拼写修正为 measureList
        raw_list = data.get("measureList") if isinstance(data, dict) else None
    if not isinstance(raw_list, list):
        raw_list = []

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_list:
        if not isinstance(raw, dict):
            continue
        row = _normalize_measure_row(raw)
        if row is None:
            continue
        measure_id = row["measure_id"]
        if measure_id in seen:
            continue
        seen.add(measure_id)
        rows.append(row)

    db.execute(delete(MeasuresUnitDh))
    for row in rows:
        db.add(MeasuresUnitDh(**row))
    db.commit()

    return {
        "count": len(rows),
        "list": [
            DhMeasuresUnitPublic(
                measure_id=item["measure_id"],
                name=item.get("name"),
                description=item.get("description"),
                valid=item.get("valid"),
                cname=item.get("cname"),
                short_name=item.get("short_name"),
                plural=item.get("plural"),
            )
            for item in rows
        ],
    }


def list_measures_units_dh(
    db: Session,
    *,
    valid_only: bool = True,
) -> list[DhMeasuresUnitPublic]:
    """查询本地计件单位列表。"""
    stmt = select(MeasuresUnitDh).order_by(MeasuresUnitDh.id.asc())
    if valid_only:
        stmt = stmt.where(MeasuresUnitDh.valid == "1")
    rows = db.scalars(stmt).all()
    return [_to_public(row) for row in rows]
