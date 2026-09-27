"""敦煌运费模板（dh.shipping.template.list ShippingModelList）。"""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ShippingTemplateDh(Base):
    """对应敦煌 shippingModelList 项，表名 shipping_template_dh。"""

    __tablename__ = "shipping_template_dh"
    __table_args__ = (
        UniqueConstraint(
            "store_id",
            "shipping_temp_id",
            name="uq_shipping_template_dh_store_temp",
        ),
        Index("ix_shipping_template_dh_supplier_id", "supplier_id"),
        Index("ix_shipping_template_dh_store_id", "store_id"),
        Index("ix_shipping_template_dh_model_type", "model_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        comment="供应商 ID",
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        comment="来源店铺 ID",
    )
    shipping_temp_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="运费模板 ID（shippingTempId，对应发布 shippingModelId）",
    )
    model_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="模板名称（modelName）",
    )
    model_desc: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="模板描述（modelDesc）",
    )
    create_date: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="平台创建时间（createDate）",
    )
    model_type: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="模板类型（modelType，10=新手运费模板）",
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
