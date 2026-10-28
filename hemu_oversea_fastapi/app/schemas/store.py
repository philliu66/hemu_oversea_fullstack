from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.store_types import StoreType


class StoreCreate(BaseModel):
    store_type: StoreType = Field(description="店铺类型：dhgate / tiktok")
    name: str = Field(min_length=1, max_length=100, description="店铺名称")
    identifier: str = Field(min_length=1, max_length=100, description="店铺标识")
    base_discount: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        le=Decimal("0.99"),
        max_digits=3,
        decimal_places=2,
        description="基础折扣（0.00～0.99）",
    )
    account: str = Field(min_length=1, max_length=100, description="店铺账号")
    password: str = Field(min_length=1, max_length=255, description="店铺密码")
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略；平台身份必填",
    )


class StoreUpdate(BaseModel):
    id: int = Field(description="店铺 ID")
    store_type: StoreType | None = Field(default=None, description="店铺类型")
    name: str | None = Field(default=None, min_length=1, max_length=100)
    identifier: str | None = Field(default=None, min_length=1, max_length=100)
    base_discount: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("0.99"),
        max_digits=3,
        decimal_places=2,
        description="基础折扣（0.00～0.99）",
    )
    account: str | None = Field(default=None, min_length=1, max_length=100)
    password: str | None = Field(default=None, min_length=1, max_length=255)


class StoreDelete(BaseModel):
    id: int = Field(description="店铺 ID")


class StoreDetail(BaseModel):
    id: int = Field(description="店铺 ID")


class StoreBaseDiscountRequest(BaseModel):
    id: int = Field(ge=1, description="店铺 ID")


class StoreBaseDiscountPublic(BaseModel):
    """店铺基础折扣率。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="店铺 ID")
    name: str = Field(description="店铺名称")
    base_discount: Decimal = Field(description="基础折扣率（0.00～0.99）")


class StoreTemplateListRequest(BaseModel):
    store_id: int = Field(ge=1, description="店铺 ID")


class StoreGroupListRequest(BaseModel):
    store_id: int = Field(description="店铺 ID", ge=1)
    keyword: str | None = Field(
        default=None,
        max_length=128,
        description="按分组中英文名称筛选，含子分组（可选）",
    )
    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=20, ge=1, le=500, description="每页条数")


class StoreAftersaleTemplatePublic(BaseModel):
    after_sale_template_id: str = Field(description="售后模板 ID afterSaleTemplateId")
    name: str | None = Field(default=None, description="模板名称")
    if_template_default: str | None = Field(
        default=None, description="是否默认模板，1 为默认"
    )


class StoreShippingTemplatePublic(BaseModel):
    shipping_model_id: str = Field(
        description="物流模板 ID，对应商品 shippingModelId / 接口 shippingTempId"
    )
    name: str | None = Field(default=None, description="模板名称")
    model_type: str | None = Field(
        default=None, description="模板类型，10 为新手运费模板"
    )


class StoreList(BaseModel):
    keyword: str | None = Field(
        default=None,
        description="按名称、标识或账号模糊搜索",
    )
    store_type: StoreType | None = Field(default=None, description="按店铺类型筛选")
    supplier_id: int | None = Field(default=None, description="按供应商筛选")
    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class StoreAuthorize(BaseModel):
    id: int = Field(description="店铺 ID")


class StoreAuthorizePublic(BaseModel):
    store_id: int
    store_type: str = Field(description="店铺类型：dhgate / tiktok")
    authorize_url: str = Field(description="跳转平台授权页的完整 URL")


class StoreTiktokAuthorize(BaseModel):
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略；平台身份必填",
    )


class StoreTiktokAuthorizePublic(BaseModel):
    store_type: str = Field(description="店铺类型：tiktok")
    authorize_url: str = Field(description="跳转 TikTok 授权页的完整 URL")


class StorePublic(BaseModel):
    """列表 / 创建 / 更新对外返回：不含密码与 token 细节。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_id: int | None = Field(description="所属供应商 ID")
    supplier_name: str | None = Field(default=None, description="供应商名称")
    store_type: str
    name: str
    identifier: str
    base_discount: Decimal = Field(description="基础折扣（0.00～0.99）")
    oauth_status: int = Field(
        description="授权状态：0 未授权，1 已授权，2 授权已过期",
    )
    refresh_token_expires_at: datetime | None = Field(
        default=None,
        description="refresh_token 到期时间",
    )
    platform_region: str | None = Field(default=None, description="TikTok 店铺区域")
    platform_shop_code: str | None = Field(
        default=None,
        description="TikTok 店铺代码",
    )
    platform_seller_type: str | None = Field(
        default=None,
        description="TikTok 卖家类型：LOCAL / CROSS_BORDER",
    )
    created_by: str | None = Field(description="创建人用户名")
    updated_by: str | None = Field(description="更新人用户名")
    created_at: datetime
    updated_at: datetime


class StoreDetailPublic(BaseModel):
    """详情：在列表字段基础上额外返回账号、密码。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_id: int | None = Field(description="所属供应商 ID")
    supplier_name: str | None = Field(default=None, description="供应商名称")
    store_type: str
    name: str
    identifier: str
    base_discount: Decimal = Field(description="基础折扣（0.00～0.99）")
    account: str = Field(description="店铺账号")
    password: str = Field(description="店铺密码")
    oauth_status: int = Field(
        description="授权状态：0 未授权，1 已授权，2 授权已过期",
    )
    refresh_token_expires_at: datetime | None = Field(
        default=None,
        description="refresh_token 到期时间",
    )
    platform_region: str | None = Field(default=None, description="TikTok 店铺区域")
    platform_shop_code: str | None = Field(
        default=None,
        description="TikTok 店铺代码",
    )
    platform_seller_type: str | None = Field(
        default=None,
        description="TikTok 卖家类型：LOCAL / CROSS_BORDER",
    )
    created_by: str | None = Field(description="创建人用户名")
    updated_by: str | None = Field(description="更新人用户名")
    created_at: datetime
    updated_at: datetime
