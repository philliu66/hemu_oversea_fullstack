from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Pagination, require_admin_user, require_perm
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.mission import (
    MissionCreate,
    MissionDetail,
    MissionExecute,
    MissionFissionDataAdd,
    MissionFissionDataDetail,
    MissionFissionDataDetailPublic,
    MissionFissionDataImport,
    MissionFissionDataList,
    MissionFissionDataOperate,
    MissionFissionDataPublic,
    MissionFissionDataUpdate,
    MissionHotsaleDataExtract,
    MissionHotsaleDataExtractResult,
    MissionHotsaleDataImport,
    MissionHotsaleDataImportResult,
    MissionHotsaleDataList,
    MissionHotsaleDataOperate,
    MissionHotsaleDataPublic,
    MissionList,
    MissionLogList,
    MissionLogPublic,
    MissionMarkFinished,
    MissionPublic,
    MissionUpdate,
)
from app.services import missions as mission_service
from app.services.supplier_scope import assert_supplier_data_writable

router = APIRouter(
    prefix="/missions",
    tags=["admin:mission"],
    dependencies=[Depends(require_admin_user)],
)


@router.post("/list", response_model=ApiResponse[PageData[MissionPublic]])
def list_missions(
    payload: MissionList,
    current_user: User = Depends(
        require_perm("mission.fission", "mission.hotsale", require_all=False)
    ),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[MissionPublic]]:
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        mission_service.list_missions(
            db,
            actor=current_user,
            supplier_id=payload.supplier_id,
            keyword=payload.keyword,
            mission_type=payload.type,
            pagination=pagination,
        )
    )


@router.post("/detail", response_model=ApiResponse[MissionPublic])
def detail_mission(
    payload: MissionDetail,
    current_user: User = Depends(
        require_perm("mission.fission", "mission.hotsale", require_all=False)
    ),
    db: Session = Depends(get_db),
) -> ApiResponse[MissionPublic]:
    return success(
        mission_service.get_mission(
            db,
            mission_id=payload.id,
            actor=current_user,
            supplier_id=payload.supplier_id,
        )
    )


@router.post("/create", status_code=201, response_model=ApiResponse[MissionPublic])
def create_mission(
    payload: MissionCreate,
    current_user: User = Depends(
        require_perm(
            "mission.fission.create",
            "mission.hotsale.create",
            require_all=False,
        )
    ),
    db: Session = Depends(get_db),
) -> ApiResponse[MissionPublic]:
    assert_supplier_data_writable(current_user)
    return success(
        mission_service.create_mission(
            db,
            actor=current_user,
            title=payload.title,
            description=payload.description,
            worker_id=payload.worker_id,
            mission_type=payload.type,
            supplier_id=payload.supplier_id,
        )
    )


@router.post("/update", response_model=ApiResponse[MissionPublic])
def update_mission(
    payload: MissionUpdate,
    current_user: User = Depends(
        require_perm(
            "mission.fission.create",
            "mission.hotsale.create",
            require_all=False,
        )
    ),
    db: Session = Depends(get_db),
) -> ApiResponse[MissionPublic]:
    assert_supplier_data_writable(current_user)
    return success(
        mission_service.update_mission(
            db,
            actor=current_user,
            mission_id=payload.id,
            title=payload.title,
            description=payload.description,
            worker_id=payload.worker_id,
            supplier_id=payload.supplier_id,
        )
    )


@router.post("/mark-finished", response_model=ApiResponse[MissionPublic])
def mark_mission_finished(
    payload: MissionMarkFinished,
    current_user: User = Depends(
        require_perm(
            "mission.fission.finish",
            "mission.hotsale.finish",
            require_all=False,
        )
    ),
    db: Session = Depends(get_db),
) -> ApiResponse[MissionPublic]:
    assert_supplier_data_writable(current_user)
    return success(
        mission_service.mark_mission_finished(
            db,
            mission_id=payload.id,
            actor=current_user,
            supplier_id=payload.supplier_id,
        )
    )


