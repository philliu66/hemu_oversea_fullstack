from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Pagination, require_admin_user, require_supplier_admin
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.mission import (
    MissionCreate,
    MissionDetail,
    MissionExecute,
    MissionFissionDataAdd,
    MissionFissionDataImport,
    MissionFissionDataList,
    MissionFissionDataOperate,
    MissionFissionDataPublic,
    MissionList,
    MissionLogList,
    MissionLogPublic,
    MissionMarkFinished,
    MissionPublic,
)
from app.services import missions as mission_service

router = APIRouter(
    prefix="/missions",
    tags=["admin:mission"],
    dependencies=[Depends(require_admin_user)],
)


@router.post("/list", response_model=ApiResponse[PageData[MissionPublic]])
def list_missions(
    payload: MissionList,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[MissionPublic]]:
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        mission_service.list_missions(
            db,
            actor=current_user,
            supplier_id=payload.supplier_id,
            keyword=payload.keyword,
            pagination=pagination,
        )
    )


@router.post("/detail", response_model=ApiResponse[MissionPublic])
def detail_mission(
    payload: MissionDetail,
    current_user: User = Depends(require_admin_user),
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
    current_user: User = Depends(require_supplier_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[MissionPublic]:
    return success(
        mission_service.create_mission(
            db,
            actor=current_user,
            title=payload.title,
            description=payload.description,
            worker_id=payload.worker_id,
        )
    )


@router.post("/mark-finished", response_model=ApiResponse[MissionPublic])
def mark_mission_finished(
    payload: MissionMarkFinished,
    current_user: User = Depends(require_supplier_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[MissionPublic]:
    return success(
        mission_service.mark_mission_finished(
            db,
            mission_id=payload.id,
            actor=current_user,
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
        )
    )


@router.post("/logs/list", response_model=ApiResponse[PageData[MissionLogPublic]])
def list_logs(
    payload: MissionLogList,
    current_user: User = Depends(require_admin_user),
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
    "/fission-data/add",
    response_model=ApiResponse[MissionFissionDataPublic],
)
def add_fission_data(
    payload: MissionFissionDataAdd,
    current_user: User = Depends(require_supplier_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[MissionFissionDataPublic]:
    return success(
        mission_service.add_fission_data(
            db,
            actor=current_user,
            mission_id=payload.mission_id,
            seed_product_id=payload.seed_product_id,
            update_json=payload.update_json,
        )
    )


@router.post("/fission-data/delete", response_model=ApiResponse[dict])
def delete_fission_data(
    payload: MissionFissionDataOperate,
    current_user: User = Depends(require_supplier_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    mission_service.delete_fission_data(
        db,
        actor=current_user,
        mission_id=payload.mission_id,
        data_id=payload.id,
    )
    return success({})


@router.post(
    "/fission-data/mark-finished",
    response_model=ApiResponse[MissionFissionDataPublic],
)
def mark_fission_data_finished(
    payload: MissionFissionDataOperate,
    current_user: User = Depends(require_supplier_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[MissionFissionDataPublic]:
    return success(
        mission_service.mark_fission_data_finished(
            db,
            actor=current_user,
            mission_id=payload.mission_id,
            data_id=payload.id,
        )
    )


@router.post("/fission-data/import", response_model=ApiResponse[dict])
def import_fission_data(
    payload: MissionFissionDataImport,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    mission_service.reject_placeholder(
        db,
        mission_id=payload.mission_id,
        actor=current_user,
        supplier_id=payload.supplier_id,
    )
    return success({})


@router.post("/execute", response_model=ApiResponse[dict])
def execute_mission(
    payload: MissionExecute,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    mission_service.reject_placeholder(
        db,
        mission_id=payload.mission_id,
        actor=current_user,
        supplier_id=payload.supplier_id,
    )
    return success({})
