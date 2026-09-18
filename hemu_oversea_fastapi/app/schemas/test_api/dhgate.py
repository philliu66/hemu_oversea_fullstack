"""敦煌官方 API 联调请求体（仅 testAPI，非业务接口）。"""

from typing import Literal

from pydantic import BaseModel, Field


class StoreIdBody(BaseModel):
    store_id: int = Field(description="店铺 ID，用于取该店 access_token")


class PunishBrandListTestRequest(StoreIdBody):
    third_type: Literal["brand", "other"] = Field(
        description="投诉类型：brand=品牌商投诉，other=其他第三方投诉",
    )
    page_no: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=100, ge=1, le=200, description="每页条数，1～200")


class PunishListTestRequest(StoreIdBody):
    start_date: str = Field(min_length=1, description="开始日期 yyyy-MM-dd")
    end_date: str = Field(min_length=1, description="结束日期 yyyy-MM-dd")
    punish_id: str | None = Field(default=None, description="处罚编号（可选）")
    page_no: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=100, ge=1, le=200, description="每页条数，1～200")


class CategoryListTestRequest(StoreIdBody):
    """单店铺递归拉取全部展示类目。"""


class CategoryGetTestRequest(StoreIdBody):
    cate_pub_id: str = Field(
        min_length=1,
        max_length=64,
        description="叶子发布类目 ID（catePubId，来自 dh.category.list）",
    )


class CategoryPathGetTestRequest(StoreIdBody):
    cate_pub_id: str = Field(
        min_length=1,
        max_length=64,
        description=(
            "叶子发布类目 ID（catePubId）；"
            "用于获取从根到该类目的主线路径 categoryPublishList"
        ),
    )


class ItemAftersaleListTestRequest(StoreIdBody):
    """获取当前店铺售后模板列表，无额外业务入参。"""


class ShippingTemplateListTestRequest(StoreIdBody):
    """获取当前店铺运费模板列表，无额外业务入参。"""


class ItemGetTestRequest(StoreIdBody):
    item_code: str = Field(
        min_length=1,
        max_length=64,
        description="商品编码 itemCode（来自 dh.item.list）",
    )
    site_id: Literal["EN", "RU", "ES", "ID"] = Field(
        default="EN",
        description="站点语言：EN=英语（默认）、RU=俄语、ES=西语、ID=印尼语",
    )


class ItemFissionUpdateInfo(BaseModel):
    """裂变时覆盖种子商品的字段；后续按业务继续加字段。"""

    item_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=140,
        description="裂变后的商品标题（对应 dh.item.add itemBase.itemName，最多 140 字符）",
    )
    afterSaleTemplateId: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="要发布的售后模板 ID；有值则直接使用，不再拉售后模板列表",
    )
    shippingTempId: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="要发布的运费模板 ID；有值则直接使用，不再拉运费模板列表",
    )


class ItemFissionAddTestRequest(BaseModel):
    target_store_id: int = Field(
        description="要发布到的目标店铺 ID；用该店 access_token 调用 dh.item.add",
    )
    pid: int = Field(
        ge=1,
        description="本地种子商品 ID（product_dh.id），用于查出源店 store_id / item_code",
    )
    update_info: ItemFissionUpdateInfo = Field(
        default_factory=ItemFissionUpdateInfo,
        description="裂变时覆盖种子详情的字段：标题、售后模板、运费模板等",
    )
    site_id: Literal["EN", "RU", "ES", "ID"] | None = Field(
        default=None,
        description="站点语言；不传则用种子商品 site_id，再默认 EN",
    )
