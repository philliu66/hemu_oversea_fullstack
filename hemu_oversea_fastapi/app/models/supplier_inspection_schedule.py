"""供应商每日店铺巡检设置（一供应商一条）。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SupplierInspectionSchedule(Base):
    __tablename__ = "supplier_inspection_schedules"
    __table_args__ = (
        UniqueConstraint(
            "supplier_id",
            name="uq_supplier_inspection_schedules_supplier_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 巡检天数：仅允许 3 / 7 / 10
    query_days: Mapped[int] = mapped_column(Integer, nullable=False)
    # 收件邮箱，多个用英文逗号分隔
    emails: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    # 预留：最近一次由定时任务更新的发送时间（第三阶段使用）
    last_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_send_status: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
