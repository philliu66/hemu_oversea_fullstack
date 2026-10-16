"""供应商每日店铺巡检设置。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_QUERY_DAYS = frozenset({3, 7, 10})


class SupplierInspectionScheduleGet(BaseModel):
    """查询某供应商的每日巡检设置。"""

    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID；供应商门户可省略，平台必传",
    )


class SupplierInspectionScheduleSave(BaseModel):
    """保存（新建或更新）每日巡检设置。"""

    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID；供应商门户可省略，平台必传",
    )
    query_days: int = Field(description="巡检天数，仅允许 3 / 7 / 10")
    emails: str = Field(
        min_length=1,
        description="收件邮箱，多个用英文逗号分隔",
    )

    @field_validator("query_days")
    @classmethod
    def validate_query_days(cls, value: int) -> int:
        if value not in ALLOWED_QUERY_DAYS:
            raise ValueError("巡检天数仅允许 3 / 7 / 10")
        return value

    @field_validator("emails")
    @classmethod
    def normalize_emails(cls, value: str) -> str:
        parts = [p.strip() for p in value.split(",")]
        emails = [p for p in parts if p]
        if not emails:
            raise ValueError("至少填写一个邮箱地址")
        for email in emails:
            if "@" not in email or "." not in email.split("@")[-1]:
                raise ValueError(f"邮箱格式不正确：{email}")
        return ",".join(emails)


class SupplierInspectionScheduleDelete(BaseModel):
    """删除某供应商的每日巡检设置。"""

    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID；供应商门户可省略，平台必传",
    )


class SupplierInspectionSchedulePublic(BaseModel):
    """每日巡检设置对外字段。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_id: int
    query_days: int
    emails: str
    created_at: datetime
    updated_at: datetime
    last_sent_at: datetime | None = None
    last_send_status: str | None = None
