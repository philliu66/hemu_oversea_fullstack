"""店铺巡检相关请求 / 响应。"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StoreInspectionPunishRequest(BaseModel):
    supplier_id: int = Field(description="供应商 ID（必传）")
    store_id: int | None = Field(
        default=None,
        description="店铺 ID（选传；传入则只查该店，不传则查该供应商下全部已授权敦煌店铺）",
    )
    query_days: int = Field(
        ge=1,
        le=365,
        description="查询天数（含当天；用于推算处罚列表的起止日期）",
    )
    page_no: int = Field(default=1, ge=1, description="页码，默认 1")
    page_size: int = Field(
        default=100,
        ge=1,
        le=200,
        description="每页条数，默认 100",
    )


class StoreInspectionPunishPublic(BaseModel):
    """前端展示用：仅返回 punishStatus 为 \"1\" 的处罚列表。"""

    model_config = ConfigDict(populate_by_name=True)

    items: list[dict[str, Any]] = Field(
        default_factory=list,
        alias="list",
        description=(
            "处罚列表（仅 punishStatus=\"1\"；"
            "每条含 store_id、store_identifier 及敦煌原始字段）"
        ),
    )
    start_date: str = Field(description="查询开始日期（含当天推算）")
    end_date: str = Field(description="查询结束日期（含当天推算）")


class StoreInspectionDisputeRequest(BaseModel):
    """店铺巡检：纠纷开启订单（v2 dh.order.disputeopen.list）。"""

    supplier_id: int = Field(description="供应商 ID（必传）")
    store_id: int | None = Field(
        default=None,
        description="店铺 ID（选传；传入则只查该店，不传则查该供应商下全部已授权敦煌店铺）",
    )
    page_no: int = Field(default=1, ge=1, description="页码，默认 1")
    page_size: int = Field(
        default=100,
        ge=1,
        le=200,
        description="每页条数，默认 100",
    )


class StoreInspectionDisputePublic(BaseModel):
    """前端展示用：纠纷开启订单列表。"""

    model_config = ConfigDict(populate_by_name=True)

    items: list[dict[str, Any]] = Field(
        default_factory=list,
        alias="list",
        description=(
            "纠纷开启订单列表（来自 orderDisputeOpenInfos；"
            "含 store_id / store_identifier；"
            "orderStatus / disputeStatus 已转中文文案（保留 *Code）；"
            "disputeOpenDate / openTime 为 yyyy-MM-dd HH:mm:ss；"
            "isWarn → is_high_risk；"
            "country / warnReason / orderTotalPrice 已做别名归一）"
        ),
    )
