from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class LoginLogList(BaseModel):
    keyword: str | None = Field(
        default=None,
        description="关键词：用户昵称、邮箱或手机号（模糊）",
    )
    supplier_id: int | None = Field(
        default=None,
        ge=1,
        description="供应商 ID。仅平台账号可传；不传则按可见范围查询",
    )
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
    nickname: str | None = Field(default=None, description="用户昵称")
    email: str | None = Field(default=None, description="用户邮箱")
    phone: str | None = Field(default=None, description="用户手机号")
    supplier_id: int | None = Field(
        default=None,
        description="登录时用户所属供应商；平台账号为空",
    )
    supplier_name: str | None = Field(default=None, description="所属供应商名称")
    audience: str
    login_at: datetime
    logout_at: datetime | None
    logout_reason: str | None
    last_seen_at: datetime
    online_seconds: int = Field(
        description="停留秒数。已登出时为登录到登出；未登出时估算到最近活跃",
    )
    ip: str | None
    user_agent: str | None
    refresh_jti: str
    created_at: datetime


class LoginLogStats(BaseModel):
    grain: Literal["day", "week", "month"] = Field(description="统计粒度")
    supplier_id: int | None = Field(
        default=None,
        ge=1,
        description="供应商 ID。仅平台账号可传；不传则按可见范围统计",
    )
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
    keyword: str | None = Field(
        default=None,
        description="关键词：用户昵称、邮箱、手机号或操作名称（模糊）",
    )
    supplier_id: int | None = Field(
        default=None,
        ge=1,
        description="供应商 ID。仅平台账号可传；不传则按可见范围查询",
    )
    actor_user_id: int | None = Field(default=None, ge=1, description="操作人用户 ID")
    action: str | None = Field(default=None, description="动作码，如 mission.create")
    resource_type: str | None = Field(default=None, description="资源类型")
    resource_id: str | None = Field(default=None, description="资源 ID")
    created_at_from: datetime | None = Field(default=None, description="操作时间起")
    created_at_to: datetime | None = Field(default=None, description="操作时间止")
    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class OperationLogPublic(BaseModel):
    id: int
    actor_user_id: int | None
    actor_username: str
    nickname: str | None = Field(default=None, description="操作人昵称")
    email: str | None = Field(default=None, description="操作人邮箱")
    phone: str | None = Field(default=None, description="操作人手机号")
    actor_role: str
    org_type: str
    supplier_id: int | None
    supplier_name: str | None = Field(default=None, description="所属供应商名称")
    action: str
    resource_type: str
    resource_id: str
    summary: str
    detail: dict[str, Any] | None
    ip: str | None
    user_agent: str | None
    status: str
    created_at: datetime
