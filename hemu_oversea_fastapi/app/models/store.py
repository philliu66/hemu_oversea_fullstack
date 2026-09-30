from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.supplier import Supplier
    from app.models.user import User


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = (
        Index(
            "uq_stores_identifier_active",
            "identifier",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_stores_store_type", "store_type"),
        Index("ix_stores_supplier_id", "supplier_id"),
        Index(
            "ix_stores_oauth_pending_state",
            "oauth_pending_state",
            unique=True,
            postgresql_where=text(
                "deleted_at IS NULL AND oauth_pending_state IS NOT NULL"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
    )
    store_type: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(100))
    identifier: Mapped[str] = mapped_column(String(100))
    base_discount: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        server_default="0",
        comment="基础折扣（0.00～0.99）",
    )
    account: Mapped[str] = mapped_column(String(100))
    password: Mapped[str] = mapped_column(String(255))
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    oauth_scope: Mapped[str | None] = mapped_column(String(64), nullable=True)
    oauth_authorized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    oauth_pending_state: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    oauth_pending_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    supplier: Mapped["Supplier | None"] = relationship(
        "Supplier",
        foreign_keys=[supplier_id],
    )
    creator: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by],
    )
    updater: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[updated_by],
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def oauth_authorized(self) -> bool:
        return bool(self.access_token)

    @property
    def oauth_status(self) -> int:
        """0 未授权，1 已授权，2 授权已过期。"""
        if not self.access_token:
            return 0
        expires = self.access_token_expires_at
        if expires is not None:
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < datetime.now(timezone.utc):
                return 2
        return 1
