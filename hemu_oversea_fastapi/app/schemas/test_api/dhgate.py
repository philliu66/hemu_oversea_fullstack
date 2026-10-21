"""敦煌官方 API 联调请求体（仅 testAPI，非业务接口）。

字段说明对齐 dhgate_API.md / open.dhgate.com；枚举以手册明确列出的为准，
手册未列枚举的字段会标注「以官方实返为准」。
"""

from typing import Literal

from pydantic import BaseModel, Field


class StoreIdBody(BaseModel):
    store_id: int = Field(
        description=(
            "【联调必填·本地】店铺 ID（stores.id）。"
            "用于取该店 OAuth access_token，不传给敦煌业务入参。"
        ),
    )


class PunishBrandListTestRequest(StoreIdBody):
    """dh.punish.brand.list.get$1.0 — 第三方投诉处罚。"""

    third_type: Literal["brand", "other"] = Field(
        description=(
            "【官方必填】thirdType 投诉类型。"
            "可选值：`brand`=品牌商投诉；`other`=其他第三方投诉。"
        ),
    )
    page_no: int = Field(
        default=1,
        ge=1,
        description="【官方必填】pageNo 页码，从 1 开始",
    )
    page_size: int = Field(
        default=100,
        ge=1,
        le=200,
        description="【官方必填】pageSize 每页条数，范围 1～200",
    )


class PunishListTestRequest(StoreIdBody):
    """dh.punish.list.get$1.0 — 卖家处罚信息。"""

    start_date: str = Field(
        min_length=1,
        description="【官方必填】startDate 开始日期，格式 yyyy-MM-dd",
        examples=["2026-10-01"],
    )
    end_date: str = Field(
        min_length=1,
        description="【官方必填】endDate 结束日期，格式 yyyy-MM-dd",
        examples=["2026-10-19"],
    )
    punish_id: str | None = Field(
        default=None,
        description="【官方可选】punishId 处罚编号；不传则按时间范围查",
    )
    page_no: int = Field(
        default=1,
        ge=1,
        description="【官方必填】pageNo 页码，从 1 开始",
    )
    page_size: int = Field(
        default=100,
        ge=1,
        le=200,
        description="【官方必填】pageSize 每页条数，范围 1～200",
    )


class DisputeProcessingListTestRequest(StoreIdBody):
    """dh.dispute.processing.list$1.0 — 进行中纠纷订单列表。"""

    dispute_status: str = Field(
        min_length=1,
        max_length=64,
        description=(
            "【官方必填】disputeStatus 纠纷状态。"
            "手册未单独列本接口枚举；可参考纠纷开启列表响应编码联调："
            "`106001` 协议纠纷-等待协议达成；"
            "`106003` 协议纠纷-协议已达成；"
            "`107001` 平台纠纷开启；"
            "`107002` 平台纠纷-dhgate审核中；"
            "`107003` 平台纠纷-裁决方案执行中；"
            "`109001` 售后纠纷开启；"
            "`109002` 售后纠纷裁决中。"
            "最终以官方实返/错误提示为准。"
        ),
        examples=["109001"],
    )
    page_num: int = Field(
        default=1,
        ge=1,
        description="【官方可选】pageNum 页码，从 1 开始（默认 1）",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=200,
        description="【官方可选】pageSize 每页条数，1～200（默认 20）",
    )
    start_time: str | None = Field(
        default=None,
        description=(
            "【官方可选】startTime 开始时间；格式以官方为准"
            "（常见 yyyy-MM-dd 或 yyyy-MM-dd HH:mm:ss）"
        ),
        examples=["2026-10-01"],
    )
    end_time: str | None = Field(
        default=None,
        description=(
            "【官方可选】endTime 结束时间；格式以官方为准"
            "（常见 yyyy-MM-dd 或 yyyy-MM-dd HH:mm:ss）"
        ),
        examples=["2026-10-19"],
    )


