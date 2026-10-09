"""敦煌 SKU 基础信息表。"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.supplier import Supplier


class SkuBaseInfoDh(Base):
    """敦煌 SKU 基础信息（按供应商 + 型号），表名 sku_base_info_dh。"""

    __tablename__ = "sku_base_info_dh"
    __table_args__ = (
        UniqueConstraint(
            "supplier_id",
            "sku_code",
            name="uq_sku_base_info_dh_supplier_sku",
        ),
        Index("ix_sku_base_info_dh_supplier_id", "supplier_id"),
        Index("ix_sku_base_info_dh_sku_code", "sku_code"),
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
        comment="SKU 编码型号（产品型号）",
    )
    sku_series: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="SKU 产品系列",
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="单元价格（美元）",
    )
    shipping_template_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="物流模板名称（Excel 物流模板）",
    )
    weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3),
        nullable=True,
        comment="重量（kg）",
    )
    packing_quantity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="打包数（Excel 打包 DH）",
    )
    min_wholesale_qty: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="起订量（Excel 起批量 DH）",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )
    updated_by: Mapped[int] = mapped_column(
        nullable=False,
        server_default="0",
        comment="更新用户 ID；0=系统",
    )

    supplier: Mapped["Supplier"] = relationship(
        "Supplier",
        foreign_keys=[supplier_id],
        lazy="raise",
    )
