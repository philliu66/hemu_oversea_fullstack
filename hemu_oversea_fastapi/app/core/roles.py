from enum import StrEnum


class Role(StrEnum):
    """门户身份。管理端 4 种 + App 端 1 种。"""

    PLATFORM_ADMIN = "platform_admin"
    PLATFORM_STAFF = "platform_staff"
    SUPPLIER_ADMIN = "supplier_admin"
    SUPPLIER_STAFF = "supplier_staff"
    APP_USER = "app_user"

    # 兼容旧值（迁移前遗留会话/数据）
    SUPER_ADMIN = "super_admin"


class OrgType(StrEnum):
    """组织归属类型。"""

    PLATFORM = "platform"
    SUPPLIER = "supplier"
    NONE = "none"


def normalize_portal_role(role: str | None) -> str | None:
    """将遗留 super_admin 归一为 platform_admin。"""
    if role == Role.SUPER_ADMIN.value or role == "super_admin":
        return Role.PLATFORM_ADMIN.value
    return role


def is_platform_admin(role: str | None) -> bool:
    r = normalize_portal_role(role)
    return r == Role.PLATFORM_ADMIN.value


# 可登录管理端的角色
ADMIN_PORTAL_ROLES: frozenset[Role] = frozenset(
    {
        Role.PLATFORM_ADMIN,
        Role.PLATFORM_STAFF,
        Role.SUPPLIER_ADMIN,
        Role.SUPPLIER_STAFF,
        Role.SUPER_ADMIN,  # 兼容旧 token / 未迁完数据
    }
)

# 可登录 App 端的角色
APP_PORTAL_ROLES: frozenset[Role] = frozenset({Role.APP_USER})
