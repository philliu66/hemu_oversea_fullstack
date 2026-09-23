"""任务、敦煌裂变任务数据、执行日志。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

MISSION_STATUS_PENDING = "pending"
MISSION_STATUS_RUNNING = "running"
MISSION_STATUS_FINISHED = "finished"
MISSION_STATUS_MARKED_FINISHED = "marked_finished"

FISSION_STATUS_PENDING = "pending"
FISSION_STATUS_SUCCESS = "success"
FISSION_STATUS_FAILED = "failed"


class Mission(Base):
    """商品裂变任务。"""

    __tablename__ = "missions"
    __table_args__ = (
        Index("ix_missions_supplier_status", "supplier_id", "status"),
        Index("ix_missions_supplier_worker", "supplier_id", "worker_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=MISSION_STATUS_PENDING,
    )
    worker_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_by: Mapped[int | None] = mapped_column(
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

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class MissionDataDhFission(Base):
    """敦煌裂变任务数据。只保存种子定位和本次覆盖内容，不存商品正文。"""

    __tablename__ = "mission_data_dh_fission"
    __table_args__ = (
        Index(
            "uq_mission_data_dh_fission_mission_seed_active",
            "mission_id",
            "seed_product_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_mission_data_dh_fission_mission_id", "mission_id"),
        Index(
            "ix_mission_data_dh_fission_supplier_mission",
            "supplier_id",
            "mission_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(
        ForeignKey("missions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    seed_product_id: Mapped[int] = mapped_column(
        ForeignKey("product_dh.id", ondelete="RESTRICT"),
        nullable=False,
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=False,
    )
    item_code: Mapped[str] = mapped_column(String(64))
    site_id: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        server_default="EN",
    )
    fission_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=FISSION_STATUS_PENDING,
    )
    fission_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    update_data_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_by: Mapped[int | None] = mapped_column(
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

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class MissionLog(Base):
    """任务执行日志。"""

    __tablename__ = "mission_logs"
    __table_args__ = (
        Index("ix_mission_logs_mission_started", "mission_id", "started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(
        ForeignKey("missions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    operator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    success_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    fail_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
