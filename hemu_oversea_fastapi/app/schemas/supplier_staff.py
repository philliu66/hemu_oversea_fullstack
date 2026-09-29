from pydantic import BaseModel, Field


class SupplierStaffList(BaseModel):
    keyword: str | None = Field(
        default=None,
        description="按用户名、昵称、邮箱或手机号模糊搜索",
    )
    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class SupplierStaffCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, description="员工账号")
    password: str = Field(min_length=6, max_length=128, description="明文密码")
    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    email: str = Field(min_length=3, max_length=255, description="邮箱")
    phone: str | None = Field(default=None, min_length=5, max_length=20)
    role_ids: list[int] = Field(default_factory=list, description="业务角色 ID 列表")


class SupplierStaffUpdate(BaseModel):
    id: int = Field(description="员工用户 ID")
    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    phone: str | None = Field(default=None, min_length=5, max_length=20)
    password: str | None = Field(
        default=None,
        min_length=6,
        max_length=128,
        description="可选：重置明文密码",
    )
    role_ids: list[int] | None = Field(default=None, description="业务角色 ID 列表")


class SupplierStaffStatusUpdate(BaseModel):
    id: int = Field(description="员工用户 ID")
    is_active: bool = Field(description="是否启用")


class SupplierStaffDelete(BaseModel):
    id: int = Field(description="员工用户 ID")