class OrderDisputeOpenListTestRequest(StoreIdBody):
    """dh.order.disputeopen.list$2.0 — seller 纠纷开启订单列表。"""

    page_no: int = Field(
        default=1,
        ge=1,
        description="【官方必填】pageNo 页码，从 1 开始；超过总页数返回最后一页",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=200,
        description="【官方必填】pageSize 每页条数，范围 1～200",
    )
    dispute_type: str | None = Field(
        default=None,
        max_length=64,
        description=(
            "【官方可选】disputeType 纠纷类型。"
            "可选值：`1`=协议纠纷；`2`=平台纠纷；`3`=售后纠纷；"
            "不传=全部开启中纠纷。"
        ),
        examples=["1", "2", "3"],
    )
    buyer_nick_name: str | None = Field(
        default=None,
        max_length=128,
        description="【官方可选】buyerNickName 买家昵称",
        examples=["zhangsan"],
    )
    order_no: str | None = Field(
        default=None,
        max_length=64,
        description="【官方可选】orderNo 订单号；精确查单笔开启中纠纷",
        examples=["1455953150"],
    )


class CategoryListTestRequest(StoreIdBody):
    """dh.category.list$2.0 — 本联调为递归全量入库，无 parentId 入参。"""


class MeasuresListTestRequest(StoreIdBody):
    """dh.base.measures.get$1.0 — 无业务入参，store_id 仅取 token。"""


class CommissionRateListTestRequest(StoreIdBody):
    """dh.categorys.commissions$1.0 — 无业务入参，store_id 仅取 token。"""


class CategoryGetTestRequest(StoreIdBody):
    """dh.category.get$2.0 — 类目详情/属性。"""

    cate_pub_id: str = Field(
        min_length=1,
        max_length=64,
        description=(
            "【官方必填】catePubId 叶子发布类目 ID。"
            "须为有效叶子类目（来自 dh.category.list / product_category_dh）。"
        ),
    )


class CategoryPathGetTestRequest(StoreIdBody):
    """dh.category.path.get$2.0 — 类目路径。"""

    cate_pub_id: str = Field(
        min_length=1,
        max_length=64,
        description=(
            "【官方必填】catePubId 发布类目 ID；"
            "返回从根到该类目的主线路径 categoryPublishList。"
        ),
    )


class ItemGroupListTestRequest(StoreIdBody):
    """dh.item.group.list$2.0 — 产品组列表。"""

    page_no: int = Field(
        default=1,
        ge=1,
        description="【官方必填】pageNo 当前页，从 1 开始",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=200,
        description="【官方必填】pageSize 每页条数，1～200",
    )
    contain_child_group: bool | None = Field(
        default=None,
        description=(
            "【官方可选】containChildGroup 是否包含子组。"
            "`true` 含子组；`false` 不含；不传则官方默认 false。"
        ),
    )
    parent_group_id: str | None = Field(
        default=None,
        max_length=64,
        description="【官方可选】parentGroupId 产品组父类 ID",
    )
    group_cn_name: str | None = Field(
        default=None,
        max_length=128,
        description="【官方可选】groupCnName 产品组中文名称（筛选）",
    )
    group_en_name: str | None = Field(
        default=None,
        max_length=128,
        description="【官方可选】groupEnName 产品组英文名称（筛选）",
    )


class ItemAftersaleListTestRequest(StoreIdBody):
    """dh.item.aftersale.list$2.0 — 无业务入参。"""


class ShippingTemplateListTestRequest(StoreIdBody):
    """dh.shipping.template.list$2.0 — 无业务入参。"""


class ItemGetTestRequest(StoreIdBody):
    """dh.item.get$2.0 / dh.item.html.get（长描复用本入参）。"""

    item_code: str = Field(
        min_length=1,
        max_length=64,
        description=(
            "【官方必填】itemCode 商品编码（产品列表 dh.item.list 返回）。"
            "长描接口官方字段名多为 itemcode，本联调统一传 item_code。"
        ),
        examples=["211198221"],
    )
    site_id: Literal["EN", "RU", "ES", "ID"] = Field(
        default="EN",
        description=(
            "【官方可选】siteId 站点语言。"
            "可选值：`EN`=英语（默认）；`RU`=俄语；`ES`=西语；`ID`=印尼语。"
            "长描 get 时本字段仅对齐本地，不一定上送平台。"
        ),
    )


