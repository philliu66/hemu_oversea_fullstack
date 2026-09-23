from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MissionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100, description="任务标题")
    description: str | None = Field(default=None, description="任务描述")
    worker_id: int = Field(ge=1, description="指定人员用户 ID")


class MissionList(BaseModel):
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


class MissionFissionDataList(BaseModel):
    mission_id: int = Field(ge=1, description="任务 ID")
    supplier_id: int | None = Field(
        default=None,
        description="供应商 ID。供应商身份忽略该字段；平台身份必填",
    )
    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class MissionFissionDataAdd(BaseModel):
    mission_id: int = Field(ge=1, description="任务 ID")
    supplier_id: int | None = Field(default=None, description="供应商 ID，平台身份使用")
    product_ids: list[int] = Field(default_factory=list, description="预留：选中的种子商品 ID")


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
    item_code: str
    site_id: str
    fission_status: str
    fission_msg: str | None
    update_data_json: dict[str, Any]
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
