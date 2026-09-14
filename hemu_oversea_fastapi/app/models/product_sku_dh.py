"""敦煌商品 SKU（dh.item.get itemSkuList）。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ProductSkuDh(Base):
    """敦煌商品 SKU，表名 product_sku_dh。"""

    __tablename__ = "product_sku_dh"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "sku_md5",
            name="uq_product_sku_dh_product_sku_md5",
        ),
        Index("ix_product_sku_dh_product_id", "product_id"),
        Index("ix_product_sku_dh_sku_id", "sku_id"),
        Index("ix_product_sku_dh_sku_code", "sku_code"),
        Index("ix_product_sku_dh_sale_status", "sale_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product_dh.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联 product_dh.id",
    )
    sku_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="平台 SKU ID（skuId）",
    )
    sku_md5: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SKU MD5（skuMD5），规格组合指纹",
    )
    sku_code: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="卖家自定义 SKU 编码（skuCode）",
    )
    retail_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="零售价（retailPrice）",
    )
    inventory: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="库存（inventory）",
    )
    sale_status: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        comment="是否可售（saleStatus）：0不可售/1可售",
    )
    pic_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="SKU 图片路径（picUrl）",
    )
    attr_combo_json: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="属性组合（itemSkuAttrValueList）",
    )
    attr_combo_text: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="属性组合展示文案，如 Color:Pink;Size:S",
    )
    region_prices_json: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="销售国家定价（shiptoCountryPriceList）",
    )
    location_inventory_json: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="分仓库存（itemSkuInventoryList）",
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
