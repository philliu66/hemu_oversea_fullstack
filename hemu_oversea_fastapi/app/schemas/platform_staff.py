from pydantic import BaseModel, Field


class PlatformStaffList(BaseModel):
    keyword: str | None = Field(default=None)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


class PlatformStaffCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    phone: str | None = Field(default=None, min_length=5, max_length=20)
    role_ids: list[int] = Field(default_factory=list)


class PlatformStaffUpdate(BaseModel):
    id: int
    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    phone: str | None = Field(default=None, min_length=5, max_length=20)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    role_ids: list[int] | None = None


class PlatformStaffStatusUpdate(BaseModel):
    id: int
    is_active: bool


class PlatformStaffDelete(BaseModel):
    id: int
