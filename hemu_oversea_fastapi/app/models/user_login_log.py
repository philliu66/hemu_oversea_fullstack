from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserLoginLog(Base):
    __tablename__ = "user_login_logs"
    __table_args__ = (
        Index("ix_user_login_logs_user_login_at", "user_id", "login_at"),
        Index("ix_user_login_logs_login_at", "login_at"),
        Index("ix_user_login_logs_audience_login_at", "audience", "login_at"),
        Index("ix_user_login_logs_refresh_jti", "refresh_jti"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    username: Mapped[str] = mapped_column(String(50))
    audience: Mapped[str] = mapped_column(String(20))
    login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    logout_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    logout_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refresh_jti: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
