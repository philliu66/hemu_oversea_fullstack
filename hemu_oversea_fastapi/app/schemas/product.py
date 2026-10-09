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


class DhSeedCategoryPublic(DhCategoryPublic):
    """种子商品涉及的类目，带该类目下种子商品数量。"""

    product_count: int = Field(
        description="该类目下种子商品数量（含子类目汇总）",
        ge=0,
    )


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


class DhCommissionUnitPublic(BaseModel):
    """阶梯佣金区间（对应 unitList 项）。"""

    left_bound: str | None = Field(default=None, description="区间左边界 leftBound")
    right_bound: str | None = Field(default=None, description="区间右边界 rightBound")
    left_bound_close: bool | None = Field(
        default=None, description="左边界是否闭合 leftBoundClose"
    )
    right_bound_close: bool | None = Field(
        default=None, description="右边界是否闭合 rightBoundClose"
    )
    commission_rate: str | None = Field(
        default=None, description="佣金率 commissionRate"
    )


class DhCommissionRatePublic(BaseModel):
    """类目佣金率（对应 LadderCommissionRateVO / commissions_rate_dh）。

    官方按二级类目绑定；当前查询接口暂固定返回参考定价类目（000000）。
    """

    cate_id: str = Field(description="二级类目 ID cateId")
    unit_list: list[DhCommissionUnitPublic] = Field(
        default_factory=list,
        description="阶梯佣金率 unitList",
    )


