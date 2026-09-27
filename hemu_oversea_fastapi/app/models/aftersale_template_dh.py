"""敦煌售后模板（dh.item.aftersale.list AfterSaleTemplate）。"""

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


class AftersaleTemplateDh(Base):
    """对应敦煌 afterSaleList 项，表名 aftersale_template_dh。"""

    __tablename__ = "aftersale_template_dh"
    __table_args__ = (
        UniqueConstraint(
            "store_id",
            "after_sale_template_id",
            name="uq_aftersale_template_dh_store_temp",
        ),
        Index("ix_aftersale_template_dh_supplier_id", "supplier_id"),
        Index("ix_aftersale_template_dh_store_id", "store_id"),
        Index("ix_aftersale_template_dh_status", "status"),
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
    after_sale_template_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="售后模板 ID（afterSaleTemplateId）",
    )
    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="模板名称（name）",
    )
    if_noreason_back: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="是否支持无理由退货（ifNoreasonBack）",
    )
    freight_bear: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="运费承担方（freightBear）",
    )
    return_deadline: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="退货期限天数（returnDeadline）",
    )
    return_refund: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="退货退款（returnRefund）",
    )
    other_return: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="其他退货说明（otherReturn）",
    )
    status: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        comment="模板状态（status，0=已删除）",
    )
    if_template_default: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        comment="是否默认模板（ifTemplateDefault，1=默认）",
    )
    create_date: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="平台创建时间（createDate）",
    )
    update_date: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="平台更新时间（updateDate）",
    )
    protection_period: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="保障期天数（protectionPeriod）",
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
