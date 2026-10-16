"""供应商每日店铺巡检设置 CRUD。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, not_found
from app.models.supplier_inspection_schedule import SupplierInspectionSchedule
from app.models.user import User
from app.schemas.supplier_inspection_schedule import (
    ALLOWED_QUERY_DAYS,
    SupplierInspectionSchedulePublic,
)
from app.services.supplier_scope import (
    assert_supplier_data_writable,
    resolve_supplier_id,
)


def to_public(row: SupplierInspectionSchedule) -> SupplierInspectionSchedulePublic:
    return SupplierInspectionSchedulePublic.model_validate(row)


def get_schedule(
    db: Session,
    *,
    actor: User,
    supplier_id: int | None,
) -> SupplierInspectionSchedulePublic | None:
    """读取当前作用域供应商的巡检设置；未配置时返回 None。"""
    sid = resolve_supplier_id(db, actor, supplier_id)
    row = db.scalar(
        select(SupplierInspectionSchedule).where(
            SupplierInspectionSchedule.supplier_id == sid
        )
    )
    if row is None:
        return None
    return to_public(row)


def save_schedule(
    db: Session,
    *,
    actor: User,
    supplier_id: int | None,
    query_days: int,
    emails: str,
) -> SupplierInspectionSchedulePublic:
    """新建或更新巡检设置（按 supplier_id upsert）。"""
    assert_supplier_data_writable(actor)
    sid = resolve_supplier_id(db, actor, supplier_id)
    if query_days not in ALLOWED_QUERY_DAYS:
        raise bad_request("巡检天数仅允许 3 / 7 / 10")

    row = db.scalar(
        select(SupplierInspectionSchedule).where(
            SupplierInspectionSchedule.supplier_id == sid
        )
    )
    if row is None:
        row = SupplierInspectionSchedule(
            supplier_id=sid,
            query_days=query_days,
            emails=emails,
        )
        db.add(row)
    else:
        row.query_days = query_days
        row.emails = emails
    db.commit()
    db.refresh(row)
    return to_public(row)


def delete_schedule(
    db: Session,
    *,
    actor: User,
    supplier_id: int | None,
) -> None:
    """删除当前作用域供应商的巡检设置。"""
    assert_supplier_data_writable(actor)
    sid = resolve_supplier_id(db, actor, supplier_id)
    row = db.scalar(
        select(SupplierInspectionSchedule).where(
            SupplierInspectionSchedule.supplier_id == sid
        )
    )
    if row is None:
        raise not_found("未配置每日巡检，无需删除")
    db.delete(row)
    db.commit()
