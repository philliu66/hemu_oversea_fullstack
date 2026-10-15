"""SKU 属性模版相关请求 / 响应。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SkuAttrTemplateList(BaseModel):
    sku_code: str | None = Field(default=None, description="SKU 编码（模糊）")
    cate_pub_id: str | None = Field(default=None, description="叶子类目敦煌 ID")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略；平台身份必填",
    )


class SkuAttrTemplateDetail(BaseModel):
    id: int = Field(ge=1, description="模版 ID")
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略；平台身份必填",
    )


class SkuAttrTemplateDelete(BaseModel):
    id: int = Field(ge=1, description="模版 ID")
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略；平台身份必填",
    )


class SkuAttrTemplateCreate(BaseModel):
    sku_code: str = Field(min_length=1, description="SKU 编码型号")
    cate_pub_id: str = Field(min_length=1, description="叶子类目敦煌 ID")
    raw_json: dict[str, Any] = Field(
        description='属性快照，形如 {"attr_list": [...]}'
    )
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略；平台身份必填",
    )


class SkuAttrTemplateUpdate(BaseModel):
    id: int = Field(ge=1, description="模版 ID")
    sku_code: str = Field(min_length=1, description="SKU 编码型号")
    cate_pub_id: str = Field(min_length=1, description="叶子类目敦煌 ID")
    raw_json: dict[str, Any] = Field(
        description='属性快照，形如 {"attr_list": [...]}'
    )
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略；平台身份必填",
    )


class SkuAttrTemplateListItemPublic(BaseModel):
    id: int
    sku_code: str
    cate_pub_id: str
    cate_name: str | None = None
    category_id: int | None = None
    supplier_id: int | None = None
    supplier_name: str | None = None
    updated_at: datetime


class SkuAttrTemplatePublic(BaseModel):
    id: int
    supplier_id: int
    supplier_name: str | None = None
    sku_code: str
    cate_pub_id: str
    cate_name: str | None = None
    category_id: int | None = None
    raw_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by: int
    updated_by: int


class DhSkuBaseInfoList(BaseModel):
    keyword: str | None = Field(default=None, description="按 sku_code 模糊搜索")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(
        default=5000,
        ge=1,
        le=5000,
        description="每页条数；下拉全量加载可用较大值",
    )
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略；平台身份必填",
    )


class SkuAttrTemplateLookup(BaseModel):
    cate_pub_id: str = Field(min_length=1, description="叶子类目敦煌 ID")
    sku_codes: list[str] = Field(
        min_length=1,
        max_length=100,
        description="产品基型号列表（将统一清洗并去变体后缀）",
    )
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略；平台身份必填",
    )


class SkuAttrTemplateLookupItemPublic(BaseModel):
    sku_code: str = Field(description="归类后的基型号")
    found: bool = Field(description="是否存在属性模板")
    raw_json: dict[str, Any] | None = Field(
        default=None,
        description="找到时的属性快照",
    )


class SkuAttrTemplateLookupPublic(BaseModel):
    items: list[SkuAttrTemplateLookupItemPublic]
