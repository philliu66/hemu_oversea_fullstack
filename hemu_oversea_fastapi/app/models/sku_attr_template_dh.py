"""敦煌 SKU 属性模版（按供应商 + SKU 型号 + 叶子类目）。"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SkuAttrTemplateDh(Base):
    """SKU 类目属性模版，表名 sku_attr_template_dh。"""

    __tablename__ = "sku_attr_template_dh"
    __table_args__ = (
        UniqueConstraint(
            "supplier_id",
            "sku_code",
            "cate_pub_id",
            name="uq_sku_attr_template_dh_supplier_sku_cate",
        ),
        Index("ix_sku_attr_template_dh_supplier_id", "supplier_id"),
        Index("ix_sku_attr_template_dh_sku_code", "sku_code"),
        Index("ix_sku_attr_template_dh_cate_pub_id", "cate_pub_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        comment="归属供应商 ID",
    )
    sku_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SKU 编码型号",
    )
    cate_pub_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="叶子类目敦煌 ID",
    )
    raw_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment='属性快照，形如 {"attr_list": [...]}',
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="创建用户 ID；0=系统",
    )
    updated_by: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="更新用户 ID；0=系统",
    )
