from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MissionType = Literal["fission_dh", "hotsale_dh"]


class MissionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100, description="任务标题")
    description: str | None = Field(default=None, description="任务描述")
    worker_id: int = Field(ge=1, description="指定人员用户 ID")
    type: MissionType = Field(
        description=(
            "任务类型（由前端入口传入，不可编辑）。"
            "fission_dh=商品裂变；hotsale_dh=热卖采集"
        ),
    )
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略该字段；平台身份必填",
    )


class MissionUpdate(BaseModel):
    id: int = Field(ge=1, description="任务 ID")
    title: str = Field(min_length=1, max_length=100, description="任务标题")
    description: str | None = Field(default=None, description="任务描述")
    worker_id: int = Field(ge=1, description="指定人员用户 ID")
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略；平台身份建议传入",
    )


class MissionList(BaseModel):
    type: MissionType = Field(
        description="任务类型筛选：fission_dh / hotsale_dh（按菜单入口传入）",
    )
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略该字段；平台身份必填",
    )
    keyword: str | None = Field(default=None, description="按标题模糊搜索")
    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class MissionDetail(BaseModel):
    id: int = Field(ge=1, description="任务 ID")
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略该字段；平台身份必填",
    )


class MissionMarkFinished(BaseModel):
    id: int = Field(ge=1, description="任务 ID")
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略；平台身份建议传入",
    )


class MissionFissionDataList(BaseModel):
    mission_id: int = Field(ge=1, description="任务 ID")
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略该字段；平台身份必填",
    )
    keyword: str | None = Field(
        default=None,
        description="搜索内容：按商品标题 / 原商品编码 / 新商品编码模糊匹配；空=不限",
    )
    fission_status: str | None = Field(
        default=None,
        description=(
            "裂变状态筛选：pending=待裂变；success=成功；failed=失败；"
            "marked_finished=标记结束；空或 all=全部"
        ),
    )
    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class MissionFissionDataAdd(BaseModel):
    mission_id: int = Field(ge=1, description="任务 ID")
    seed_product_id: int = Field(ge=1, description="种子商品 ID")
    update_json: dict[str, Any] = Field(
        default_factory=dict,
        description="相对最初种子详情的完整差异",
    )
    raw_json: dict[str, Any] = Field(
        description="修改完成后的完整正文，发布直接使用",
    )
    seed_json: dict[str, Any] | None = Field(
        default=None,
        description="加入时冻结的种子详情（与前端编辑基线一致）；缺省则用商品 raw_json",
    )


class MissionFissionDataDetail(BaseModel):
    id: int = Field(ge=1, description="任务数据 ID")
    mission_id: int = Field(ge=1, description="任务 ID")
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略该字段；平台身份必填",
    )


class MissionFissionDataDetailPublic(BaseModel):
    id: int
    mission_id: int
    supplier_id: int = Field(description="所属供应商 ID（由任务数据记录带出）")
    seed_product_id: int
    fission_status: str
    update_json: dict[str, Any]
    raw_json: dict[str, Any] | None = None
    seed_json: dict[str, Any] | None = None


class MissionFissionDataUpdate(BaseModel):
    id: int = Field(ge=1, description="任务数据 ID")
    mission_id: int = Field(ge=1, description="任务 ID")
    update_json: dict[str, Any] = Field(
        default_factory=dict,
        description="相对最初种子详情的完整差异（按种子重算）",
    )
    raw_json: dict[str, Any] = Field(
        description="修改完成后的完整正文，发布直接使用",
    )


class MissionFissionDataOperate(BaseModel):
    """删除 / 标记结束：id 支持单个或数组。"""

    id: int | list[int] = Field(description="任务数据 ID，单个或数组")
    mission_id: int = Field(ge=1, description="任务 ID")

    @model_validator(mode="after")
    def _require_ids(self) -> "MissionFissionDataOperate":
        ids = self.resolved_ids()
        if not ids:
            raise ValueError("请至少选择一条任务数据")
        if any(i < 1 for i in ids):
            raise ValueError("任务数据 ID 无效")
        return self

    def resolved_ids(self) -> list[int]:
        """归一化为去重后的 ID 列表（保持顺序）。"""
        raw = [self.id] if isinstance(self.id, int) else list(self.id)
        seen: set[int] = set()
        out: list[int] = []
        for i in raw:
            if i not in seen:
                seen.add(i)
                out.append(i)
        return out


