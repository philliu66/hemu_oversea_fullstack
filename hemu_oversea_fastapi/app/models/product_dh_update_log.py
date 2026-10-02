"""敦煌商品变更日志。"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.product_dh import ProductDh
    from app.models.store import Store
    from app.models.user import User


class ProductDhUpdateLog(Base):
    """商品信息变更日志（批量 / 人工）。"""

    __tablename__ = "product_dh_update_log"
    __table_args__ = (
        Index("ix_product_dh_update_log_store_item", "store_id", "item_code"),
        Index("ix_product_dh_update_log_created_at", "created_at"),
        Index("ix_product_dh_update_log_operator_id", "operator_id"),
        Index("ix_product_dh_update_log_source", "source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_dh_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_dh.id", ondelete="SET NULL"),
        nullable=True,
        comment="本地商品主键（可空，商品未入库时）",
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        comment="店铺 ID",
    )
    item_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="商品编码 itemCode",
    )
    site_id: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        server_default="EN",
        comment="站点语言 siteId",
    )
    operator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="变更人用户 ID（系统任务可空）",
    )
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="来源：manual / batch_excel / api 等",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default="success",
        comment="结果：success / failed / skipped",
    )
    summary: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="变更短描述（列表展示）",
    )
    changes: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="字段级变更明细 [{field,label,before,after}]",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="失败原因",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="变更时间",
    )

    store: Mapped["Store"] = relationship(
        "Store",
        foreign_keys=[store_id],
        lazy="raise",
    )
    product: Mapped["ProductDh | None"] = relationship(
        "ProductDh",
        foreign_keys=[product_dh_id],
        lazy="raise",
    )
    operator: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[operator_id],
        lazy="raise",
    )
