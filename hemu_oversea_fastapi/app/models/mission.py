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
FISSION_STATUS_MARKED_FINISHED = "marked_finished"


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
    """敦煌裂变任务数据。

    seed_json 是加入任务时冻结的种子详情，之后不再修改。
    raw_json 是套上改动后的完整正文，发布直接使用。
    update_json 是相对 seed_json 的完整差异，每次保存都按最初种子重算。
    """

    __tablename__ = "mission_data_dh_fission"
    __table_args__ = (
        Index("ix_mission_data_dh_fission_mission_id", "mission_id"),
        Index(
            "ix_mission_data_dh_fission_supplier_mission",
            "supplier_id",
            "mission_id",
        ),
        Index("ix_mission_data_dh_fission_store_id", "store_id"),
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
        comment="原种子商品 ID",
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="RESTRICT"),
        nullable=False,
        comment="目标店铺。未改店铺时等于种子店铺",
    )
    item_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="新商品编码。发布成功前为空，成功后写入官方 API 返回值",
    )
    site_id: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        server_default="EN",
        comment="站点语言（siteId），默认 EN",
    )
    cate_pub_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="改完后的发布类目 ID（catePubId）",
    )
    item_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="改完后的标题（itemBase.itemName）",
    )
    main_image_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="改完后的列表主图相对路径",
    )
    seed_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="加入任务时冻结的种子详情，之后不再修改",
    )
    raw_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="种子详情套上改动后的完整正文，发布直接使用",
    )
    update_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="相对 seed_json 的完整差异，每次保存都按最初种子重算",
    )
    fission_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=FISSION_STATUS_PENDING,
        comment="裂变状态：pending/success/failed/marked_finished",
    )
    fission_msg: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="裂变信息",
    )
    fission_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="裂变执行时间，尚未执行时为空",
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
