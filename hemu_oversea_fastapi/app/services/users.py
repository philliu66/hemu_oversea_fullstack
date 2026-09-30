from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import Pagination
from app.core.errors import bad_request, conflict, forbidden, not_found
from app.core.roles import Role, is_platform_admin
from app.core.security import hash_password
from app.models.user import User
from app.schemas.common import PageData
from app.schemas.user import SupplierUserOption, UserPublic
from app.services.auth import revoke_all_sessions


def _count_active_platform_admins(db: Session) -> int:
    """统计仍可登录的平台管理员（含遗留 super_admin）。"""
    return (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                User.role.in_(
                    [Role.PLATFORM_ADMIN.value, Role.SUPER_ADMIN.value]
                ),
            )
        )
        or 0
    )


def _forbid_losing_last_platform_admin(db: Session, user: User) -> None:
    """禁止让系统失去最后一个可用的平台管理员。"""
    if not is_platform_admin(user.role):
        return
    if not user.is_active or user.is_deleted:
        return
    if _count_active_platform_admins(db) <= 1:
        raise bad_request("至少保留一名可用的平台管理员")


def create_user(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
    role: str = Role.APP_USER.value,
    org_type: str = "none",
    supplier_id: int | None = None,
    created_by: int | None = None,
    nickname: str | None = None,
    phone: str | None = None,
    avatar_url: str | None = None,
    is_active: bool = True,
    commit: bool = True,
) -> User:
    user = User(
        username=username,
        nickname=nickname or username,
        email=email,
        phone=phone,
        avatar_url=avatar_url,
        hashed_password=hash_password(password),
        role=role,
        org_type=org_type,
        supplier_id=supplier_id,
        created_by=created_by,
        is_active=is_active,
    )
    db.add(user)
    if not commit:
        db.flush()
        return user
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise _conflict_from_integrity(exc) from exc
    return user


def _conflict_from_integrity(exc: IntegrityError) -> Exception:
    detail = str(exc.orig).lower() if exc.orig is not None else str(exc).lower()
    if "phone" in detail:
        return conflict("手机号已存在")
    if "email" in detail:
        return conflict("邮箱已存在")
    if "username" in detail:
        return conflict("用户名已存在")
    return conflict("用户名、邮箱或手机号已存在")


def list_users(
    db: Session,
    *,
    keyword: str | None,
    role: Role | None,
    pagination: Pagination,
) -> PageData[UserPublic]:
    filters = [User.deleted_at.is_(None)]
    if keyword:
        pattern = f"%{keyword}%"
        filters.append(
            or_(
                User.username.ilike(pattern),
                User.nickname.ilike(pattern),
                User.email.ilike(pattern),
                User.phone.ilike(pattern),
            )
        )
    if role is not None:
        filters.append(User.role == role.value)

    count_stmt = select(func.count()).select_from(User).where(*filters)
    stmt = select(User).where(*filters)

    total = db.scalar(count_stmt) or 0
    rows = db.scalars(
        stmt.order_by(User.id.desc()).offset(pagination.offset).limit(pagination.page_size)
    ).all()
    return PageData(
        items=[UserPublic.model_validate(user) for user in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def _get_alive_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None or user.is_deleted:
        raise not_found("用户不存在")
    return user


def _forbid_self(actor: User, user_id: int, message: str) -> None:
    if actor.id == user_id:
        raise bad_request(message)


def soft_delete_user(db: Session, *, user_id: int, actor: User) -> None:
    _forbid_self(actor, user_id, "不能删除当前登录账号")
    user = _get_alive_user(db, user_id)
    _forbid_losing_last_platform_admin(db, user)
    user.deleted_at = datetime.now(timezone.utc)
    revoke_all_sessions(db, user.id)
    db.commit()


def set_user_active(db: Session, *, user_id: int, is_active: bool, actor: User) -> User:
    _forbid_self(actor, user_id, "不能启用或停用当前登录账号")
    user = _get_alive_user(db, user_id)
    if not is_active:
        _forbid_losing_last_platform_admin(db, user)
    user.is_active = is_active
    if not is_active:
        revoke_all_sessions(db, user.id)
    db.commit()
    db.refresh(user)
    return user


def set_user_role(
    db: Session,
    *,
    user_id: int,
    role: Role,
    actor: User,
    org_type: str | None = None,
    supplier_id: int | None = None,
) -> User:
    _forbid_self(actor, user_id, "不能修改当前登录账号的角色")
    user = _get_alive_user(db, user_id)
    if is_platform_admin(user.role) and not is_platform_admin(role.value):
        _forbid_losing_last_platform_admin(db, user)
    user.role = role.value
    if org_type is not None:
        user.org_type = org_type
    if supplier_id is not None:
        user.supplier_id = supplier_id
    elif role in {
        Role.PLATFORM_ADMIN,
        Role.SUPER_ADMIN,
        Role.PLATFORM_STAFF,
        Role.APP_USER,
    }:
        user.supplier_id = None
    revoke_all_sessions(db, user.id)
    db.commit()
    db.refresh(user)
    return user


def reset_user_password(
    db: Session,
    *,
    user_id: int,
    new_password: str,
    actor: User,
) -> None:
    """重置密码：new_password 为明文。"""
    _forbid_self(actor, user_id, "不能在此重置当前登录账号的密码，请走改密接口")
    user = _get_alive_user(db, user_id)
    user.hashed_password = hash_password(new_password)
    revoke_all_sessions(db, user.id)
    db.commit()


_PLATFORM_ROLES = {
    Role.PLATFORM_ADMIN.value,
    Role.SUPER_ADMIN.value,
    Role.PLATFORM_STAFF.value,
}
_SUPPLIER_PORTAL_ROLES = {Role.SUPPLIER_ADMIN.value, Role.SUPPLIER_STAFF.value}


def list_supplier_users(
    db: Session,
    *,
    actor: User,
    keyword: str | None,
    supplier_id: int | None,
) -> list[SupplierUserOption]:
    """当前供应商下的在职管理员和员工，供任务人员下拉使用。"""
    if actor.role in _SUPPLIER_PORTAL_ROLES:
        if actor.supplier_id is None:
            raise bad_request("当前账号未绑定供应商")
        scope_supplier_id = actor.supplier_id
    elif actor.role in _PLATFORM_ROLES:
        if supplier_id is None:
            raise bad_request("请指定供应商")
        scope_supplier_id = supplier_id
    else:
        raise forbidden()

    filters = [
        User.deleted_at.is_(None),
        User.is_active.is_(True),
        User.supplier_id == scope_supplier_id,
        User.role.in_(_SUPPLIER_PORTAL_ROLES),
    ]
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        filters.append(
            or_(
                User.username.ilike(pattern),
                User.nickname.ilike(pattern),
            )
        )
    rows = db.scalars(select(User).where(*filters).order_by(User.id.asc())).all()
    return [SupplierUserOption.model_validate(user) for user in rows]


def soft_delete_self(db: Session, user: User) -> None:
    if user.is_deleted:
        raise not_found("用户不存在")
    _forbid_losing_last_platform_admin(db, user)
    user.deleted_at = datetime.now(timezone.utc)
    revoke_all_sessions(db, user.id)
    db.commit()