class MissionFissionDataImport(BaseModel):
    mission_id: int = Field(ge=1, description="任务 ID")
    supplier_id: int | None = Field(default=None, description="供应商 ID，平台身份使用")


class MissionLogList(BaseModel):
    mission_id: int = Field(ge=1, description="任务 ID")
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略该字段；平台身份必填",
    )
    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class MissionExecute(BaseModel):
    mission_id: int = Field(ge=1, description="任务 ID")
    supplier_id: int | None = Field(default=None, description="供应商 ID，平台身份使用")


class MissionPublic(BaseModel):
    id: int
    supplier_id: int
    supplier_name: str | None = Field(default=None, description="供应商名称")
    type: MissionType = Field(
        description="任务类型：fission_dh / hotsale_dh（列表筛选用，表单不展示）",
    )
    title: str
    description: str | None
    status: str
    worker_id: int
    worker_username: str
    worker_nickname: str
    created_by: int | None
    creator_username: str | None
    creator_nickname: str | None
    created_at: datetime
    updated_at: datetime


class MissionFissionDataPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mission_id: int
    supplier_id: int
    seed_product_id: int
    store_id: int
    store_name: str | None = Field(default=None, description="店铺名称，列表展示用")
    seed_item_code: str | None = Field(
        default=None,
        description="原商品编码（种子商品 item_code），列表展示用",
    )
    item_code: str | None = Field(
        default=None,
        description="新商品编码。发布成功前为空，成功后为官方 API 返回值",
    )
    site_id: str
    cate_pub_id: str | None = None
    item_name: str | None = None
    main_image_url: str | None = None
    update_json: dict[str, Any]
    fission_status: str
    fission_msg: str | None
    fission_at: datetime | None = None
    created_by: int | None
    created_at: datetime
    updated_at: datetime


class MissionLogPublic(BaseModel):
    id: int
    mission_id: int
    operator_id: int
    operator_username: str | None
    operator_nickname: str | None
    started_at: datetime
    ended_at: datetime | None
    success_count: int
    fail_count: int
    remark: str | None
    created_at: datetime


class MissionHotsaleDataList(BaseModel):
    mission_id: int = Field(ge=1, description="任务 ID")
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略该字段；平台身份必填",
    )
    keyword: str | None = Field(
        default=None,
        description="搜索内容：按产品名称 / 产品简称 / 商品编码 / 店铺名称模糊匹配；空=不限",
    )
    collect_status: str | None = Field(
        default=None,
        description=(
            "任务数据状态筛选：pending=进行中；success=已完成；failed=失败；"
            "marked_finished=标记结束；空或 all=全部"
        ),
    )
    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class MissionHotsaleDataImport(BaseModel):
    """扩展回传的热卖榜接口响应整包入库。"""

    mission_id: int = Field(ge=1, description="任务 ID")
    payload: dict[str, Any] = Field(
        description="扩展 SYNC_CONFIRM 的原始接口响应（含 currentCategory / pageInfoOfProductRank）",
    )
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略；平台身份建议传入",
    )


class MissionHotsaleDataOperate(BaseModel):
    """删除 / 标记结束：id 支持单个或数组。"""

    id: int | list[int] = Field(description="任务数据 ID，单个或数组")
    mission_id: int = Field(ge=1, description="任务 ID")

    @model_validator(mode="after")
    def _require_ids(self) -> "MissionHotsaleDataOperate":
        ids = self.resolved_ids()
        if not ids:
            raise ValueError("请至少选择一条任务数据")
        if any(i < 1 for i in ids):
            raise ValueError("任务数据 ID 无效")
        return self

    def resolved_ids(self) -> list[int]:
        """归一化为去重后的 ID 列表（保持顺序）。"""
        raw = [self.id] if isinstance(self.id, int) else list(self.id)
        seen: set[int] = set()
        out: list[int] = []
        for i in raw:
            if i not in seen:
                seen.add(i)
                out.append(i)
        return out


class MissionHotsaleDataImportResult(BaseModel):
    created: int = Field(description="新插入条数")
    updated: int = Field(description="按 item_code 更新条数")
    total: int = Field(description="本次处理条数")
    cate_name: str | None = Field(default=None, description="品类名称")
    mission_status: str = Field(
        description="入库后同步的任务状态：有未闭环则为 running，否则 finished（人工标记结束除外）",
    )


