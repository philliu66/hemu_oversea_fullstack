from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PermissionTreeNode(BaseModel):
    id: int
    code: str
    title: str
    type: str
    scope: str
    path: str | None = None
    children: list["PermissionTreeNode"] = Field(default_factory=list)


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
