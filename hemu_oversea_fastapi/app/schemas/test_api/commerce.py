"""敦煌多店铺编排联调请求体（仅 testAPI，非业务接口）。

路径前缀：/api/v1/common/testAPI/dhgate/commerce
"""

from typing import Literal

from pydantic import BaseModel, Field


class PunishSummaryTestRequest(BaseModel):
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
        description="站点语言，默认 EN",
    )


class ProductSyncTestRequest(BaseModel):
    items: list[ProductSyncItem] = Field(
        min_length=1,
        description="待同步商品列表（可跨店铺）",
    )
