"""敦煌商品主表。

列表筛选和展示用列；详情正文在 raw_json，SKU 数组在 sku_json。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
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
    main_image_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="列表主图相对路径，取 itemImgList 第一张有效图",
    )
    sku_json: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="SKU 数组，内容为 raw_json.itemSkuList",
    )
    raw_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="dh.item.get 原始响应，详情页据此解析",
    )
    sync_state: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        server_default="1",
        comment="同步状态：1=成功，0=失败",
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="最近一次详情同步时间",
    )
