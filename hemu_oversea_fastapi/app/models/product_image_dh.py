"""敦煌商品图片（dh.item.get itemImgList）。"""

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


class ProductImageDh(Base):
    """敦煌商品图片，表名 product_image_dh。"""

    __tablename__ = "product_image_dh"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "sort",
            name="uq_product_image_dh_product_sort",
        ),
        Index("ix_product_image_dh_product_id", "product_id"),
        Index("ix_product_image_dh_type", "type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product_dh.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联 product_dh.id",
    )
    img_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="图片相对路径（imgUrl）",
    )
    img_md5: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="图片 MD5（imgMd5）",
    )
    type: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        comment="图片类型（type）：3=推广图，其它=普通",
    )
    sort: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="展示排序，越小越靠前",
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
