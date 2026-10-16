"""邮件发送记录相关 schema。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MailSendLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    supplier_id: int | None = None
    to_emails: str
    subject: str
    status: str
    error_message: str | None = None
    payload: dict[str, Any] | None = None
    provider_request_id: str | None = None
    created_at: datetime


class MailSendLogListRequest(BaseModel):
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID；供应商门户可省略，平台必传",
    )
    category: str | None = Field(
        default=None,
        description="业务类别；不传则不过滤（当前主要用 store_inspection）",
    )
    status: str | None = Field(
        default=None,
        description="success / failed；不传则不过滤",
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SupplierDailyInspectionRunRequest(BaseModel):
    """手动触发供应商每日巡检发信。"""

    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID；供应商门户可省略，平台必传",
    )


class SupplierDailyInspectionRunPublic(BaseModel):
    """每日巡检发信执行结果。"""

    supplier_id: int
    query_days: int | None = None
    to_emails: str | None = None
    subject: str | None = None
    status: str
    punish_count: int = 0
    dispute_count: int = 0
    mail_send_log_id: int | None = None
    error_message: str | None = None
    provider_request_id: str | None = None
