from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class LoginLogList(BaseModel):
    user_id: int | None = Field(default=None, ge=1, description="用户 ID")
    username: str | None = Field(default=None, description="用户名（模糊）")
    audience: Literal["admin", "app"] | None = Field(
        default=None,
        description="端：admin / app",
    )
    ip: str | None = Field(default=None, description="登录 IP（精确）")
    login_at_from: datetime | None = Field(default=None, description="登录时间起")
    login_at_to: datetime | None = Field(default=None, description="登录时间止")
    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class LoginLogPublic(BaseModel):
    id: int
    user_id: int | None
    username: str
    audience: str
    login_at: datetime
    logout_at: datetime | None
    logout_reason: str | None
    last_seen_at: datetime
    online_seconds: int = Field(description="估算在线秒数")
    ip: str | None
    user_agent: str | None
    refresh_jti: str
    created_at: datetime


class LoginLogStats(BaseModel):
    grain: Literal["day", "week", "month"] = Field(description="统计粒度")
    audience: Literal["admin", "app"] | None = Field(
        default=None,
        description="端：admin / app",
    )
    login_at_from: datetime | None = Field(default=None, description="登录时间起")
    login_at_to: datetime | None = Field(default=None, description="登录时间止")


class LoginLogStatItem(BaseModel):
    bucket: datetime = Field(description="时间桶起点")
    login_count: int
    unique_user_count: int


class OperationLogList(BaseModel):
    actor_user_id: int | None = Field(default=None, ge=1, description="操作人用户 ID")
    action: str | None = Field(default=None, description="动作码，如 mission.create")
    resource_type: str | None = Field(default=None, description="资源类型")
    resource_id: str | None = Field(default=None, description="资源 ID")
    created_at_from: datetime | None = Field(default=None, description="创建时间起")
    created_at_to: datetime | None = Field(default=None, description="创建时间止")
    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class OperationLogPublic(BaseModel):
    id: int
    actor_user_id: int | None
    actor_username: str
    actor_role: str
    org_type: str
    supplier_id: int | None
    action: str
    resource_type: str
    resource_id: str
    summary: str
    detail: dict[str, Any] | None
    ip: str | None
    user_agent: str | None
    status: str
    created_at: datetime
