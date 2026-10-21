"""敦煌多店铺编排联调请求体（仅 testAPI，非业务接口）。

路径前缀：/api/v1/common/testAPI/dhgate/commerce
"""

from typing import Literal

from pydantic import BaseModel, Field


class PunishSummaryTestRequest(BaseModel):
    """联调：汇总单店/多店处罚信息（平台处罚 + 品牌/其他第三方投诉）。"""

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
    page_no: int = Field(default=1, ge=1, description="页码，默认 1（三类处罚共用）")
    page_size: int = Field(
        default=100,
        ge=1,
        le=200,
        description="每页条数，默认 100（三类处罚共用）",
    )


class DisputeProcessingSummaryTestRequest(BaseModel):
    """联调 v1：汇总单店/多店进行中纠纷订单（dh.dispute.processing.list$1.0）。"""

    supplier_id: int = Field(description="供应商 ID（必传）")
    store_id: int | None = Field(
        default=None,
        description="店铺 ID（选传；传入则只查该店，不传则查该供应商下全部已授权敦煌店铺）",
    )
    dispute_status: str = Field(
        min_length=1,
        max_length=64,
        description=(
            "【官方必填】disputeStatus（各店共用）。"
            "可参考：`106001`/`106003`/`107001`/`107002`/`107003`/`109001`/`109002`；"
            "详见单店联调 /dispute/processing/list 注释。"
        ),
        examples=["109001"],
    )
    page_num: int = Field(
        default=1,
        ge=1,
        description="【官方可选】pageNum 页码，默认 1",
    )
    page_size: int = Field(
        default=100,
        ge=1,
        le=200,
        description="【官方可选】pageSize 每页条数，默认 100，范围 1～200",
    )
    start_time: str | None = Field(
        default=None,
        description="【官方可选】startTime 开始时间（各店共用）",
    )
    end_time: str | None = Field(
        default=None,
        description="【官方可选】endTime 结束时间（各店共用）",
    )


class DisputeOpenSummaryTestRequest(BaseModel):
    """联调 v2：汇总单店/多店当前开启中的纠纷订单（dh.order.disputeopen.list$2.0）。"""

    supplier_id: int = Field(description="供应商 ID（必传）")
    store_id: int | None = Field(
        default=None,
        description="店铺 ID（选传；传入则只查该店，不传则查该供应商下全部已授权敦煌店铺）",
    )
    page_no: int = Field(
        default=1,
        ge=1,
        description="【官方必填】pageNo 页码，默认 1",
    )
    page_size: int = Field(
        default=100,
        ge=1,
        le=200,
        description="【官方必填】pageSize 每页条数，默认 100，范围 1～200",
    )


class ProductSyncItem(BaseModel):
    store_identifier: str = Field(
        min_length=1,
        max_length=100,
        description="店铺唯一标识（stores.identifier）",
    )
    item_code: str = Field(
        min_length=1,
        max_length=64,
        description="商品编码 itemCode",
    )
    site_id: Literal["EN", "RU", "ES", "ID"] = Field(
        default="EN",
        description=(
            "【官方可选】siteId 站点语言，默认 EN。"
            "可选值：`EN` / `RU` / `ES` / `ID`"
        ),
    )


class ProductSyncTestRequest(BaseModel):
    items: list[ProductSyncItem] = Field(
        min_length=1,
        description="待同步商品列表（可跨店铺）",
    )


class ProductGroupSyncTestRequest(BaseModel):
    """按供应商同步其下敦煌店铺的产品分组。"""

    supplier_id: int = Field(description="供应商 ID（必传）", ge=1)


class ShippingTemplateSyncTestRequest(BaseModel):
    """按供应商同步其下敦煌店铺的运费模板。"""

    supplier_id: int = Field(description="供应商 ID（必传）", ge=1)


class AftersaleTemplateSyncTestRequest(BaseModel):
    """按供应商同步其下敦煌店铺的售后模板。"""

    supplier_id: int = Field(description="供应商 ID（必传）", ge=1)
