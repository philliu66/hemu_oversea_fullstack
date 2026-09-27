"""敦煌产品分组（dh.item.group.list ItemGroup）。"""

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


class ProductGroupDh(Base):
    """对应敦煌 ItemGroup / ItemChildGroup，表名 product_group_dh。"""

    __tablename__ = "product_group_dh"
    __table_args__ = (
        UniqueConstraint(
            "store_id",
            "group_id",
            name="uq_product_group_dh_store_group",
        ),
        Index("ix_product_group_dh_supplier_id", "supplier_id"),
        Index("ix_product_group_dh_store_id", "store_id"),
        Index("ix_product_group_dh_parent_group_id", "parent_group_id"),
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
    group_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="产品分组 ID（groupId）",
    )
    parent_group_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="父分组 ID（parentGroupId）",
    )
    group_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="分组中文名称（groupName）",
    )
    group_en_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="分组英文名称（groupEnName）",
    )
    remark: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="备注（remark）",
    )
    item_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="分组下产品数量（itemCount）",
    )
    show_in_store: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        comment="是否在店铺展示：1=是，0=否（showInStore）",
    )
    update_date: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="平台更新时间（updateDate）",
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
