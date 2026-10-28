from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.store import Store
    from app.models.supplier import Supplier
    from app.models.user import User


class StoreTts(Base):
    """一家 TikTok 站点店。token 与 shop_cipher 都在这一行。"""

    __tablename__ = "store_tts"
    __table_args__ = (
        Index(
            "uq_store_tts_store_id_active",
            "store_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_store_tts_shop_id_active",
            "shop_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_store_tts_supplier_open", "supplier_id", "open_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    shop_id: Mapped[str] = mapped_column(String(64))
    shop_cipher: Mapped[str] = mapped_column(Text)
    shop_code: Mapped[str] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(16), nullable=True)
    seller_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    open_id: Mapped[str] = mapped_column(String(255))
    user_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    granted_scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    oauth_authorized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    store: Mapped["Store"] = relationship(
        "Store",
        back_populates="tts_rows",
    )
    supplier: Mapped["Supplier"] = relationship(
        "Supplier",
        foreign_keys=[supplier_id],
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def oauth_status(self) -> int:
        """0 未授权，1 已授权，2 授权已过期。只看 access_token 到期时间。"""
        if not self.access_token:
            return 0
        expires = self.access_token_expires_at
        if expires is not None:
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < datetime.now(timezone.utc):
                return 2
        return 1


class StoreTtsOauthPending(Base):
    """授权完成前暂存 state。回调用完即删，不存 token。"""

    __tablename__ = "store_tts_oauth_pending"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(String(20), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    creator: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by],
    )
