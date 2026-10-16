"""通用邮件发送记录（按业务类别区分场景）。"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MailSendLog(Base):
    __tablename__ = "mail_send_logs"
    __table_args__ = (
        Index("ix_mail_send_logs_category_created", "category", "created_at"),
        Index("ix_mail_send_logs_supplier_created", "supplier_id", "created_at"),
        Index("ix_mail_send_logs_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # 业务类别，如 store_inspection
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
    )
    to_emails: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    # success / failed
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 成功时按业务写入结构化数据（巡检：处罚 + 纠纷）
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # 阿里云 RequestId 等
    provider_request_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
