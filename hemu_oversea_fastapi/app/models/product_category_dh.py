"""敦煌网发布类目（dh.category.list CategoryPublish）。"""

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ProductCategoryDh(Base):
    """对应敦煌 CategoryPublish 结构，表名 product_category_dh。"""

    __tablename__ = "product_category_dh"
    __table_args__ = (
        Index("ix_product_category_dh_pare_cate_pub_id", "pare_cate_pub_id"),
        Index("ix_product_category_dh_leaf", "leaf"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cate_pub_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        comment="发布类目 ID（catePubId）",
    )
    pub_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="英文名称（pubName）",
    )
    pub_name_cn: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="中文名称（pubNameCn）",
    )
    remark: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="备注（remark）",
    )
    leaf: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        comment="是否叶子：1=是，0=否（leaf）",
    )
    pare_cate_pub_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="父发布类目 ID（pareCatePubId）",
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