class DhCommissionRateRequest(BaseModel):
    cate_id: str = Field(
        min_length=1,
        max_length=64,
        description=(
            "二级类目 ID（兼容前端传入）；"
            "当前后端暂忽略该值，固定按参考定价类目 000000 查询"
        ),
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
    cate_pub_id: str | None = Field(
        default=None,
        description=(
            "发布类目 ID；传入后筛选该类目及其全部下级类目下的商品，"
            "不传表示全部类目"
        ),
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
    store_name: str | None = Field(default=None, description="店铺名称")
    item_code: str = Field(description="商品编码")
    site_id: str = Field(description="站点语言")
    is_seed: str = Field(description="是否种子：1=是，0=否")
    cate_pub_id: str | None = Field(default=None, description="发布类目 ID")
    state: str | None = Field(
        default=None,
        description=(
            "商品状态描述：未定义/上架产品/待审核产品/审核未通过产品/"
            "下架产品/品牌商投诉产品/疑似侵权产品/内容违规品"
        ),
    )
    item_name: str | None = Field(default=None, description="商品标题")
    main_image_url: str | None = Field(
        default=None,
        description="主图完整 URL（相对路径会补前缀 http://image.dhgate.com/100x100/）",
    )
    last_synced_at: datetime | None = Field(default=None, description="最近同步时间")
    sync_state: str = Field(description="同步状态：1=成功，0=失败")


class DhProductDetailRequest(BaseModel):
    id: int = Field(description="商品 ID（product_dh.id）", ge=1)


# 定价参考类目默认 cate_id（与前端 / 佣金查询一致）
DH_REF_PRICING_CATE_ID = "000000"


class DhSkuListPriceRequest(BaseModel):
    """计算 SKU 标价的入参。"""

    supplier_id: int = Field(ge=1, description="供应商 ID")
    sku_code: str = Field(min_length=1, description="SKU 编码（可含后缀，后端会清洗）")
    store_id: int = Field(ge=1, description="当前店铺 ID（取店铺折扣率）")
    cate_id: str = Field(
        default=DH_REF_PRICING_CATE_ID,
        min_length=1,
        max_length=64,
        description=f"定价参考类目 ID，默认 {DH_REF_PRICING_CATE_ID}",
    )


class DhSkuListPricePublic(BaseModel):
    """SKU 标价计算结果。

    标价 = 基础价格 × 打包数 ×（1 − 佣金率）/ 店铺折扣
    订单金额 = 基础价格 × 打包数 × 起订量，用于匹配类目佣金区间。
    """

    supplier_id: int = Field(description="供应商 ID")
    sku_code: str = Field(description="清洗后的 SKU 编码")
    store_id: int = Field(description="店铺 ID")
    cate_id: str = Field(description="定价参考类目 ID")
    unit_price: Decimal = Field(description="基础价格（美元）")
    packing_quantity: int = Field(description="打包数")
    min_wholesale_qty: int = Field(description="起订量")
    sales_unit: int = Field(description="销售单元 = 打包数 × 起订量")
    order_amount: Decimal = Field(description="订单金额 = 基础价格 × 销售单元")
    commission_rate: Decimal = Field(description="命中区间的佣金率（小数，如 0.08）")
    base_discount: Decimal = Field(description="店铺折扣率（小数，如 0.85）")
    list_price: Decimal = Field(description="标价（美元，保留两位小数）")


class DhMeasuresUnitPublic(BaseModel):
    """计件单位（对应 dh.base.measures.get MeasureVO / measures_unit_dh）。"""

    measure_id: str = Field(description="计量单位 ID（measureid）")
    name: str | None = Field(default=None, description="英文名称（name）")
    description: str | None = Field(default=None, description="描述（description）")
    valid: str | None = Field(
        default=None, description="是否有效（valid）：1有效/0无效"
    )
    cname: str | None = Field(default=None, description="中文名称（cname）")
    short_name: str | None = Field(default=None, description="英文缩写（shortname）")
    plural: str | None = Field(default=None, description="英文复数（plural）")


class DhItemWholesaleRangePublic(BaseModel):
    """产品折扣区间（对应 dh.item.get itemWholesaleRangeList）。"""

    discount: Decimal | None = Field(default=None, description="折扣率 discount")
    start_qty: int | None = Field(default=None, description="折扣起件 startQty")


class DhItemWeightRangePublic(BaseModel):
    """包装阶梯重量（对应 itemPackage.itemWeigthRange，官方拼写）。"""

    base_qt: int | None = Field(default=None, description="基本数量 baseQt")
    step_qt: int | None = Field(default=None, description="阶梯数量 stepQt")
    step_weight: Decimal | None = Field(default=None, description="阶梯重量 stepWeight")


class DhItemShiptoSkuPricePublic(BaseModel):
    """销售国家定价（对应 shiptoCountryPriceList）。"""

    region_code: str | None = Field(default=None, description="区域编码 regionCode")
    retail_price: Decimal | None = Field(default=None, description="售往该区域价格 retailPrice")


class DhItemSkuInventoryPublic(BaseModel):
    """SKU 备货地址关联（对应 itemSkuInventoryList）。"""

    sku_md5: str | None = Field(default=None, description="skuMD5")
    inventory_location: str | None = Field(
        default=None, description="备货地址编码 inventoryLocation"
    )
    sku_inventory_qty: int | None = Field(
        default=None, description="该地址 SKU 备货数量 skuInventoryQty"
    )


class DhItemSkuAttrValPublic(BaseModel):
    """SKU 属性值（对应 itemSkuAttrValueList）。"""

    attr_id: str | None = Field(default=None, description="sku 属性 id attrId")
    attr_val_id: str | None = Field(default=None, description="sku 属性值 id attrValId")
    attr_val_code: str | None = Field(
        default=None, description="属性值编码 attrValCode（多地备货）"
    )
    size_spec_type: str | None = Field(
        default=None,
        description="规格类型 sizeSpecType：1产品规格/3自定义规格/4备货地规格",
    )


class DhItemInventoryLocationPublic(BaseModel):
    """备货地址（对应 itemInventory.inventoryLocationList）。"""

    sort_val: int | None = Field(default=None, description="备货地址排序 sortVal")
    leading_time: int | None = Field(default=None, description="该地址备货期 leadingTime")
    inventory_location: str | None = Field(
        default=None, description="备货地址编码 inventoryLocation"
    )
    if_in_transit: str | None = Field(
        default=None, description="是否备货途中 ifInTransit：0否/1是"
    )


class DhItemInventoryPublic(BaseModel):
    """产品备货信息（对应 itemInventory）。"""

    inventory_location: str | None = Field(
        default=None, description="产品备货地 inventoryLocation"
    )
    inventory_status: str | None = Field(
        default=None, description="是否有备货 inventoryStatus：0否/1是"
    )
    subtract_stock_type: str | None = Field(
        default=None,
        description="扣减库存类型 subtractStockType：1下单扣减/2支付完成扣减",
    )
    inventory_ori_qty: int | None = Field(
        default=None, description="产品原备货量 inventoryOriQty"
    )
    inventory_qty: int | None = Field(default=None, description="产品备货数量 inventoryQty")
    inventory_location_list: list[DhItemInventoryLocationPublic] = Field(
        default_factory=list,
        description="备货地址列表 inventoryLocationList",
    )


class DhItemShiptoSettingPublic(BaseModel):
    """销售国家定价区域（对应 itemShiptoSettingList）。"""

    region_code: str | None = Field(default=None, description="区域编码 regionCode")
    shipto_country_list: list[str] = Field(
        default_factory=list, description="销售国家 shiptoCountryList"
    )
    item_wholesale_range_list: list[DhItemWholesaleRangePublic] = Field(
        default_factory=list,
        description="该区域折扣区间 itemWholesaleRangeList",
    )


class DhItemCustomTypeInfoPublic(BaseModel):
    """定制商品信息（对应 itemCustomTypeInfo）。"""

    custom_type: str | None = Field(default=None, description="定制服务 customType")
    retail_price: Decimal | None = Field(default=None, description="定制产品零售价")
    min_wholesale_qty: int | None = Field(default=None, description="最小起批量")
    max_sale_qty: int | None = Field(default=None, description="单次最大购买量")
    leading_time: int | None = Field(default=None, description="定制备货期")
    sku_code: str | None = Field(default=None, description="定制 SKU 编码")
    sale_status: str | None = Field(default=None, description="是否可销售：0/1")
    shipto_country_price_list: list[DhItemShiptoSkuPricePublic] = Field(
        default_factory=list,
        description="定制销售国家定价 shiptoCountryPriceList",
    )


class DhItemAttrGroupDetailPublic(BaseModel):
    """兼容属性值（对应 itemAttrgroupDetailList）。"""

    attr_id: str | None = Field(default=None, description="属性 Id")
    attr_val_id: str | None = Field(default=None, description="属性值 id")
    attr_name: str | None = Field(default=None, description="兼容属性英文名")
    attr_name_cn: str | None = Field(default=None, description="兼容属性中文名")
    line_attrval_name: str | None = Field(default=None, description="兼容属性值英文名")
    line_attrval_name_cn: str | None = Field(default=None, description="兼容属性值中文名")


class DhItemAttrGroupPublic(BaseModel):
    """产品兼容属性组（对应 itemAttrGroupList）。"""

    item_attrgroup_detail_list: list[DhItemAttrGroupDetailPublic] = Field(
        default_factory=list,
        description="兼容性属性值列表 itemAttrgroupDetailList",
    )


class DhProductSelectedAttrValPublic(BaseModel):
    """产品属性值（对应 dh.item.get itemAttrValList）。"""

    attr_id: str | None = Field(default=None, description="属性 Id")
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
    pic_url: str | None = Field(
        default=None, description="属性值图片 picUrl，官方相对路径原样返回"
    )
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
        description="是否品牌属性 isbrand：0/1",
    )
    is_price_attr: str | None = Field(
        default=None,
        description="是否影响价格 isPriceAttr：0否/1是",
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
        description="规格图片 picUrl，官方相对路径原样返回",
    )


class DhProductSkuPublic(BaseModel):
    """敦煌商品 SKU（对应 dh.item.get itemSkuList）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="前端行号，非平台字段")
    sku_id: str | None = Field(default=None, description="平台 SKU ID skuId")
    sku_code: str | None = Field(default=None, description="卖家自定义 SKU 编码 skuCode")
    sku_md5: str | None = Field(default=None, description="SKU 属性 MD5 skuMD5")
    retail_price: Decimal | None = Field(default=None, description="零售价 retailPrice")
    inventory: int | None = Field(default=None, description="备货数量 inventory")
    sale_status: str | None = Field(
        default=None,
        description="是否可售 saleStatus：0不可售/1可售",
    )
    pic_url: str | None = Field(
        default=None, description="SKU 图片 picUrl，官方相对路径原样返回"
    )
    attr_combo_text: str | None = Field(
        default=None,
        description="属性组合展示文案（业务派生，非官网字段）",
    )
    item_sku_attr_value_list: list[DhItemSkuAttrValPublic] = Field(
        default_factory=list,
        description="SKU 属性值列表 itemSkuAttrValueList",
    )
    item_sku_inventory_list: list[DhItemSkuInventoryPublic] = Field(
        default_factory=list,
        description="SKU 备货地址关联 itemSkuInventoryList",
    )
    shipto_country_price_list: list[DhItemShiptoSkuPricePublic] = Field(
        default_factory=list,
        description="SKU 销售国家定价 shiptoCountryPriceList",
    )


class DhProductImgPublic(BaseModel):
    """产品图片（对应 dh.item.get itemImgList）。"""

    img_url: str | None = Field(
        default=None,
        description="官方 imgUrl，相对路径原样返回、不加前缀",
    )
    img_md5: str | None = Field(default=None, description="官方 imgMd5")
    type: str | None = Field(
        default=None,
        description="官方 type：3=Google shopping 推广图，其它=其他来源",
    )


class DhProductDetailPublic(BaseModel):
    """敦煌商品详情：官网 dh.item.get$2.0 字段对照解析 + 本地业务字段。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int = Field(description="店铺 ID（本地）")
    item_code: str = Field(description="商品编码 itemCode")
    site_id: str = Field(description="站点语言 siteId")
    is_seed: str = Field(description="是否种子：1=是，0=否（本地）")
    supplier_id: str | None = Field(default=None, description="卖家 ID supplierId")
    cate_pub_id: str | None = Field(default=None, description="发布类目 ID catePubId")
    state: str | None = Field(
        default=None,
        description="产品状态编码 state（100100 上架等，官方原值）",
    )
    item_name: str | None = Field(default=None, description="产品名称 itemBase.itemName")
    short_desc: str | None = Field(default=None, description="卖点&特性 itemBase.shortDesc")
    short_desc1: str | None = Field(default=None, description="卖点&特性1 itemBase.shortDesc1")
    short_desc2: str | None = Field(default=None, description="卖点&特性2 itemBase.shortDesc2")
    short_desc3: str | None = Field(default=None, description="卖点&特性3 itemBase.shortDesc3")
    short_desc4: str | None = Field(default=None, description="卖点&特性4 itemBase.shortDesc4")
    short_desc5: str | None = Field(default=None, description="卖点&特性5 itemBase.shortDesc5")
    html_content: str | None = Field(
        default=None, description="产品详情内容 itemBase.htmlContent"
    )
    key_word1: str | None = Field(default=None, description="搜索关键字 itemBase.keyWord1")
    key_word2: str | None = Field(default=None, description="搜索关键字 itemBase.keyWord2")
    key_word3: str | None = Field(default=None, description="搜索关键字 itemBase.keyWord3")
    video_url: str | None = Field(default=None, description="产品视频地址 itemBase.videoUrl")
    min_wholesale_qty: int | None = Field(
        default=None, description="最小起批量 itemSaleSetting.minWholesaleQty"
    )
    max_sale_qty: int | None = Field(
        default=None, description="单次最大购买量 itemSaleSetting.maxSaleQty"
    )
    leading_time: int | None = Field(
        default=None, description="备货期 itemSaleSetting.leadingTime"
    )
    price_config_type: str | None = Field(
        default=None,
        description="定价方式 itemSaleSetting.priceConfigType：1分别/2统一",
    )
    gross_weight: Decimal | None = Field(
        default=None, description="包装后重量 kg itemPackage.grossWeight"
    )
    length: Decimal | None = Field(default=None, description="包装长 cm itemPackage.length")
    width: Decimal | None = Field(default=None, description="包装宽 cm itemPackage.width")
    height: Decimal | None = Field(default=None, description="包装高 cm itemPackage.height")
    measure_id: str | None = Field(
        default=None, description="销售单位 ID itemPackage.measureId"
    )
    packing_quantity: int | None = Field(
        default=None, description="每包件数 itemPackage.packingQuantity"
    )
    item_weight_range: DhItemWeightRangePublic | None = Field(
        default=None,
        description="阶梯重量 itemPackage.itemWeigthRange",
    )
    shipping_model_id: str | None = Field(
        default=None, description="运费模板 ID shippingModelId"
    )
    after_sale_template_id: str | None = Field(
        default=None, description="售后模板 ID afterSaleTemplateId"
    )
    size_template_id: str | None = Field(
        default=None, description="尺码模板 ID sizeTemplateId"
    )
    item_group_id: str | None = Field(
        default=None, description="产品分组 ID itemGroupId"
    )
    price_min: Decimal | None = Field(default=None, description="最低价（业务派生）")
    price_max: Decimal | None = Field(default=None, description="最高价（业务派生）")
    sku_count: int | None = Field(default=None, description="SKU 数量（业务派生）")
    total_inventory: int | None = Field(default=None, description="库存合计（业务派生）")
    issample: str | None = Field(
        default=None,
        description="是否成人性质 issample；文档 2是/3否，平台也可能返回其它值",
    )
    is_dh_optimized: str | None = Field(
        default=None,
        description="是否敦煌优选 isDhOptimized：0/1",
    )
    vaild_day: str | None = Field(
        default=None, description="产品有效期 vaildDay（官方拼写，文档暂不使用）"
    )
    expire_date: datetime | None = Field(default=None, description="过期时间 expireDate")
    operate_date: datetime | None = Field(
        default=None, description="产品最新修改时间 operateDate"
    )
    last_synced_at: datetime | None = Field(default=None, description="最近同步时间（本地）")
    sync_state: str = Field(description="同步状态：1=成功，0=失败（本地）")
    item_img_list: list[DhProductImgPublic] = Field(
        default_factory=list,
        description="产品图片列表 itemImgList",
    )
    sku_list: list[DhProductSkuPublic] = Field(
        default_factory=list,
        description="产品 SKU 列表 itemSkuList",
    )
    category: DhCategoryPublic | None = Field(
        default=None,
        description="所属发布类目（按 cate_pub_id 关联本地 product_category_dh）",
    )
    attr_list: list[DhProductSelectedAttrPublic] = Field(
        default_factory=list,
        description="产品属性列表 itemAttrList",
    )
    item_spec_self_def_list: list[DhProductSpecSelfDefPublic] = Field(
        default_factory=list,
        description="自定义规格列表 itemSpecSelfDefList",
    )
    item_wholesale_range_list: list[DhItemWholesaleRangePublic] = Field(
        default_factory=list,
        description="产品折扣区间 itemWholesaleRangeList",
    )
    item_inventory: DhItemInventoryPublic | None = Field(
        default=None, description="产品备货信息 itemInventory"
    )
    item_attr_group_list: list[DhItemAttrGroupPublic] = Field(
        default_factory=list,
        description="产品兼容属性列表 itemAttrGroupList",
    )
    item_shipto_setting_list: list[DhItemShiptoSettingPublic] = Field(
        default_factory=list,
        description="销售国家定价信息 itemShiptoSettingList",
    )
    item_custom_type_info: DhItemCustomTypeInfoPublic | None = Field(
        default=None, description="定制商品信息 itemCustomTypeInfo"
    )


class DhProductGroupPublic(BaseModel):
    """敦煌产品分组（对应 dh.item.group.list itemGroupList）。"""

    group_id: str = Field(description="产品分组 ID（groupId，对应发布 itemGroupId）")
    parent_group_id: str | None = Field(default=None, description="父分组 ID")
    group_name: str | None = Field(default=None, description="分组中文名称")
    group_en_name: str | None = Field(default=None, description="分组英文名称")
    remark: str | None = Field(default=None, description="备注")
    item_count: int = Field(default=0, ge=0, description="分组下产品数量")
    show_in_store: int | None = Field(
        default=None,
        description="是否在店铺展示：1=是，0=否",
    )
    update_date: str | None = Field(default=None, description="平台更新时间")
    children: list["DhProductGroupPublic"] = Field(
        default_factory=list,
        description="子分组列表（对应 itemChildGroupList）",
    )