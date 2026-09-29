from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import Pagination
from app.core.errors import bad_request, conflict, forbidden, not_found
from app.core.roles import OrgType, Role
from app.core.security import hash_password
from app.models.user import User
from app.schemas.common import PageData
from app.schemas.user import UserPublic
from app.services import permissions as perm_service
from app.services import users as user_service
from app.services.auth import revoke_all_sessions


def _conflict_from_integrity(exc: IntegrityError) -> Exception:
    detail = str(exc.orig).lower() if exc.orig is not None else str(exc).lower()
    if "phone" in detail:
        return conflict("手机号已存在")
    if "email" in detail:
        return conflict("邮箱已存在")
    if "username" in detail:
        return conflict("用户名已存在")
    return conflict("用户名、邮箱或手机号已存在")


def enrich_user(db: Session, user: User) -> UserPublic:
    data = perm_service.to_user_public_dict(user, db)
    roles = perm_service.list_user_role_summaries(db, [user.id]).get(user.id, [])
    data["roles"] = roles
    return UserPublic(**data)


def enrich_users(db: Session, users: list[User]) -> list[UserPublic]:
    if not users:
        return []
    role_map = perm_service.list_user_role_summaries(db, [u.id for u in users])
    result: list[UserPublic] = []
    for user in users:
        data = UserPublic.model_validate(user).model_dump()
        data["permission_codes"] = []  # 列表不解析全量权限，减负
        data["roles"] = role_map.get(user.id, [])
        result.append(UserPublic(**data))
    return result


def _actor_supplier_id(actor: User) -> int:
    if actor.supplier_id is None:
        raise bad_request("当前账号未绑定供应商")
    return actor.supplier_id


def _get_owned_staff(db: Session, *, staff_id: int, actor: User) -> User:
    supplier_id = _actor_supplier_id(actor)
    user = db.get(User, staff_id)
    if user is None or user.is_deleted:
        raise not_found("员工不存在")
    if user.supplier_id != supplier_id or user.role != Role.SUPPLIER_STAFF.value:
        raise forbidden("只能管理本供应商下的员工账号")
    return user


def list_staff(
    db: Session,
    *,
    actor: User,
    keyword: str | None,
    pagination: Pagination,
) -> PageData[UserPublic]:
    supplier_id = _actor_supplier_id(actor)
    filters = [
        User.deleted_at.is_(None),
        User.supplier_id == supplier_id,
        User.role == Role.SUPPLIER_STAFF.value,
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
    supplier_id = _actor_supplier_id(actor)
    try:
        user = user_service.create_user(
            db,
            username=username,
            email=email,
            password=password,
            nickname=nickname or username,
            phone=phone,
            role=Role.SUPPLIER_STAFF.value,
            org_type=OrgType.SUPPLIER.value,
            supplier_id=supplier_id,
            created_by=actor.id,
            commit=False,
        )
        perm_service.replace_user_roles(
            db,
            user_id=user.id,
            role_ids=role_ids or [],
            expected_supplier_id=supplier_id,
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
    actor: User,
    staff_id: int,
    nickname: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    password: str | None = None,
    role_ids: list[int] | None = None,
) -> UserPublic:
    user = _get_owned_staff(db, staff_id=staff_id, actor=actor)
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
            expected_supplier_id=_actor_supplier_id(actor),
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
    actor: User,
    staff_id: int,
    is_active: bool,
) -> UserPublic:
    user = _get_owned_staff(db, staff_id=staff_id, actor=actor)
    user.is_active = is_active
    if not is_active:
        revoke_all_sessions(db, user.id)
    db.commit()
    db.refresh(user)
    return enrich_user(db, user)


def soft_delete_staff(db: Session, *, actor: User, staff_id: int) -> None:
    user = _get_owned_staff(db, staff_id=staff_id, actor=actor)
    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    revoke_all_sessions(db, user.id)
    db.commit()
