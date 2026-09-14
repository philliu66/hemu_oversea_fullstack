"""敦煌商品属性（预留表）。

当前产品属性从 product_dh.raw_json.itemAttrList 读取，同步时清空本表，暂不写入。
"""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ProductAttrDh(Base):
    """敦煌商品属性维度，表名 product_attr_dh。"""

    __tablename__ = "product_attr_dh"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "attr_id",
            name="uq_product_attr_dh_product_attr",
        ),
        Index("ix_product_attr_dh_product_id", "product_id"),
        Index("ix_product_attr_dh_attr_id", "attr_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product_dh.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联 product_dh.id",
    )
    attr_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="属性 ID（attrId）；自定义规格可用约定 ID",
    )
    attr_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="属性英文名（attrName / specAttrName）",
    )
    attr_name_cn: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="属性中文名（attrNameCn）",
    )
    is_price_attr: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        comment="是否价格属性（isPriceAttr）：0/1",
    )
    is_brand: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        comment="是否品牌属性（isbrand）：0/1",
    )
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="category",
        comment="来源：category=类目属性，custom=自定义规格",
    )
    sort: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="展示排序",
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
