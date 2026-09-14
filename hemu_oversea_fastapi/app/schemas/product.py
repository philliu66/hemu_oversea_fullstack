"""商品 / 类目相关请求与响应。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# 敦煌一级类目的父 ID（平台约定）
DHGATE_ROOT_PARE_CATE_PUB_ID = "00000000000000000000000000000000"


class DhCategoryListRequest(BaseModel):
    parent_id: str | None = Field(
        default=None,
        description=(
            "父类目 cate_pub_id；不传或空字符串表示查询一级（根）类目"
        ),
    )


class DhCategorySearchRequest(BaseModel):
    keyword: str = Field(
        description="按中英文类目名称模糊搜索",
        min_length=1,
        max_length=100,
    )
    leaf_only: bool = Field(
        default=True,
        description="是否仅返回叶子类目（商品可选类目）",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="返回条数上限",
    )


class DhCategoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cate_pub_id: str = Field(description="发布类目 ID")
    pub_name: str = Field(description="英文名称")
    pub_name_cn: str | None = Field(default=None, description="中文名称")
    remark: str | None = Field(default=None, description="备注")
    leaf: str = Field(description="是否叶子：1=是，0=否")
    pare_cate_pub_id: str | None = Field(default=None, description="父类目 ID")
    is_leaf: bool = Field(description="是否叶子类目（便于前端判断可否继续下钻）")


class DhCategoryPathRequest(BaseModel):
    id: int = Field(
        description="类目 ID（product_category_dh.id）",
        ge=1,
    )


class DhCategoryPathPublic(BaseModel):
    """类目从根到叶子的全路径。"""

    id: int = Field(description="类目主键 ID")
    cate_pub_id: str = Field(description="发布类目 ID")
    path_name: str = Field(
        description="全路径名称，格式：中文(英文) > 中文(英文) > …",
    )
    path_items: list[DhCategoryPublic] = Field(
        default_factory=list,
        description="路径节点列表（由根到当前，顺序与 path_name 一致）",
    )


class DhCategoryAttrsRequest(BaseModel):
    id: int = Field(
        description="类目 ID（product_category_dh.id），须为叶子类目",
        ge=1,
    )


class DhCategoryAttrValPublic(BaseModel):
    """类目属性可选值。"""

    cate_pub_attrval_id: int | None = Field(
        default=None,
        description="属性值主键 catePubAttrvalId",
    )
    cate_pub_attr_id: int | None = Field(
        default=None,
        description="所属类目属性 ID catePubAttrId",
    )
    attr_val_id: str = Field(description="属性值 ID attrValId")
    pic_url: str | None = Field(default=None, description="属性值图片 picUrl")
    line_attrval_name: str | None = Field(
        default=None,
        description="属性值英文名",
    )
    line_attrval_name_cn: str | None = Field(
        default=None,
        description="属性值中文名",
    )


class DhCategoryAttrPublic(BaseModel):
    """类目属性定义（供表单渲染）。"""

    cate_pub_attr_id: int | None = Field(
        default=None,
        description="类目属性主键 catePubAttrId",
    )
    attr_id: str = Field(description="属性 ID attrId")
    cate_pub_id: str | None = Field(default=None, description="发布类目 ID")
    required: str = Field(description="是否必填：1=是，0=否")
    located: str = Field(description="是否地点属性：1=是，0=否")
    sale_attr: str = Field(description="是否销售属性：1=是，0=否")
    buy_attr: str = Field(description="是否购买属性：1=是，0=否")
    style: str = Field(
        description="展示形态：1=文本，2=图片，3=图文",
    )
    type: str = Field(
        description="控件类型：1=多选框，2=下拉框，4=文本框，5=数字框",
    )
    defined: str = Field(description="属性值是否可修改：1=是，0=否")
    is_brand: str = Field(description="是否品牌属性：1=是，0=否")
    line_attr_name: str | None = Field(default=None, description="属性英文名")
    line_attr_name_cn: str | None = Field(default=None, description="属性中文名")
    isother: str = Field(description="是否支持自定义/其他：1=是，0=否")
    child_attr_id: str | None = Field(default=None, description="子属性 ID")
    values: list[DhCategoryAttrValPublic] = Field(
        default_factory=list,
        description="可选属性值列表",
    )


class DhCategoryAttrsPublic(BaseModel):
    """叶子类目下的属性定义。"""

    id: int = Field(description="类目主键 ID")
    cate_pub_id: str = Field(description="发布类目 ID")
    pub_name: str = Field(description="英文名称")
    pub_name_cn: str | None = Field(default=None, description="中文名称")
    leaf: str = Field(description="是否叶子：1=是，0=否")
    attrs: list[DhCategoryAttrPublic] = Field(
        default_factory=list,
        description="类目属性列表",
    )


class DhProductListRequest(BaseModel):
    type: int = Field(
        default=1,
        ge=0,
        le=1,
        description="商品类型：0=全部，1=仅种子商品（is_seed=1），默认 1",
    )
    state: str | None = Field(
        default=None,
        description=(
            "商品状态编码筛选：100000未定义 / 100100上架产品 / 100200待审核产品 / "
            "100300审核未通过产品 / 100400下架产品 / 100500品牌商投诉产品 / "
            "100600疑似侵权产品 / 100700内容违规品"
        ),
    )
    item_code: str | None = Field(
        default=None,
        description="商品编码 itemCode（精确匹配）",
    )
    item_name: str | None = Field(
        default=None,
        description="商品标题（模糊匹配）",
    )
    store_id: int | None = Field(
        default=None,
        description="店铺 ID（精确匹配）",
    )
    sort: int = Field(
        default=0,
        ge=0,
        le=1,
        description="排序：0=同步时间倒序（默认），1=同步时间正序",
    )
    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class DhProductPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int = Field(description="店铺 ID")
    item_code: str = Field(description="商品编码")
    site_id: str = Field(description="站点语言")
    is_seed: str = Field(description="是否种子：1=是，0=否")
    supplier_id: str | None = Field(default=None, description="平台卖家 ID")
    cate_pub_id: str | None = Field(default=None, description="发布类目 ID")
    state: str | None = Field(
        default=None,
        description=(
            "商品状态描述：未定义/上架产品/待审核产品/审核未通过产品/"
            "下架产品/品牌商投诉产品/疑似侵权产品/内容违规品"
        ),
    )
    item_name: str | None = Field(default=None, description="商品标题")
    short_desc: str | None = Field(default=None, description="简短介绍")
    min_wholesale_qty: int | None = Field(default=None, description="最小起批量")
    max_sale_qty: int | None = Field(default=None, description="单次最大购买量")
    leading_time: int | None = Field(default=None, description="备货天数")
    price_min: Decimal | None = Field(default=None, description="最低价")
    price_max: Decimal | None = Field(default=None, description="最高价")
    sku_count: int | None = Field(default=None, description="SKU 数量")
    total_inventory: int | None = Field(default=None, description="库存合计")
    main_image_url: str | None = Field(
        default=None,
        description="主图完整 URL（相对路径会补前缀 http://image.dhgate.com/100x100/）",
    )
    expire_date: datetime | None = Field(default=None, description="过期时间")
    operate_date: datetime | None = Field(default=None, description="平台最后修改时间")
    last_synced_at: datetime | None = Field(default=None, description="最近同步时间")
    sync_state: str = Field(description="同步状态：1=成功，0=失败")
    sync_state_desc: str | None = Field(default=None, description="同步状态描述")
    created_at: datetime
    updated_at: datetime


class DhProductDetailRequest(BaseModel):
    id: int = Field(description="商品 ID（product_dh.id）", ge=1)


class DhProductSelectedAttrValPublic(BaseModel):
    """产品属性值（对应 dh.item.get itemAttrValList）。"""

    attr_val_id: str | None = Field(
        default=None,
        description="属性值 ID；自定义属性可从 1 累加，也可不填",
    )
    attr_name: str | None = Field(
        default=None,
        description="值级属性英文名（自定义属性的属性名，如 Function/Voltage）",
    )
    attr_name_cn: str | None = Field(
        default=None,
        description="值级属性中文名",
    )
    line_attrval_name: str | None = Field(default=None, description="属性值英文名")
    line_attrval_name_cn: str | None = Field(
        default=None,
        description="属性值中文名",
    )
    pic_url: str | None = Field(default=None, description="属性值图片完整 URL")
    brand_id: str | None = Field(default=None, description="品牌 ID")


class DhProductSelectedAttrPublic(BaseModel):
    """商品产品属性（对应 dh.item.get itemAttrList，仅展示，不参与 SKU）。

    官方区分规则：attr_id=11 自定义属性；attr_id=99 品牌属性；其余为类目属性。
    """

    attr_id: str = Field(description="属性 ID")
    attr_name: str | None = Field(default=None, description="属性英文名")
    attr_name_cn: str | None = Field(default=None, description="属性中文名")
    is_brand: str | None = Field(
        default=None,
        description="是否品牌属性：0/1",
    )
    values: list[DhProductSelectedAttrValPublic] = Field(default_factory=list)


class DhProductSpecSelfDefPublic(BaseModel):
    """自定义规格（对应 dh.item.get itemSpecSelfDefList）。"""

    attr_val_id: str | None = Field(
        default=None,
        description="自定义规格值 ID（attrValId，平台从 1000 起）",
    )
    spec_attr_name: str | None = Field(
        default=None,
        description="规格属性英文名（specAttrName，默认 Options）",
    )
    attr_val_name: str | None = Field(
        default=None,
        description="规格值名称（attrValName）",
    )
    pic_url: str | None = Field(
        default=None,
        description="规格图片完整 URL（picUrl）",
    )


class DhProductSkuPublic(BaseModel):
    """敦煌商品 SKU 展示字段。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    sku_id: str | None = Field(default=None, description="平台 SKU ID")
    sku_code: str | None = Field(default=None, description="卖家自定义 SKU 编码")
    retail_price: Decimal | None = Field(default=None, description="零售价")
    inventory: int | None = Field(default=None, description="库存")
    sale_status: str | None = Field(
        default=None,
        description="是否可售：0不可售/1可售",
    )
    pic_url: str | None = Field(default=None, description="SKU 图片完整 URL")
    attr_combo_text: str | None = Field(
        default=None,
        description="属性组合展示文案",
    )


