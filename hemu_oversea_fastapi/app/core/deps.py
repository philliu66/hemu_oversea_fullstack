from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import forbidden, unauthorized
from app.core.roles import (
    ADMIN_PORTAL_ROLES,
    APP_PORTAL_ROLES,
    Role,
    normalize_portal_role,
)
from app.core.security import Audience, TokenError, decode_token
from app.models.user import User
from app.services import permissions as perm_service

_bearer = HTTPBearer(auto_error=False)
_STAFF_ROLE_VALUES = {
    normalize_portal_role(role.value) or role.value for role in ADMIN_PORTAL_ROLES
}
_STAFF_ROLE_VALUES.add(Role.SUPER_ADMIN.value)
_STAFF_ROLE_VALUES.add(Role.PLATFORM_ADMIN.value)
_APP_ROLE_VALUES = {role.value for role in APP_PORTAL_ROLES}


class Pagination(BaseModel):
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def get_pagination(
    page: int = Query(default=1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页条数"),
) -> Pagination:
    return Pagination(page=page, page_size=page_size)


def _user_from_access(
    creds: HTTPAuthorizationCredentials | None,
    db: Session,
    audience: Audience | tuple[Audience, ...],
) -> User:
    if creds is None or not creds.credentials:
        raise unauthorized()
    try:
        user_id = int(decode_token(creds.credentials, "access", audience).subject)
    except (TokenError, ValueError):
        raise unauthorized()

    user = db.get(User, user_id)
    if user is None or user.is_deleted:
        raise unauthorized()
    if not user.is_active:
        raise unauthorized("账号已停用")
    return user


def get_current_app_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    user = _user_from_access(creds, db, "app")
    if user.role not in _APP_ROLE_VALUES:
        raise unauthorized()
    return user


def get_current_admin_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    user = _user_from_access(creds, db, "admin")
    normalized = normalize_portal_role(user.role) or user.role
    if normalized not in _STAFF_ROLE_VALUES and user.role not in _STAFF_ROLE_VALUES:
        raise unauthorized()
    return user


def get_current_account(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """App 或管理端 access 均可。用于 /common 下两端同权接口。"""
    return _user_from_access(creds, db, ("app", "admin"))


def require_roles(*roles: Role):
    """管理端：先确认是 admin token（401），再核对角色（不够则 403）。"""
    allowed: set[str] = set()
    for role in roles:
        allowed.add(role.value)
        if role == Role.PLATFORM_ADMIN:
            allowed.add(Role.SUPER_ADMIN.value)

    def _checker(current_user: User = Depends(get_current_admin_user)) -> User:
        user_role = normalize_portal_role(current_user.role) or current_user.role
        if current_user.role not in allowed and user_role not in allowed:
            raise forbidden()
        return current_user

    return _checker


def require_perm(*codes: str, require_all: bool = True):
    """校验权限码；platform_admin 直接放行。"""

    def _checker(
        current_user: User = Depends(get_current_admin_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not perm_service.user_has_permissions(
            db,
            current_user,
            *codes,
            require_all=require_all,
        ):
            raise forbidden("无操作权限")
        return current_user

    return _checker


require_platform_admin = require_roles(Role.PLATFORM_ADMIN)
require_super_admin = require_platform_admin  # 兼容旧名
require_platform = require_roles(Role.PLATFORM_ADMIN, Role.PLATFORM_STAFF)
require_supplier_admin = require_roles(Role.SUPPLIER_ADMIN)
require_supplier = require_roles(Role.SUPPLIER_ADMIN, Role.SUPPLIER_STAFF)
require_admin_user = require_roles(*ADMIN_PORTAL_ROLES)
