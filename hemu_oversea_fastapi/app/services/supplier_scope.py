"""平台 / 供应商角色统一的供应商作用域解析。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import ColumnElement

from app.core.errors import bad_request, forbidden
from app.core.roles import Role
from app.models.supplier import Supplier
from app.models.user import User

PLATFORM_ROLES = frozenset(
    {Role.PLATFORM_ADMIN.value, Role.PLATFORM_STAFF.value}
)
SUPPLIER_PORTAL_ROLES = frozenset(
    {Role.SUPPLIER_ADMIN.value, Role.SUPPLIER_STAFF.value}
)


def is_platform_role(role: str | None) -> bool:
    return role in PLATFORM_ROLES


def is_supplier_portal_role(role: str | None) -> bool:
    return role in SUPPLIER_PORTAL_ROLES


def accessible_supplier_filters(actor: User) -> list[ColumnElement[bool]]:
    """供应商列表 / options 的可见范围过滤条件（不含 deleted_at）。"""
    if actor.role == Role.PLATFORM_ADMIN.value:
        return []
    if actor.role == Role.PLATFORM_STAFF.value:
        return [Supplier.created_by == actor.id]
    raise forbidden()


def assert_supplier_accessible(
    db: Session,
    actor: User,
    supplier_id: int,
) -> Supplier:
    """校验供应商存在且对当前平台账号可见；返回存活供应商。"""
    supplier = db.scalar(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.deleted_at.is_(None),
        )
    )
    if supplier is None:
        raise bad_request("供应商不存在")
    if actor.role == Role.PLATFORM_ADMIN.value:
        return supplier
    if actor.role == Role.PLATFORM_STAFF.value:
        if supplier.created_by != actor.id:
            raise forbidden("无权访问该供应商")
        return supplier
    raise forbidden()


def resolve_supplier_id(
    db: Session,
    actor: User,
    supplier_id: int | None,
) -> int:
    """
    解析业务接口使用的供应商 ID。

    - 供应商门户：强制用账号绑定的 supplier_id，忽略入参
    - 平台门户：必须传入 supplier_id，并校验归属（admin 全部，staff 仅自己创建）
    """
    if actor.role in SUPPLIER_PORTAL_ROLES:
        if actor.supplier_id is None:
            raise bad_request("当前账号未绑定供应商")
        return actor.supplier_id
    if actor.role in PLATFORM_ROLES:
        if supplier_id is None:
            raise bad_request("请指定供应商")
        assert_supplier_accessible(db, actor, supplier_id)
        return supplier_id
    raise forbidden()
