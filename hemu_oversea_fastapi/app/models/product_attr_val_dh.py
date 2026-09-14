"""敦煌商品属性值（预留表）。

当前属性值从 product_dh.raw_json.itemAttrList 读取，同步时清空本表，暂不写入。
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


class ProductAttrValDh(Base):
    """敦煌商品属性值，表名 product_attr_val_dh。"""

    __tablename__ = "product_attr_val_dh"
    __table_args__ = (
        UniqueConstraint(
            "attr_row_id",
            "attr_val_id",
            name="uq_product_attr_val_dh_attr_row_val",
        ),
        Index("ix_product_attr_val_dh_product_id", "product_id"),
        Index("ix_product_attr_val_dh_attr_row_id", "attr_row_id"),
        Index("ix_product_attr_val_dh_attr_val_id", "attr_val_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product_dh.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联 product_dh.id（冗余，便于按商品查）",
    )
    attr_row_id: Mapped[int] = mapped_column(
        ForeignKey("product_attr_dh.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联 product_attr_dh.id",
    )
    attr_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="属性 ID（attrId，与属性表一致）",
    )
    attr_val_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="属性值 ID（attrValId）",
    )
    attr_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="值级属性英文名（itemAttrValList.attrName，自定义属性常用）",
    )
    attr_name_cn: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="值级属性中文名（itemAttrValList.attrNameCn）",
    )
    line_attrval_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="属性值英文名（lineAttrvalName / attrValName）",
    )
    line_attrval_name_cn: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="属性值中文名（lineAttrvalNameCn）",
    )
    pic_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="属性值图片（picUrl）",
    )
    brand_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="品牌 ID（brandId）",
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
