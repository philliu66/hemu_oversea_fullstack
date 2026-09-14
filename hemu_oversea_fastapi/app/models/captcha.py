from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Captcha(Base):
    __tablename__ = "captchas"
    __table_args__ = (
        Index("ix_captchas_captcha_id", "captcha_id", unique=True),
        Index("ix_captchas_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    captcha_id: Mapped[str] = mapped_column(String(32))
    code: Mapped[str] = mapped_column(String(8))
    audience: Mapped[str] = mapped_column(String(20))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
