import random
import string
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import Pagination
from app.core.errors import conflict, not_found
from app.core.roles import OrgType, Role
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.common import PageData
from app.schemas.supplier import SupplierPublic
from app.services import users as user_service
from app.services.auth import revoke_all_sessions

# 6 位供应商编码：大写字母 + 数字
_CODE_ALPHABET = string.ascii_uppercase + string.digits
_CODE_LENGTH = 6
_CODE_MAX_ATTEMPTS = 32


def _generate_unique_code(db: Session) -> str:
    for _ in range(_CODE_MAX_ATTEMPTS):
        code = "".join(random.choices(_CODE_ALPHABET, k=_CODE_LENGTH))
        exists = db.scalar(
            select(Supplier.id).where(
                Supplier.code == code,
                Supplier.deleted_at.is_(None),
            )
        )
        if exists is None:
            return code
    raise conflict("供应商编码生成失败，请重试")


def _get_alive_supplier(db: Session, supplier_id: int) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None or supplier.is_deleted:
        raise not_found("供应商不存在")
    return supplier


def _conflict_from_integrity(exc: IntegrityError) -> Exception:
    detail = str(exc.orig).lower() if exc.orig is not None else str(exc).lower()
    if "code" in detail:
        return conflict("供应商编码已存在")
    if "username" in detail:
        return conflict("管理员用户名已存在")
    if "email" in detail:
        return conflict("邮箱已存在")
    if "phone" in detail:
        return conflict("手机号已存在")
    return conflict("供应商或管理员账号信息冲突")


def create_supplier(
    db: Session,
    *,
    name: str,
    phone: str,
    email: str,
    admin_username: str,
    admin_password: str,
    permission_codes: list[str],
    created_by: int,
) -> Supplier:
    """创建供应商，并同步创建该供应商的默认管理员账号。"""
    from app.services import permissions as perm_service

    code = _generate_unique_code(db)
    supplier = Supplier(
        code=code,
        name=name,
        phone=phone,
        email=email,
        created_by=created_by,
    )
    db.add(supplier)
    try:
        db.flush()
        perm_service.replace_supplier_pool(
            db,
            supplier_id=supplier.id,
            permission_codes=permission_codes,
        )
        user_service.create_user(
            db,
            username=admin_username,
            email=email,
            password=admin_password,
            nickname=admin_username,
            phone=phone,
            role=Role.SUPPLIER_ADMIN.value,
            org_type=OrgType.SUPPLIER.value,
            supplier_id=supplier.id,
            created_by=created_by,
            commit=False,
        )
        db.commit()
        db.refresh(supplier)
    except IntegrityError as exc:
        db.rollback()
        raise _conflict_from_integrity(exc) from exc
    return supplier


def list_suppliers(
    db: Session,
    *,
    keyword: str | None,
    pagination: Pagination,
) -> PageData[SupplierPublic]:
    filters = [Supplier.deleted_at.is_(None)]
    if keyword:
        pattern = f"%{keyword}%"
        filters.append(
            or_(
                Supplier.name.ilike(pattern),
                Supplier.code.ilike(pattern),
                Supplier.email.ilike(pattern),
                Supplier.phone.ilike(pattern),
            )
        )

    count_stmt = select(func.count()).select_from(Supplier).where(*filters)
    stmt = select(Supplier).where(*filters)

    total = db.scalar(count_stmt) or 0
    rows = db.scalars(
        stmt.order_by(Supplier.id.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()
    return PageData(
        items=[SupplierPublic.model_validate(row) for row in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def get_supplier(db: Session, supplier_id: int) -> Supplier:
    return _get_alive_supplier(db, supplier_id)


def get_supplier_admin_username(db: Session, supplier_id: int) -> str | None:
    """取该供应商下最早创建的未删除供应商管理员用户名。"""
    return db.scalar(
        select(User.username)
        .where(
            User.supplier_id == supplier_id,
            User.role == Role.SUPPLIER_ADMIN.value,
            User.deleted_at.is_(None),
        )
        .order_by(User.id.asc())
        .limit(1)
    )


def update_supplier(
    db: Session,
    *,
    supplier_id: int,
    name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    permission_codes: list[str] | None = None,
) -> Supplier:
    from app.services import permissions as perm_service

    supplier = _get_alive_supplier(db, supplier_id)
    if name is not None:
        supplier.name = name
    if phone is not None:
        supplier.phone = phone
    if email is not None:
        supplier.email = email
    if permission_codes is not None:
        perm_service.replace_supplier_pool(
            db,
            supplier_id=supplier.id,
            permission_codes=permission_codes,
        )
    try:
        db.commit()
        db.refresh(supplier)
    except IntegrityError as exc:
        db.rollback()
        raise _conflict_from_integrity(exc) from exc
    return supplier


def soft_delete_supplier(db: Session, *, supplier_id: int) -> None:
    supplier = _get_alive_supplier(db, supplier_id)
    now = datetime.now(timezone.utc)
    supplier.deleted_at = now

    # 同步软删除归属该供应商的未删除用户，并撤销会话
    users = db.scalars(
        select(User).where(
            User.supplier_id == supplier_id,
            User.deleted_at.is_(None),
        )
    ).all()
    for user in users:
        user.deleted_at = now
        user.is_active = False
        revoke_all_sessions(db, user.id)

    db.commit()
