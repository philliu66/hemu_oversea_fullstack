import logging
from datetime import datetime, timezone

from sqlalchemy import select, text

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.roles import OrgType, Role
from app.core.security import hash_password, verify_password
from app.models.supplier import Supplier
from app.models.user import User

logger = logging.getLogger("app")

# 旧种子账号：启动时软删除，避免与新角色体系混淆
_LEGACY_SEED_USERNAMES = ("admin", "operator", "user")
_BOOTSTRAP_SUPPLIER_CODE = "B00001"


def ensure_seed_users() -> None:
    """初始化种子供应商 + 管理端 4 种角色各一个账号；密码统一为 BOOTSTRAP_PASSWORD。"""
    db = SessionLocal()
    try:
        _retire_legacy_seeds(db)
        supplier = _ensure_bootstrap_supplier(db)

        password = settings.BOOTSTRAP_PASSWORD
        supplier_id = supplier.id

        super_admin = _ensure_user(
            db,
            username="superadmin",
            email="superadmin@example.com",
            password=password,
            role=Role.SUPER_ADMIN,
            org_type=OrgType.PLATFORM,
            supplier_id=None,
            created_by=None,
        )
        _ensure_user(
            db,
            username="superstaff01",
            email="superstaff01@example.com",
            password=password,
            role=Role.PLATFORM_STAFF,
            org_type=OrgType.PLATFORM,
            supplier_id=None,
            created_by=super_admin.id,
        )
        supplier_admin = _ensure_user(
            db,
            username="supplieradmin01",
            email="supplieradmin01@example.com",
            password=password,
            role=Role.SUPPLIER_ADMIN,
            org_type=OrgType.SUPPLIER,
            supplier_id=supplier_id,
            created_by=None,
        )
        _ensure_user(
            db,
            username="supplierstaff01",
            email="supplierstaff01@example.com",
            password=password,
            role=Role.SUPPLIER_STAFF,
            org_type=OrgType.SUPPLIER,
            supplier_id=supplier_id,
            created_by=supplier_admin.id,
        )
        db.commit()
    finally:
        db.close()


def _ensure_bootstrap_supplier(db) -> Supplier:
    """确保种子供应商存在，供供应商角色账号挂靠。"""
    supplier_id = settings.BOOTSTRAP_SUPPLIER_ID
    supplier = db.get(Supplier, supplier_id)
    if supplier is not None and not supplier.is_deleted:
        return supplier

    by_code = db.scalar(
        select(Supplier).where(
            Supplier.code == _BOOTSTRAP_SUPPLIER_CODE,
            Supplier.deleted_at.is_(None),
        )
    )
    if by_code is not None:
        return by_code

    if supplier is not None and supplier.is_deleted:
        supplier.deleted_at = None
        supplier.name = "Bootstrap Supplier"
        supplier.phone = "10000000000"
        supplier.email = "bootstrap-supplier@example.com"
        supplier.code = _BOOTSTRAP_SUPPLIER_CODE
        db.flush()
        logger.info("restored bootstrap supplier id=%s", supplier.id)
        return supplier

    supplier = Supplier(
        id=supplier_id,
        code=_BOOTSTRAP_SUPPLIER_CODE,
        name="Bootstrap Supplier",
        phone="10000000000",
        email="bootstrap-supplier@example.com",
        created_by=None,
    )
    db.add(supplier)
    db.flush()
    # 显式写入 id 后同步序列，避免后续自增冲突
    db.execute(
        text(
            "SELECT setval(pg_get_serial_sequence('suppliers', 'id'), "
            "(SELECT COALESCE(MAX(id), 1) FROM suppliers))"
        )
    )
    logger.info("seeded bootstrap supplier id=%s code=%s", supplier.id, supplier.code)
    return supplier


def _retire_legacy_seeds(db) -> None:
    now = datetime.now(timezone.utc)
    rows = db.scalars(
        select(User).where(
            User.username.in_(_LEGACY_SEED_USERNAMES),
            User.deleted_at.is_(None),
        )
    ).all()
    for user in rows:
        user.deleted_at = now
        user.is_active = False
        logger.info("retired legacy seed user username=%s", user.username)


def _ensure_user(
    db,
    *,
    username: str,
    email: str,
    password: str,
    role: Role,
    org_type: OrgType,
    supplier_id: int | None,
    created_by: int | None,
) -> User:
    user = db.scalar(
        select(User).where(User.username == username, User.deleted_at.is_(None))
    )
    if user is None:
        user = User(
            username=username,
            nickname=username,
            email=email,
            hashed_password=hash_password(password),
            role=role.value,
            org_type=org_type.value,
            supplier_id=supplier_id,
            created_by=created_by,
            is_active=True,
        )
        db.add(user)
        db.flush()
        logger.info("seeded user username=%s role=%s", username, role.value)
        return user

    changed = False
    if user.role != role.value:
        user.role = role.value
        changed = True
    if user.org_type != org_type.value:
        user.org_type = org_type.value
        changed = True
    if user.supplier_id != supplier_id:
        user.supplier_id = supplier_id
        changed = True
    if user.created_by != created_by:
        user.created_by = created_by
        changed = True
    if not verify_password(password, user.hashed_password):
        user.hashed_password = hash_password(password)
        changed = True
    if changed:
        logger.info("updated seed user username=%s role=%s", username, role.value)
    return user
