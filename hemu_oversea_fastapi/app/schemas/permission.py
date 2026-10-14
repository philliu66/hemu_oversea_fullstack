from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PermissionTreeNode(BaseModel):
    id: int
    code: str
    title: str
    type: str
    scope: str
    path: str | None = None
    sort_order: int = 0
    is_active: bool = True
    children: list["PermissionTreeNode"] = Field(default_factory=list)


class PermissionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    parent_id: int | None
    type: str
    title: str
    path: str | None
    scope: str
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PermissionTreeQuery(BaseModel):
    scopes: list[Literal["platform", "supplier", "common"]] | None = Field(
        default=None,
        description="按 scope 过滤；缺省返回全部",
    )
    include_inactive: bool = Field(
        default=False,
        description="是否包含已停用权限",
    )


class PermissionDetail(BaseModel):
    id: int = Field(ge=1, description="权限 ID")


class PermissionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100, description="权限码，如 mission.logs")
    parent_id: int | None = Field(default=None, ge=1, description="父权限 ID")
    parent_code: str | None = Field(
        default=None,
        max_length=100,
        description="父权限码；与 parent_id 二选一，同时传时以 parent_id 为准",
    )
    type: Literal["menu", "button"] = Field(description="menu=菜单，button=按钮")
    title: str = Field(min_length=1, max_length=100, description="显示名称")
    path: str | None = Field(default=None, max_length=255, description="菜单路径")
    scope: Literal["platform", "supplier", "common"] = Field(
        description="platform / supplier / common",
    )
    sort_order: int = Field(default=0, description="同级排序，越小越靠前")
    is_active: bool = Field(default=True, description="是否启用")
    grant_to_all_suppliers: bool = Field(
        default=True,
        description="scope 为 supplier/common 时，是否写入所有供应商权限池",
    )


class PermissionUpdate(BaseModel):
    id: int = Field(ge=1, description="权限 ID")
    code: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: int | None = Field(
        default=None,
        description="父权限 ID；显式传 null 表示置为顶级；省略则不改",
    )
    type: Literal["menu", "button"] | None = None
    title: str | None = Field(default=None, min_length=1, max_length=100)
    path: str | None = Field(default=None, max_length=255)
    scope: Literal["platform", "supplier", "common"] | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class PermissionDelete(BaseModel):
    id: int = Field(ge=1, description="权限 ID")


class RoleSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class RolePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_id: int | None
    name: str
    remark: str | None
    is_active: bool
    created_by: int | None
    created_at: datetime
    updated_at: datetime
    permission_codes: list[str] = Field(default_factory=list)


class RoleList(BaseModel):
    keyword: str | None = Field(default=None, description="按角色名模糊搜索")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    remark: str | None = Field(default=None, max_length=255)
    permission_codes: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    id: int
    name: str | None = Field(default=None, min_length=1, max_length=100)
    remark: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    permission_codes: list[str] | None = None


class RoleDelete(BaseModel):
    id: int


class RoleDetail(BaseModel):
    id: int