class DhProductDetailPublic(BaseModel):
    """敦煌商品详情（前端展示必要字段，不含 raw/ext 等大字段）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int = Field(description="店铺 ID")
    item_code: str = Field(description="商品编码")
    site_id: str = Field(description="站点语言")
    is_seed: str = Field(description="是否种子：1=是，0=否")
    supplier_id: str | None = Field(default=None, description="平台卖家 ID")
    cate_pub_id: str | None = Field(default=None, description="发布类目 ID")
    state: str | None = Field(
        default=None,
        description="商品状态描述",
    )
    item_name: str | None = Field(default=None, description="商品标题")
    short_desc: str | None = Field(default=None, description="简短介绍")
    html_content: str | None = Field(default=None, description="详情 HTML")
    key_word1: str | None = Field(default=None, description="关键词1")
    key_word2: str | None = Field(default=None, description="关键词2")
    key_word3: str | None = Field(default=None, description="关键词3")
    video_url: str | None = Field(default=None, description="视频地址")
    min_wholesale_qty: int | None = Field(default=None, description="最小起批量")
    max_sale_qty: int | None = Field(default=None, description="单次最大购买量")
    leading_time: int | None = Field(default=None, description="备货天数")
    price_config_type: str | None = Field(
        default=None,
        description="定价方式：1单独/2统一",
    )
    gross_weight: Decimal | None = Field(default=None, description="包装毛重 kg")
    length: Decimal | None = Field(default=None, description="包装长 cm")
    width: Decimal | None = Field(default=None, description="包装宽 cm")
    height: Decimal | None = Field(default=None, description="包装高 cm")
    packing_quantity: int | None = Field(default=None, description="每包件数")
    price_min: Decimal | None = Field(default=None, description="最低价")
    price_max: Decimal | None = Field(default=None, description="最高价")
    sku_count: int | None = Field(default=None, description="SKU 数量")
    total_inventory: int | None = Field(default=None, description="库存合计")
    issample: str | None = Field(
        default=None,
        description="是否成人用品：2是/3否",
    )
    is_dh_optimized: str | None = Field(
        default=None,
        description="是否敦煌优选：0/1",
    )
    vaild_day: str | None = Field(default=None, description="有效天数")
    expire_date: datetime | None = Field(default=None, description="过期时间")
    operate_date: datetime | None = Field(default=None, description="平台最后修改时间")
    last_synced_at: datetime | None = Field(default=None, description="最近同步时间")
    sync_state: str = Field(description="同步状态：1=成功，0=失败")
    sync_state_desc: str | None = Field(default=None, description="同步状态描述")
    created_at: datetime
    updated_at: datetime
    img_list: list[str] = Field(
        default_factory=list,
        description="商品图片完整 URL 列表（按 sort 升序，前缀 https://image.dhgate.com/）",
    )
    sku_list: list[DhProductSkuPublic] = Field(
        default_factory=list,
        description="商品 SKU 列表",
    )
    category: DhCategoryPublic | None = Field(
        default=None,
        description="所属发布类目（按 cate_pub_id 关联 product_category_dh）",
    )
    attr_list: list[DhProductSelectedAttrPublic] = Field(
        default_factory=list,
        description=(
            "产品属性（itemAttrList）：类目属性 + 品牌属性(attr_id=99) + "
            "自定义属性(attr_id=11)，仅展示不参与 SKU"
        ),
    )
    item_spec_self_def_list: list[DhProductSpecSelfDefPublic] = Field(
        default_factory=list,
        description="自定义规格列表（itemSpecSelfDefList）",
    )