@router.post(
    "/fission-data/list",
    response_model=ApiResponse[PageData[MissionFissionDataPublic]],
)
def list_fission_data(
    payload: MissionFissionDataList,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[MissionFissionDataPublic]]:
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        mission_service.list_fission_data(
            db,
            mission_id=payload.mission_id,
            actor=current_user,
            supplier_id=payload.supplier_id,
            pagination=pagination,
            keyword=payload.keyword,
            fission_status=payload.fission_status,
        )
    )


@router.post("/logs/list", response_model=ApiResponse[PageData[MissionLogPublic]])
def list_logs(
    payload: MissionLogList,
    current_user: User = Depends(require_perm("mission.logs")),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[MissionLogPublic]]:
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        mission_service.list_logs(
            db,
            mission_id=payload.mission_id,
            actor=current_user,
            supplier_id=payload.supplier_id,
            pagination=pagination,
        )
    )


@router.post(
    "/fission-data/detail",
    response_model=ApiResponse[MissionFissionDataDetailPublic],
)
def fission_data_detail(
    payload: MissionFissionDataDetail,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[MissionFissionDataDetailPublic]:
    return success(
        mission_service.get_fission_data_detail(
            db,
            actor=current_user,
            mission_id=payload.mission_id,
            data_id=payload.id,
            supplier_id=payload.supplier_id,
        )
    )


@router.post(
    "/fission-data/add",
    response_model=ApiResponse[MissionFissionDataPublic],
)
def add_fission_data(
    payload: MissionFissionDataAdd,
    current_user: User = Depends(require_perm("mission.fission.data")),
    db: Session = Depends(get_db),
) -> ApiResponse[MissionFissionDataPublic]:
    assert_supplier_data_writable(current_user)
    return success(
        mission_service.add_fission_data(
            db,
            actor=current_user,
            mission_id=payload.mission_id,
            seed_product_id=payload.seed_product_id,
            update_json=payload.update_json,
            raw_json=payload.raw_json,
            seed_json=payload.seed_json,
        )
    )


@router.post(
    "/fission-data/update",
    response_model=ApiResponse[MissionFissionDataPublic],
)
def update_fission_data(
    payload: MissionFissionDataUpdate,
    current_user: User = Depends(require_perm("mission.fission.data")),
    db: Session = Depends(get_db),
) -> ApiResponse[MissionFissionDataPublic]:
    assert_supplier_data_writable(current_user)
    return success(
        mission_service.update_fission_data(
            db,
            actor=current_user,
            mission_id=payload.mission_id,
            data_id=payload.id,
            update_json=payload.update_json,
            raw_json=payload.raw_json,
        )
    )


@router.post("/fission-data/delete", response_model=ApiResponse[dict])
def delete_fission_data(
    payload: MissionFissionDataOperate,
    current_user: User = Depends(require_perm("mission.fission.data")),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    assert_supplier_data_writable(current_user)
    return success(
        mission_service.delete_fission_data(
            db,
            actor=current_user,
            mission_id=payload.mission_id,
            data_ids=payload.resolved_ids(),
        )
    )


@router.post(
    "/fission-data/mark-finished",
    response_model=ApiResponse[list[MissionFissionDataPublic]],
)
def mark_fission_data_finished(
    payload: MissionFissionDataOperate,
    current_user: User = Depends(require_perm("mission.fission.data")),
    db: Session = Depends(get_db),
) -> ApiResponse[list[MissionFissionDataPublic]]:
    assert_supplier_data_writable(current_user)
    return success(
        mission_service.mark_fission_data_finished(
            db,
            actor=current_user,
            mission_id=payload.mission_id,
            data_ids=payload.resolved_ids(),
        )
    )


@router.post("/fission-data/import", response_model=ApiResponse[dict])
def import_fission_data(
    payload: MissionFissionDataImport,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    assert_supplier_data_writable(current_user)
    mission_service.reject_placeholder(
        db,
        mission_id=payload.mission_id,
        actor=current_user,
        supplier_id=payload.supplier_id,
    )
    return success({})


@router.post(
    "/hotsale-data/list",
    response_model=ApiResponse[PageData[MissionHotsaleDataPublic]],
)
def list_hotsale_data(
    payload: MissionHotsaleDataList,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[MissionHotsaleDataPublic]]:
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        mission_service.list_hotsale_data(
            db,
            mission_id=payload.mission_id,
            actor=current_user,
            supplier_id=payload.supplier_id,
            pagination=pagination,
            keyword=payload.keyword,
            collect_status=payload.collect_status,
        )
    )


@router.post(
    "/hotsale-data/import",
    response_model=ApiResponse[MissionHotsaleDataImportResult],
)
def import_hotsale_data(
    payload: MissionHotsaleDataImport,
    current_user: User = Depends(require_perm("mission.hotsale.data")),
    db: Session = Depends(get_db),
) -> ApiResponse[MissionHotsaleDataImportResult]:
    assert_supplier_data_writable(current_user)
    return success(
        mission_service.import_hotsale_capture(
            db,
            actor=current_user,
            mission_id=payload.mission_id,
            payload=payload.payload,
            supplier_id=payload.supplier_id,
        )
    )


@router.post("/hotsale-data/delete", response_model=ApiResponse[dict])
def delete_hotsale_data(
    payload: MissionHotsaleDataOperate,
    current_user: User = Depends(require_perm("mission.hotsale.data")),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    assert_supplier_data_writable(current_user)
    return success(
        mission_service.delete_hotsale_data(
            db,
            actor=current_user,
            mission_id=payload.mission_id,
            data_ids=payload.resolved_ids(),
        )
    )


@router.post(
    "/hotsale-data/mark-finished",
    response_model=ApiResponse[list[MissionHotsaleDataPublic]],
)
def mark_hotsale_data_finished(
    payload: MissionHotsaleDataOperate,
    current_user: User = Depends(require_perm("mission.hotsale.data")),
    db: Session = Depends(get_db),
) -> ApiResponse[list[MissionHotsaleDataPublic]]:
    assert_supplier_data_writable(current_user)
    return success(
        mission_service.mark_hotsale_data_finished(
            db,
            actor=current_user,
            mission_id=payload.mission_id,
            data_ids=payload.resolved_ids(),
        )
    )


@router.post(
    "/hotsale-data/extract",
    response_model=ApiResponse[MissionHotsaleDataExtractResult],
    summary="热卖产品信息提取",
)
def extract_hotsale_data(
    payload: MissionHotsaleDataExtract,
    current_user: User = Depends(require_perm("mission.hotsale.data")),
    db: Session = Depends(get_db),
) -> ApiResponse[MissionHotsaleDataExtractResult]:
    """
    解析敦煌商品详情并入库（写入 `parse_raw_json`，成功则 `collect_status=success`）。

    **选数（二选一）**
    - `mission_data_ids`：指定任务数据（须为 pending / failed）
    - `mission_id`：该任务下全部 pending / failed（跳过已完成 / 标记结束）

    **取数**
    - 不传 `flight_content`：服务端按行内 `product_url` 发起 RSC 拉取后解析（后台批量）
    - 传 `flight_content`：Flight 已由浏览器扩展拉取，服务端只解析入库、不再向上游发 RSC；
      此时必须且仅传 1 条 `mission_data_ids`（插件单条入库；批量请前端串行多次调用）

    任务已完成 / 标记结束后仍可对 pending / failed 手动再提取。
    结束后按未闭环同步任务 `running` / `finished`（`marked_finished` 除外），
    结果带回 `mission_status`、成功/失败数与失败明细。
    """
    assert_supplier_data_writable(current_user)
    return success(
        mission_service.extract_hotsale_product_pages(
            db,
            actor=current_user,
            mission_id=payload.mission_id,
            mission_data_ids=payload.resolved_data_ids() or None,
            flight_content=payload.flight_content,
            supplier_id=payload.supplier_id,
        )
    )


@router.post("/execute", response_model=ApiResponse[dict])
def execute_mission(
    payload: MissionExecute,
    current_user: User = Depends(require_perm("mission.fission")),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    assert_supplier_data_writable(current_user)
    return success(
        mission_service.execute_mission(
            db,
            mission_id=payload.mission_id,
            actor=current_user,
            supplier_id=payload.supplier_id,
        )
    )
