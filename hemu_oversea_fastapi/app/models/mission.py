"""任务、敦煌裂变任务数据、执行日志。"""

from datetime import datetime

from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

MISSION_STATUS_PENDING = "pending"
MISSION_STATUS_RUNNING = "running"
MISSION_STATUS_FINISHED = "finished"
MISSION_STATUS_MARKED_FINISHED = "marked_finished"

# 任务类型（列表筛选用；编辑/详情表单不展示）
MISSION_TYPE_FISSION_DH = "fission_dh"
MISSION_TYPE_HOTSALE_DH = "hotsale_dh"
MISSION_TYPES = frozenset({MISSION_TYPE_FISSION_DH, MISSION_TYPE_HOTSALE_DH})

FISSION_STATUS_PENDING = "pending"
FISSION_STATUS_SUCCESS = "success"
FISSION_STATUS_FAILED = "failed"
FISSION_STATUS_MARKED_FINISHED = "marked_finished"
FISSION_STATUSES = frozenset(
    {
        FISSION_STATUS_PENDING,
        FISSION_STATUS_SUCCESS,
        FISSION_STATUS_FAILED,
        FISSION_STATUS_MARKED_FINISHED,
    }
)

# 热卖采集任务数据状态（进行中 / 已完成 / 失败 / 标记结束）
HOTSALE_STATUS_PENDING = "pending"
HOTSALE_STATUS_SUCCESS = "success"
HOTSALE_STATUS_FAILED = "failed"
HOTSALE_STATUS_MARKED_FINISHED = "marked_finished"
HOTSALE_STATUSES = frozenset(
    {
        HOTSALE_STATUS_PENDING,
        HOTSALE_STATUS_SUCCESS,
        HOTSALE_STATUS_FAILED,
        HOTSALE_STATUS_MARKED_FINISHED,
    }
)


class Mission(Base):
    """供应商任务（按 type 区分业务：商品裂变 / 热卖采集等）。"""

    __tablename__ = "missions"
    __table_args__ = (
        Index("ix_missions_supplier_status", "supplier_id", "status"),
        Index("ix_missions_supplier_worker", "supplier_id", "worker_id"),
        Index("ix_missions_supplier_type", "supplier_id", "type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=MISSION_TYPE_FISSION_DH,
        comment="任务类型：fission_dh=商品裂变；hotsale_dh=热卖采集",
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


class MissionDataDhHotsale(Base):
    """敦煌热卖品任务数据（由浏览器扩展采集回传入库）。"""

    __tablename__ = "mission_data_dh_hotsale"
    __table_args__ = (
        Index("ix_mission_data_dh_hotsale_mission_id", "mission_id"),
        Index(
            "ix_mission_data_dh_hotsale_supplier_mission",
            "supplier_id",
            "mission_id",
        ),
        Index("ix_mission_data_dh_hotsale_item_code", "item_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(
        ForeignKey("missions.id", ondelete="RESTRICT"),
        nullable=False,
        comment="任务 ID",
    )
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"),
        nullable=False,
        comment="供应商 ID",
    )
    item_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="产品编码 item_code（多从产品链接解析）",
    )
    product_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="产品链接 product_url",
    )
    product_name_short: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="产品简称 product_name_short（接口 productName 截断展示）",
    )
    product_name: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="产品名称 product_name",
    )
    main_image_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="产品主图 main_image_url（接口 imageUrl）",
    )
    cate_name: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="分类名称（商品详情提取时写入，取 category.name）",
    )
    cate_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="分类 ID（商品详情提取时写入，取 category.id / pub_id）",
    )
    store_name: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
        comment="店铺名称（商品详情提取时写入，取 shop.name）",
    )
    store_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="店铺 ID（商品详情提取时写入，取 shop.seq）",
    )
    price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="价格（商品详情提取时写入，取 price.single_price）",
    )
    sales_num: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="销量（商品详情提取时写入，取 sales.display 转 int）",
    )
    last_modify_date: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="商品最近修改时间（详情页 last_modify_date 原文）",
    )
    deal: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="成交量指数 deal",
    )
    deal_amount: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="成交金额指数 deal_amount（接口 dealAmount）",
    )
    deal_persons: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="成交人数指数 deal_persons（接口 dealPersons）",
    )
    collect_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=HOTSALE_STATUS_PENDING,
        comment="采集状态：pending/success/failed/marked_finished",
    )
    collect_msg: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="采集信息反馈；失败时写入原因",
    )
    rank_no: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="成交排名 rank_no（接口 rankNo）",
    )
    parse_raw_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="商品详情页解析后的完整结构化数据（标题/价格/类目/销量/起订/包装等）",
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="创建人",
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="更新人",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="删除时间（软删）",
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
