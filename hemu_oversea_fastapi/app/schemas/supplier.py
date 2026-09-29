from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="供应商名称")
    phone: str = Field(min_length=5, max_length=20, description="联系电话")
    email: str = Field(min_length=3, max_length=255, description="邮件地址")
    admin_username: str = Field(
        min_length=3,
        max_length=50,
        description="供应商默认管理员账号",
    )
    admin_password: str = Field(
        min_length=6,
        max_length=128,
        description="供应商默认管理员明文密码",
    )
    permission_codes: list[str] = Field(
        min_length=1,
        description="分配给该供应商的权限码列表",
    )


class SupplierUpdate(BaseModel):
    id: int = Field(description="供应商 ID")
    name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, min_length=5, max_length=20)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    permission_codes: list[str] | None = Field(
        default=None,
        description="更新供应商权限池；不传则不改",
    )


class SupplierDelete(BaseModel):
    id: int = Field(description="供应商 ID")


class SupplierDetail(BaseModel):
    id: int = Field(description="供应商 ID")


class SupplierList(BaseModel):
    keyword: str | None = Field(default=None, description="按名称、编码、邮箱或电话模糊搜索")
    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class SupplierPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    phone: str
    email: str
    created_by: int | None
    created_at: datetime
    updated_at: datetime


class SupplierDetailPublic(SupplierPublic):
    """供应商详情：额外返回默认管理员账号（不含密码）。"""

    admin_username: str | None = None
    permission_codes: list[str] = Field(default_factory=list)
