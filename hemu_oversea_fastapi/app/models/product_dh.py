"""敦煌商品主表（dh.item.get 核心汇总）。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ProductDh(Base):
    """敦煌商品（含种子/非种子），表名 product_dh。"""

    __tablename__ = "product_dh"
    __table_args__ = (
        UniqueConstraint(
            "store_id",
            "item_code",
            "site_id",
            name="uq_product_dh_store_item_site",
        ),
        Index("ix_product_dh_store_id", "store_id"),
        Index("ix_product_dh_cate_pub_id", "cate_pub_id"),
        Index("ix_product_dh_state", "state"),
        Index("ix_product_dh_is_seed", "is_seed"),
        Index("ix_product_dh_sync_state", "sync_state"),
        Index("ix_product_dh_operate_date", "operate_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        comment="归属店铺 ID",
    )
    item_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="商品编码（itemCode）",
    )
    site_id: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        server_default="EN",
        comment="站点语言（siteId），默认 EN",
    )
    is_seed: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        server_default="1",
        comment="是否种子商品：1=是，0=否",
    )
    supplier_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="平台卖家 ID（supplierId）",
    )
    cate_pub_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="发布类目 ID（catePubId）",
    )
    state: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="商品状态（state）：100100上架等",
    )
    item_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="商品标题（itemBase.itemName）",
    )
    short_desc: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="简短介绍（itemBase.shortDesc）",
    )
    html_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="详情 HTML（itemBase.htmlContent）",
    )
    key_word1: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="关键词1（itemBase.keyWord1）",
    )
    key_word2: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="关键词2（itemBase.keyWord2）",
    )
    key_word3: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="关键词3（itemBase.keyWord3）",
    )
    video_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="视频地址（itemBase.videoUrl）",
    )
    min_wholesale_qty: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="最小起批量（itemSaleSetting.minWholesaleQty）",
    )
    max_sale_qty: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="单次最大购买量（itemSaleSetting.maxSaleQty）",
    )
    leading_time: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="备货期天数（itemSaleSetting.leadingTime）",
    )
    price_config_type: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        comment="定价方式（itemSaleSetting.priceConfigType）：1单独/2统一",
    )
    gross_weight: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="包装毛重 kg（itemPackage.grossWeight）",
    )
    length: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="包装长 cm（itemPackage.length）",
    )
    width: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="包装宽 cm（itemPackage.width）",
    )
    height: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="包装高 cm（itemPackage.height）",
    )
    measure_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="销售单位 ID（itemPackage.measureId）",
    )
    packing_quantity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="每包件数（itemPackage.packingQuantity）",
    )
    shipping_model_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="运费模板 ID（shippingModelId）",
    )
    after_sale_template_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="售后模板 ID（afterSaleTemplateId）",
    )
    size_template_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="尺码模板 ID（sizeTemplateId）",
    )
    item_group_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="产品分组 ID（itemGroupId）",
    )
    vaild_day: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="有效天数（vaildDay，平台字段拼写）",
    )
    expire_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="过期时间（expireDate）",
    )
    operate_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最后修改时间（operateDate）",
    )
    issample: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        comment="是否成人用品（issample）：2是/3否",
    )
    is_dh_optimized: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        comment="是否敦煌优选（isDhOptimized）：0/1",
    )
    price_min: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="派生：可售 SKU 最低价",
    )
    price_max: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="派生：可售 SKU 最高价",
    )
    sku_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="派生：SKU 数量",
    )
    total_inventory: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="派生：库存合计",
    )
    main_image_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="派生：主图相对路径",
    )
    base_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展：shortDesc1-5 等 itemBase 附加字段",
    )
    wholesale_ranges_json: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="批发折扣阶梯（itemWholesaleRangeList）",
    )
    inventory_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="备货信息（itemInventory）",
    )
    ext_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="其它扩展：国家定价/定制/兼容属性等",
    )
    raw_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="dh.item.get 原始响应备份",
    )
    sync_state: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        server_default="1",
        comment="同步状态：1=成功，0=失败",
    )
    sync_state_desc: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="同步状态描述：成功时为「同步成功」，失败时为失败原因",
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最近一次详情同步时间",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
