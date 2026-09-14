from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.roles import OrgType, Role


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=128, description="明文密码")
    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    phone: str | None = Field(default=None, min_length=5, max_length=20)
    avatar_url: str | None = Field(default=None, max_length=512)


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=128, description="明文密码")
    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    phone: str | None = Field(default=None, min_length=5, max_length=20)
    avatar_url: str | None = Field(default=None, max_length=512)
    role: Role = Role.PLATFORM_STAFF
    org_type: OrgType = OrgType.PLATFORM
    supplier_id: int | None = None
    is_active: bool = True


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserRoleUpdate(BaseModel):
    role: Role
    org_type: OrgType | None = None
    supplier_id: int | None = None


class AdminPasswordReset(BaseModel):
    new_password: str = Field(min_length=6, max_length=128, description="新明文密码")


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nickname: str
    email: str
    phone: str | None
    avatar_url: str | None
    role: str
    org_type: str
    supplier_id: int | None
    created_by: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
