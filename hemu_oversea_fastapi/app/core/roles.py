from enum import StrEnum


class Role(StrEnum):
    """门户身份。管理端 4 种 + App 端 1 种。"""

    PLATFORM_ADMIN = "platform_admin"
    PLATFORM_STAFF = "platform_staff"
    SUPPLIER_ADMIN = "supplier_admin"
    SUPPLIER_STAFF = "supplier_staff"
    APP_USER = "app_user"


class OrgType(StrEnum):
    """组织归属类型。"""

    PLATFORM = "platform"
    SUPPLIER = "supplier"
    NONE = "none"


def is_platform_admin(role: str | None) -> bool:
    return role == Role.PLATFORM_ADMIN.value


# 可登录管理端的角色
ADMIN_PORTAL_ROLES: frozenset[Role] = frozenset(
    {
        Role.PLATFORM_ADMIN,
        Role.PLATFORM_STAFF,
        Role.SUPPLIER_ADMIN,
        Role.SUPPLIER_STAFF,
    }
)

# 可登录 App 端的角色
APP_PORTAL_ROLES: frozenset[Role] = frozenset({Role.APP_USER})
