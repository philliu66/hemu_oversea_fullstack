from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserOperationLog(Base):
    __tablename__ = "user_operation_logs"
    __table_args__ = (
        Index("ix_user_operation_logs_actor_created", "actor_user_id", "created_at"),
        Index("ix_user_operation_logs_action_created", "action", "created_at"),
        Index("ix_user_operation_logs_resource", "resource_type", "resource_id"),
        Index("ix_user_operation_logs_created_at", "created_at"),
        Index("ix_user_operation_logs_supplier_created", "supplier_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_username: Mapped[str] = mapped_column(String(50))
    actor_role: Mapped[str] = mapped_column(String(32))
    org_type: Mapped[str] = mapped_column(String(20))
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(64))
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(String(512))
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        server_default="success",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
