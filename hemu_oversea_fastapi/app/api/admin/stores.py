from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import (
    Pagination,
    require_admin_user,
    require_supplier,
)
from app.core.errors import bad_request
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.store import (
    StoreAuthorize,
    StoreAuthorizePublic,
    StoreCreate,
    StoreDelete,
    StoreDetail,
    StoreDetailPublic,
    StoreList,
    StorePublic,
    StoreUpdate,
)
from app.schemas.store_inspection import (
    StoreInspectionPunishPublic,
    StoreInspectionPunishRequest,
)
from app.services import store_oauth, stores as store_service
from app.services.commerce import summarize_supplier_punish

router = APIRouter(
    prefix="/stores",
    tags=["admin:stores"],
    dependencies=[Depends(require_admin_user)],
)


@router.post("/list", response_model=ApiResponse[PageData[StorePublic]])
def list_stores(
    payload: StoreList,
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[StorePublic]]:
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        store_service.list_stores(
            db,
            keyword=payload.keyword,
            store_type=payload.store_type,
            supplier_id=payload.supplier_id,
            pagination=pagination,
        )
    )


@router.post("/detail", response_model=ApiResponse[StoreDetailPublic])
def detail_store(
    payload: StoreDetail,
    db: Session = Depends(get_db),
) -> ApiResponse[StoreDetailPublic]:
    return success(store_service.get_store_detail(db, payload.id))


@router.post(
    "/authorize-url",
    response_model=ApiResponse[StoreAuthorizePublic],
)
def create_store_authorize_url(
    payload: StoreAuthorize,
    current_user: User = Depends(require_supplier),
    db: Session = Depends(get_db),
) -> ApiResponse[StoreAuthorizePublic]:
    """按店铺类型生成平台授权链接（管理端登录后调用，前端再跳转）。"""
    authorize_url, store_type = store_oauth.create_authorize_url(
        db,
        store_id=payload.id,
        actor_id=current_user.id,
    )
    return success(
        StoreAuthorizePublic(
            store_id=payload.id,
            store_type=store_type,
            authorize_url=authorize_url,
        )
    )


@router.post("/create", status_code=201, response_model=ApiResponse[StorePublic])
def create_store(
    payload: StoreCreate,
    current_user: User = Depends(require_supplier),
    db: Session = Depends(get_db),
) -> ApiResponse[StorePublic]:
    if current_user.supplier_id is None:
        raise bad_request("当前账号未绑定供应商，无法创建店铺")
    store = store_service.create_store(
        db,
        store_type=payload.store_type,
        name=payload.name,
        identifier=payload.identifier,
        account=payload.account,
        password=payload.password,
        actor_id=current_user.id,
        supplier_id=current_user.supplier_id,
    )
    return success(store)


@router.post("/update", response_model=ApiResponse[StorePublic])
def update_store(
    payload: StoreUpdate,
    current_user: User = Depends(require_supplier),
    db: Session = Depends(get_db),
) -> ApiResponse[StorePublic]:
    store = store_service.update_store(
        db,
        store_id=payload.id,
        actor_id=current_user.id,
        store_type=payload.store_type,
        name=payload.name,
        identifier=payload.identifier,
        account=payload.account,
        password=payload.password,
    )
    return success(store)

@router.post("/delete", response_model=ApiResponse[dict])
def delete_store(
    payload: StoreDelete,
    current_user: User = Depends(require_supplier),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    store_service.soft_delete_store(
        db, store_id=payload.id, actor_id=current_user.id
    )
    return success({})


@router.post(
    "/inspection/punish",
    response_model=ApiResponse[StoreInspectionPunishPublic],
    summary="店铺巡检：处罚信息汇总",
)
def inspect_store_punish(
    payload: StoreInspectionPunishRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[StoreInspectionPunishPublic]:
    """按供应商或单店汇总敦煌处罚信息；仅返回 punishStatus=\"1\" 的列表。"""
    summary = summarize_supplier_punish(
        db,
        supplier_id=payload.supplier_id,
        store_id=payload.store_id,
        query_days=payload.query_days,
        page_no=payload.page_no,
        page_size=payload.page_size,
    )
    punish_list = [
        item
        for item in summary.stores_summary.punish_list
        if str(item.get("punishStatus")) == "1"
    ]
    return success(
        StoreInspectionPunishPublic(
            items=punish_list,
            start_date=summary.start_date,
            end_date=summary.end_date,
        )
    )