class MissionHotsaleDataExtract(BaseModel):
    """热卖产品信息提取。

    选数方式二选一：
    - ``mission_data_ids``：指定任务数据 ID（单个时长度为 1；须为 pending / failed）
    - ``mission_id``：批量提取该任务下所有 pending / failed（跳过已完成 / 标记结束）

    取数方式：
    - 不传 ``flight_content``：服务端按行内 ``product_url`` 自行发起 RSC 拉取并解析入库
      （适合后台批量；插件批量请改为前端串行传 ``flight_content``）
    - 传 ``flight_content``：表示 Flight 已由浏览器扩展拉取，服务端只解析入库、不再向上游发 RSC。
      此时必须且仅能传 **1 条** ``mission_data_ids``（不可与 ``mission_id`` 同用）
    """

    mission_data_ids: list[int] | None = Field(
        default=None,
        description=(
            "任务数据 ID 数组（须为 pending / failed）。"
            "传 flight_content 时必须且仅能为 1 条"
        ),
    )
    mission_id: int | None = Field(
        default=None,
        ge=1,
        description=(
            "任务 ID：服务端批量提取该任务下所有 pending / failed。"
            "不可与 flight_content 同用"
        ),
    )
    flight_content: str | None = Field(
        default=None,
        description=(
            "浏览器扩展拉取的完整 RSC Flight 原文。"
            "有值时优先解析入库，服务端不发 RSC；"
            "须配合恰好 1 条 mission_data_ids"
        ),
    )
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略；平台身份建议传入",
    )

    @model_validator(mode="after")
    def _require_one_mode(self) -> "MissionHotsaleDataExtract":
        has_mission = self.mission_id is not None
        ids = self.resolved_data_ids()
        has_ids = bool(ids)
        flight = (self.flight_content or "").strip()
        has_flight = bool(flight)

        if has_mission == has_ids:
            raise ValueError("请传 mission_id 或 mission_data_ids 二者之一")
        if has_ids and any(i < 1 for i in ids):
            raise ValueError("任务数据 ID 无效")
        if has_flight:
            if has_mission:
                raise ValueError("传 flight_content 时不可使用 mission_id，请传单条 mission_data_ids")
            if len(ids) != 1:
                raise ValueError("传 flight_content 时 mission_data_ids 必须且仅能为 1 条")
            # 归一化去掉首尾空白，避免无意义空串被当成有内容
            self.flight_content = flight
        else:
            self.flight_content = None
        return self

    def resolved_data_ids(self) -> list[int]:
        """归一化为去重后的任务数据 ID 列表（保持顺序）。"""
        if not self.mission_data_ids:
            return []
        seen: set[int] = set()
        out: list[int] = []
        for i in self.mission_data_ids:
            if i not in seen:
                seen.add(i)
                out.append(i)
        return out


class MissionHotsaleDataExtractFailItem(BaseModel):
    id: int = Field(description="任务数据 ID")
    product_url: str | None = Field(default=None, description="商品链接")
    reason: str = Field(description="失败原因")


class MissionHotsaleDataExtractResult(BaseModel):
    success_count: int = Field(description="成功条数")
    fail_count: int = Field(description="失败条数")
    skipped_count: int = Field(
        default=0,
        description="跳过条数（批量模式下非进行中，或不具备提取条件）",
    )
    fails: list[MissionHotsaleDataExtractFailItem] = Field(
        default_factory=list,
        description="失败明细，供前端提示",
    )
    mission_id: int | None = Field(
        default=None,
        description="关联任务 ID（按任务批量或由数据反推）",
    )
    mission_finished: bool = Field(
        default=False,
        description="同步后任务是否为已完成（finished）",
    )
    mission_status: str | None = Field(
        default=None,
        description="同步后的任务状态；有未闭环(pending/failed)为 running，否则 finished（人工标记结束除外）",
    )


class MissionHotsaleDataPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mission_id: int
    supplier_id: int
    item_code: str | None = None
    product_url: str | None = None
    product_name_short: str | None = None
    product_name: str | None = None
    main_image_url: str | None = None
    cate_name: str | None = None
    cate_id: str | None = None
    store_name: str | None = None
    store_id: int | None = None
    price: Decimal | None = None
    sales_num: int | None = None
    last_modify_date: str | None = None
    deal: str | None = None
    deal_amount: str | None = None
    deal_persons: str | None = None
    collect_status: str
    collect_msg: str | None = None
    rank_no: int | None = None
    created_by: int | None = None
    updated_by: int | None = None
    created_at: datetime
    updated_at: datetime
