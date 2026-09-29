from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import Pagination
from app.core.errors import conflict, forbidden, not_found
from app.core.roles import OrgType, Role
from app.core.security import hash_password
from app.models.user import User
from app.schemas.common import PageData
from app.schemas.user import UserPublic
from app.services import permissions as perm_service
from app.services import users as user_service
from app.services.auth import revoke_all_sessions
from app.services.supplier_staff import enrich_user, enrich_users


def _conflict_from_integrity(exc: IntegrityError) -> Exception:
    detail = str(exc.orig).lower() if exc.orig is not None else str(exc).lower()
    if "phone" in detail:
        return conflict("手机号已存在")
    if "email" in detail:
        return conflict("邮箱已存在")
    if "username" in detail:
        return conflict("用户名已存在")
    return conflict("用户名、邮箱或手机号已存在")


def _get_platform_staff(db: Session, staff_id: int) -> User:
    user = db.get(User, staff_id)
    if user is None or user.is_deleted:
        raise not_found("员工不存在")
    if user.role != Role.PLATFORM_STAFF.value:
        raise forbidden("只能管理平台员工账号")
    return user


def list_staff(
    db: Session,
    *,
    keyword: str | None,
    pagination: Pagination,
) -> PageData[UserPublic]:
    filters = [
        User.deleted_at.is_(None),
        User.role == Role.PLATFORM_STAFF.value,
    ]
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
    total = db.scalar(select(func.count()).select_from(User).where(*filters)) or 0
    rows = list(
        db.scalars(
            select(User)
            .where(*filters)
            .order_by(User.id.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        ).all()
    )
    return PageData(
        items=enrich_users(db, rows),
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def create_staff(
    db: Session,
    *,
    actor: User,
    username: str,
    password: str,
    email: str,
    nickname: str | None = None,
    phone: str | None = None,
    role_ids: list[int] | None = None,
) -> UserPublic:
    try:
        user = user_service.create_user(
            db,
            username=username,
            email=email,
            password=password,
            nickname=nickname or username,
            phone=phone,
            role=Role.PLATFORM_STAFF.value,
            org_type=OrgType.PLATFORM.value,
            supplier_id=None,
            created_by=actor.id,
            commit=False,
        )
        perm_service.replace_user_roles(
            db,
            user_id=user.id,
            role_ids=role_ids or [],
            expected_supplier_id=None,
        )
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise _conflict_from_integrity(exc) from exc
    return enrich_user(db, user)


def update_staff(
    db: Session,
    *,
    staff_id: int,
    nickname: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    password: str | None = None,
    role_ids: list[int] | None = None,
) -> UserPublic:
    user = _get_platform_staff(db, staff_id)
    if nickname is not None:
        user.nickname = nickname
    if email is not None:
        user.email = email
    if phone is not None:
        user.phone = phone
    if password is not None:
        user.hashed_password = hash_password(password)
        revoke_all_sessions(db, user.id)
    if role_ids is not None:
        perm_service.replace_user_roles(
            db,
            user_id=user.id,
            role_ids=role_ids,
            expected_supplier_id=None,
        )
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise _conflict_from_integrity(exc) from exc
    return enrich_user(db, user)


def set_staff_active(
    db: Session,
    *,
    staff_id: int,
    is_active: bool,
) -> UserPublic:
    user = _get_platform_staff(db, staff_id)
    user.is_active = is_active
    if not is_active:
        revoke_all_sessions(db, user.id)
    db.commit()
    db.refresh(user)
    return enrich_user(db, user)


def soft_delete_staff(db: Session, *, staff_id: int) -> None:
    user = _get_platform_staff(db, staff_id)
    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    revoke_all_sessions(db, user.id)
    db.commit()
