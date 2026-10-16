from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import (
    Pagination,
    require_admin_user,
    require_perm,
)
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.supplier import (
    SupplierCreate,
    SupplierDelete,
    SupplierDetail,
    SupplierDetailPublic,
    SupplierList,
    SupplierOption,
    SupplierPublic,
    SupplierUpdate,
)
from app.schemas.mail_send_log import (
    MailSendLogListRequest,
    MailSendLogPublic,
    SupplierDailyInspectionRunPublic,
    SupplierDailyInspectionRunRequest,
)
from app.schemas.supplier_inspection_schedule import (
    SupplierInspectionScheduleDelete,
    SupplierInspectionScheduleGet,
    SupplierInspectionSchedulePublic,
    SupplierInspectionScheduleSave,
)
from app.services import mail_send_logs as mail_send_log_service
from app.services import permissions as perm_service
from app.services import supplier_daily_inspection as daily_inspection_service
from app.services import suppliers as supplier_service
from app.services import supplier_inspection_schedule as inspection_schedule_service
from app.services.supplier_scope import resolve_supplier_id

router = APIRouter(
    prefix="/suppliers",
    tags=["admin:suppliers"],
    dependencies=[Depends(require_admin_user)],
)


@router.post("/list", response_model=ApiResponse[PageData[SupplierPublic]])
def list_suppliers(
    payload: SupplierList,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[SupplierPublic]]:
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        supplier_service.list_suppliers(
            db,
            actor=current_user,
            keyword=payload.keyword,
            pagination=pagination,
        )
    )


@router.post("/options", response_model=ApiResponse[list[SupplierOption]])
def list_supplier_options(
    payload: SupplierList,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[list[SupplierOption]]:
    """平台角色下拉：按权限范围返回可选供应商。"""
    return success(
        supplier_service.list_supplier_options(
            db,
            actor=current_user,
            keyword=payload.keyword,
        )
    )


@router.post("/detail", response_model=ApiResponse[SupplierDetailPublic])
def detail_supplier(
    payload: SupplierDetail,
    db: Session = Depends(get_db),
) -> ApiResponse[SupplierDetailPublic]:
    supplier = supplier_service.get_supplier(db, payload.id)
    detail = SupplierDetailPublic.model_validate(supplier)
    detail.admin_username = supplier_service.get_supplier_admin_username(
        db, supplier.id
    )
    detail.permission_codes = perm_service.get_supplier_permission_codes(
        db, supplier.id
    )
    return success(detail)


@router.post("/create", status_code=201, response_model=ApiResponse[SupplierPublic])
def create_supplier(
    payload: SupplierCreate,
    current_user: User = Depends(require_perm("supplier.create")),
    db: Session = Depends(get_db),
) -> ApiResponse[SupplierPublic]:
    supplier = supplier_service.create_supplier(
        db,
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        admin_username=payload.admin_username,
        admin_password=payload.admin_password,
        permission_codes=payload.permission_codes,
        created_by=current_user.id,
    )
    return success(supplier_service.to_supplier_public(supplier))


@router.post("/update", response_model=ApiResponse[SupplierPublic])
def update_supplier(
    payload: SupplierUpdate,
    _: User = Depends(require_perm("supplier.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[SupplierPublic]:
    supplier = supplier_service.update_supplier(
        db,
        supplier_id=payload.id,
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        permission_codes=payload.permission_codes,
    )
    return success(supplier_service.to_supplier_public(supplier))


@router.post("/delete", response_model=ApiResponse[dict])
def delete_supplier(
    payload: SupplierDelete,
    _: User = Depends(require_perm("supplier.delete")),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    supplier_service.soft_delete_supplier(db, supplier_id=payload.id)
    return success({})


@router.post(
    "/inspection-schedule/get",
    response_model=ApiResponse[SupplierInspectionSchedulePublic | None],
    summary="获取供应商每日巡检设置",
)
def get_inspection_schedule(
    payload: SupplierInspectionScheduleGet,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[SupplierInspectionSchedulePublic | None]:
    """
    按供应商作用域读取每日巡检设置。

    - 供应商门户：使用当前账号绑定的 supplier_id
    - 平台：必须传 supplier_id
    - 未配置时 data 为 null
    """
    return success(
        inspection_schedule_service.get_schedule(
            db,
            actor=current_user,
            supplier_id=payload.supplier_id,
        )
    )


@router.post(
    "/inspection-schedule/save",
    response_model=ApiResponse[SupplierInspectionSchedulePublic],
    summary="保存供应商每日巡检设置",
)
def save_inspection_schedule(
    payload: SupplierInspectionScheduleSave,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[SupplierInspectionSchedulePublic]:
    """新建或更新每日巡检设置（平台账号默认不可写）。"""
    return success(
        inspection_schedule_service.save_schedule(
            db,
            actor=current_user,
            supplier_id=payload.supplier_id,
            query_days=payload.query_days,
            emails=payload.emails,
        )
    )


@router.post(
    "/inspection-schedule/delete",
    response_model=ApiResponse[dict],
    summary="删除供应商每日巡检设置",
)
def delete_inspection_schedule(
    payload: SupplierInspectionScheduleDelete,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    """删除每日巡检设置（平台账号默认不可写）。"""
    inspection_schedule_service.delete_schedule(
        db,
        actor=current_user,
        supplier_id=payload.supplier_id,
    )
    return success({})


@router.post(
    "/inspection/daily-run",
    response_model=ApiResponse[SupplierDailyInspectionRunPublic],
    summary="执行供应商每日巡检并发信",
)
def run_supplier_daily_inspection(
    payload: SupplierDailyInspectionRunRequest,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[SupplierDailyInspectionRunPublic]:
    """
    手动触发：读取巡检设置 → 汇总处罚/纠纷 → 发邮件 → 写发送记录。

    与后续定时任务调用同一 service：`run_supplier_daily_inspection`。
    成功/失败均会写入 mail_send_logs。
    """
    supplier_id = resolve_supplier_id(db, current_user, payload.supplier_id)
    return success(
        daily_inspection_service.run_supplier_daily_inspection(
            db,
            supplier_id=supplier_id,
        )
    )


@router.post(
    "/mail-send-logs/list",
    response_model=ApiResponse[PageData[MailSendLogPublic]],
    summary="查询邮件发送记录",
)
def list_mail_send_logs(
    payload: MailSendLogListRequest,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[MailSendLogPublic]]:
    """按供应商作用域查询邮件发送记录（可按 category / status 过滤）。"""
    supplier_id = resolve_supplier_id(db, current_user, payload.supplier_id)
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        mail_send_log_service.list_mail_send_logs(
            db,
            supplier_id=supplier_id,
            category=payload.category,
            status=payload.status,
            pagination=pagination,
        )
    )
