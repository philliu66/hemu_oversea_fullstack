from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import Pagination
from app.core.errors import conflict, forbidden, not_found
from app.core.roles import Role as PortalRole
from app.models.permission import BizRole, RolePermission, UserRole
from app.models.user import User
from app.schemas.common import PageData
from app.schemas.permission import RolePublic
from app.services import permissions as perm_service


def _conflict_name(exc: IntegrityError) -> Exception:
    return conflict("角色名称已存在")


def _get_alive_role(
    db: Session,
    role_id: int,
    *,
    supplier_id: int | None,
) -> BizRole:
    role = db.get(BizRole, role_id)
    if role is None or role.is_deleted:
        raise not_found("角色不存在")
    if supplier_id is None:
        if role.supplier_id is not None:
            raise not_found("角色不存在")
    elif role.supplier_id != supplier_id:
        raise not_found("角色不存在")
    return role


def _to_public(db: Session, role: BizRole) -> RolePublic:
    data = RolePublic.model_validate(role)
    data.permission_codes = perm_service.list_role_permission_codes(db, role.id)
    return data


def _assert_can_assign_codes(
    db: Session,
    actor: User,
    codes: list[str],
    *,
    supplier_id: int | None,
) -> None:
    grantable = perm_service.actor_grantable_codes(db, actor)
    perm_service.assert_codes_subset(grantable, codes)
    if supplier_id is not None:
        pool = set(perm_service.get_supplier_permission_codes(db, supplier_id))
        perm_service.assert_codes_subset(
            pool,
            codes,
            message="权限超出供应商已开通范围",
        )


def list_roles(
    db: Session,
    *,
    supplier_id: int | None,
    keyword: str | None,
    pagination: Pagination,
) -> PageData[RolePublic]:
    filters = [BizRole.deleted_at.is_(None)]
    if supplier_id is None:
        filters.append(BizRole.supplier_id.is_(None))
    else:
        filters.append(BizRole.supplier_id == supplier_id)
    if keyword:
        filters.append(BizRole.name.ilike(f"%{keyword}%"))

    total = db.scalar(select(func.count()).select_from(BizRole).where(*filters)) or 0
    rows = db.scalars(
        select(BizRole)
        .where(*filters)
        .order_by(BizRole.id.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()
    return PageData(
        items=[_to_public(db, row) for row in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def get_role(
    db: Session,
    role_id: int,
    *,
    supplier_id: int | None,
) -> RolePublic:
    return _to_public(db, _get_alive_role(db, role_id, supplier_id=supplier_id))


def create_role(
    db: Session,
    *,
    actor: User,
    supplier_id: int | None,
    name: str,
    remark: str | None,
    permission_codes: list[str],
) -> RolePublic:
    _assert_can_assign_codes(
        db, actor, permission_codes, supplier_id=supplier_id
    )
    role = BizRole(
        supplier_id=supplier_id,
        name=name.strip(),
        remark=remark,
        created_by=actor.id,
    )
    db.add(role)
    try:
        db.flush()
        perm_service.replace_role_permissions(
            db, role_id=role.id, permission_codes=permission_codes
        )
        db.commit()
        db.refresh(role)
    except IntegrityError as exc:
        db.rollback()
        raise _conflict_name(exc) from exc
    return _to_public(db, role)


def update_role(
    db: Session,
    *,
    actor: User,
    supplier_id: int | None,
    role_id: int,
    name: str | None,
    remark: str | None,
    is_active: bool | None,
    permission_codes: list[str] | None,
) -> RolePublic:
    role = _get_alive_role(db, role_id, supplier_id=supplier_id)
    if name is not None:
        role.name = name.strip()
    if remark is not None:
        role.remark = remark
    if is_active is not None:
        role.is_active = is_active
    if permission_codes is not None:
        _assert_can_assign_codes(
            db, actor, permission_codes, supplier_id=supplier_id
        )
        perm_service.replace_role_permissions(
            db, role_id=role.id, permission_codes=permission_codes
        )
    try:
        db.commit()
        db.refresh(role)
    except IntegrityError as exc:
        db.rollback()
        raise _conflict_name(exc) from exc
    return _to_public(db, role)


def delete_role(
    db: Session,
    *,
    supplier_id: int | None,
    role_id: int,
) -> None:
    role = _get_alive_role(db, role_id, supplier_id=supplier_id)
    role.deleted_at = datetime.now(timezone.utc)
    role.is_active = False
    db.execute(delete(UserRole).where(UserRole.role_id == role.id))
    db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
    db.commit()


def assert_platform_actor(actor: User) -> None:
    if actor.role not in {
        PortalRole.PLATFORM_ADMIN.value,
        PortalRole.PLATFORM_STAFF.value,
    }:
        raise forbidden()


def assert_supplier_admin_actor(actor: User) -> int:
    if (
        actor.role != PortalRole.SUPPLIER_ADMIN.value
        or actor.supplier_id is None
    ):
        raise forbidden()
    return actor.supplier_id


def list_role_options(
    db: Session,
    *,
    supplier_id: int | None,
) -> list[dict]:
    filters = [BizRole.deleted_at.is_(None), BizRole.is_active.is_(True)]
    if supplier_id is None:
        filters.append(BizRole.supplier_id.is_(None))
    else:
        filters.append(BizRole.supplier_id == supplier_id)
    rows = db.scalars(
        select(BizRole).where(*filters).order_by(BizRole.id.asc())
    ).all()
    return [{"id": r.id, "name": r.name} for r in rows]