class ItemShelfTestRequest(StoreIdBody):
    """dh.item.upshelf.list$2.0 / dh.item.downshelf.list$2.0。"""

    item_codes: str = Field(
        min_length=1,
        max_length=8000,
        description=(
            "【官方必填】itemCodes 产品编码字符串；"
            "多个用英文半角逗号分隔，最多 200 个。"
            "示例：`211198221` 或 `211198221,211198222`。"
        ),
        examples=["211198221", "211198221,211198222"],
    )
    action: int = Field(
        ...,
        ge=0,
        le=1,
        description=(
            "【联调必填·本地】操作标识（非官方字段）。"
            "可选值：`0`=下架 → dh.item.downshelf.list$2.0；"
            "`1`=上架 → dh.item.upshelf.list$2.0。"
        ),
    )
    site_id: Literal["EN", "RU", "ES", "ID"] | None = Field(
        default=None,
        description=(
            "【官方可选】siteId 站点语言；不传则请求不带 siteId。"
            "可选值：EN / RU / ES / ID。"
        ),
    )


class ItemFissionUpdateInfo(BaseModel):
    """裂变时覆盖种子商品的字段（映射到 dh.item.add 相关入参）。"""

    item_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=140,
        description=(
            "【可选】裂变后标题 → dh.item.add itemBase.itemName，最多 140 字符"
        ),
    )
    afterSaleTemplateId: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description=(
            "【可选】售后模板 ID → afterSaleTemplateId；"
            "有值则直接使用，不再拉 dh.item.aftersale.list"
        ),
    )
    shippingTempId: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description=(
            "【可选】运费模板 ID；有值则映射为发布入参 shippingModelId，"
            "不再拉 dh.shipping.template.list"
        ),
    )


class ItemFissionAddTestRequest(BaseModel):
    """裂变发布：源店 dh.item.get + 目标店 dh.item.add$2.0（联调编排）。"""

    target_store_id: int = Field(
        description="【联调必填·本地】目标店铺 ID；用该店 token 调用 dh.item.add",
    )
    pid: int = Field(
        ge=1,
        description=(
            "【联调必填·本地】种子商品 product_dh.id；"
            "用于查出源店 store_id / item_code / site_id"
        ),
    )
    update_info: ItemFissionUpdateInfo = Field(
        default_factory=ItemFissionUpdateInfo,
        description="【可选】覆盖种子详情的字段：标题、售后模板、运费模板等",
    )
    site_id: Literal["EN", "RU", "ES", "ID"] | None = Field(
        default=None,
        description=(
            "【官方可选】siteId；不传则用种子商品 site_id，再默认 EN。"
            "可选值：EN / RU / ES / ID。"
        ),
    )


class WisCoreInfoTestRequest(StoreIdBody):
    """dh.wis.core.info$1.0 — 数据概览核心指标。"""

    period_type: Literal["DAY", "L7", "L30", "WEEK", "MON"] = Field(
        description=(
            "【官方必填】periodType 分表/统计周期。"
            "可选值：`DAY`=1天；`L7`=7天；`L30`=30天；`WEEK`=周；`MON`=月。"
        ),
        examples=["DAY", "L7"],
    )
    site: Literal["TOTAL", "app", "unapp"] = Field(
        description=(
            "【官方必填】site 站点。"
            "可选值：`TOTAL`=合计；`app`；`unapp`。"
        ),
        examples=["TOTAL"],
    )
    end_date: str = Field(
        min_length=1,
        max_length=32,
        description="【官方必填】endDate 结束时间，格式 yyyy-MM-dd",
        examples=["2026-10-19"],
    )
    country_id: str = Field(
        min_length=1,
        max_length=64,
        description=(
            "【官方必填】countryId 国家；手册取值说明示例 `TOTAL`（合计）。"
            "其它国家编码可参考 dh.base.countrys.get。"
        ),
        examples=["TOTAL"],
    )
    stat_date: str = Field(
        min_length=1,
        max_length=32,
        description="【官方必填】statDate 开始时间，格式 yyyy-MM-dd",
        examples=["2026-10-13"],
    )


