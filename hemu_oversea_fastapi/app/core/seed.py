import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.roles import OrgType, Role
from app.core.security import hash_password, verify_password
from app.models.user import User

logger = logging.getLogger("app")

# 旧种子账号：启动时软删除，避免与新角色体系混淆
_LEGACY_SEED_USERNAMES = ("admin", "operator", "user")


def ensure_seed_users() -> None:
    """初始化平台管理员 superadmin；密码为 BOOTSTRAP_PASSWORD。已存在则按配置同步密码/角色。"""
    db = SessionLocal()
    try:
        _retire_legacy_seeds(db)
        _ensure_user(
            db,
            username="superadmin",
            email="superadmin@example.com",
            password=settings.BOOTSTRAP_PASSWORD,
            role=Role.PLATFORM_ADMIN,
            org_type=OrgType.PLATFORM,
            supplier_id=None,
            created_by=None,
        )
        db.commit()
    finally:
        db.close()


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