class WisDetailPageTestRequest(StoreIdBody):
    """dh.wis.detail.page$1.0 — 商品分析-产品详情数据。"""

    end_date: str = Field(
        min_length=1,
        max_length=32,
        description="【官方必填】endDate 结束时间，格式 yyyy-MM-dd",
        examples=["2026-10-19"],
    )
    stat_date: str = Field(
        min_length=1,
        max_length=32,
        description="【官方必填】statDate 开始时间，格式 yyyy-MM-dd",
        examples=["2026-10-13"],
    )
    site: Literal["PC", "APP", "WAP", "all"] = Field(
        description=(
            "【官方必填】site 站点。"
            "可选值：`PC`；`APP`；`WAP`；`all`=全部。"
        ),
        examples=["all", "PC"],
    )
    page_no: int = Field(
        default=1,
        ge=1,
        description="【官方必填】pageNo 页号，从 1 开始",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=200,
        description="【官方必填】pageSize 每页条数，1～200",
    )
    period_type: Literal["DAY", "L7", "L30", "WEEK", "MON"] | None = Field(
        default=None,
        description=(
            "【官方可选】periodType 分表参数；不传则不上送。"
            "可选值：`DAY` / `L7` / `L30` / `WEEK` / `MON`。"
        ),
    )


class WisKeywordTop10TestRequest(StoreIdBody):
    """dh.wis.keywordtop10.info$1.0 — 关键词 TOP 下载。"""

    platform_id: str = Field(
        default="ALL",
        min_length=1,
        max_length=64,
        description=(
            "【官方必填】platformId；手册取值说明示例 `ALL`。"
        ),
        examples=["ALL"],
    )
    search_date_type: int = Field(
        default=12,
        description=(
            "【官方必填】searchDateType；手册取值说明示例 `12`。"
            "其它取值以官方实返/错误提示为准。"
        ),
        examples=[12],
    )
    item_code: str = Field(
        min_length=1,
        max_length=64,
        description=(
            "【官方必填】itemCode 产品编码（数字）。"
            "注意：官网参数说明列可能误写为「国家」；联调按字段名=产品编码。"
        ),
        examples=["211198221"],
    )
    site_id: str = Field(
        default="EN",
        min_length=1,
        max_length=32,
        description=(
            "【官方必填】siteId；手册取值说明示例 `EN`。"
        ),
        examples=["EN"],
    )


class SellerAdReportTestRequest(StoreIdBody):
    """dh.seller.ad.order/prod.report.page$1.0 — 增值 API 广告消耗（订单/产品维度共用）。"""

    ad_type: str = Field(
        default="",
        max_length=64,
        description=(
            "【官方必填字段】adType 广告类型；可传空字符串表示全部。"
            "可选值：``（空）=所有广告；`shopauto`=全店自动广告；"
            "`ppc`=手动广告；`prodauto`=商品自动广告。"
        ),
        examples=["", "ppc", "shopauto", "prodauto"],
    )
    itemcode: str = Field(
        min_length=1,
        max_length=64,
        description="【官方必填】itemcode 商品 ID / 产品编码（注意小写字段名）",
        examples=["211198221"],
    )
    dateline_from: str = Field(
        min_length=1,
        max_length=32,
        description=(
            "【官方必填】datelineFrom 开始日期 yyyy-MM-dd；"
            "与结束日期间隔建议控制在 1 个月内，否则效率很低。"
        ),
        examples=["2026-10-01"],
    )
    dateline_to: str = Field(
        min_length=1,
        max_length=32,
        description=(
            "【官方必填】datelineTo 结束日期 yyyy-MM-dd；"
            "与开始日期间隔建议控制在 1 个月内。"
        ),
        examples=["2026-10-19"],
    )
    page: int = Field(
        default=1,
        ge=1,
        description="【官方必填】page 当前页号，从 1 开始",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=200,
        description="【官方必填】limit 每页条数，1～200（样例 30）",
    )
