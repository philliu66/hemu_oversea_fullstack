from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Pagination, require_admin_user, require_perm
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.logs import (
    LoginLogList,
    LoginLogPublic,
    LoginLogStatItem,
    LoginLogStats,
    OperationLogList,
    OperationLogPublic,
)
from app.services import login_logs, operation_logs

router = APIRouter(
    prefix="/logs",
    tags=["admin:logs"],
    dependencies=[Depends(require_admin_user)],
)


@router.post(
    "/login/list",
    response_model=ApiResponse[PageData[LoginLogPublic]],
    summary="登录日志列表",
)
def list_login_logs(
    payload: LoginLogList,
    current_user: User = Depends(require_perm("system.logs")),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[LoginLogPublic]]:
    """
    分页查询登录、登出和停留时间。

    - 权限码 `system.logs`
    - `keyword` 匹配用户昵称、邮箱、手机号
    - `login_at_from` / `login_at_to` 按登录时间筛选
    - 供应商账号只看本供应商；平台账号可传 `supplier_id` 筛选，不传则按可见范围
    - 未登出时 `logout_at` 为空，`online_seconds` 估算到最近活跃
    """
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        login_logs.list_login_logs(
            db,
            actor=current_user,
            keyword=payload.keyword,
            supplier_id=payload.supplier_id,
            user_id=payload.user_id,
            username=payload.username,
            audience=payload.audience,
            ip=payload.ip,
            login_at_from=payload.login_at_from,
            login_at_to=payload.login_at_to,
            pagination=pagination,
        )
    )


@router.post(
    "/login/stats",
    response_model=ApiResponse[list[LoginLogStatItem]],
    summary="登录日志统计",
)
def stats_login_logs(
    payload: LoginLogStats,
    current_user: User = Depends(require_perm("system.logs")),
    db: Session = Depends(get_db),
) -> ApiResponse[list[LoginLogStatItem]]:
    """
    按天、周或月统计登录次数。

    - 权限码 `system.logs`
    - 供应商范围与登录日志列表相同
    """
    return success(
        login_logs.stats_login_logs(
            db,
            actor=current_user,
            supplier_id=payload.supplier_id,
            grain=payload.grain,
            audience=payload.audience,
            login_at_from=payload.login_at_from,
            login_at_to=payload.login_at_to,
        )
    )


@router.post(
    "/operation/list",
    response_model=ApiResponse[PageData[OperationLogPublic]],
    summary="操作日志列表",
)
def list_operation_logs(
    payload: OperationLogList,
    current_user: User = Depends(require_perm("system.logs")),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[OperationLogPublic]]:
    """
    分页查询用户关键操作。

    - 权限码 `system.logs`
    - `keyword` 匹配用户昵称、邮箱、手机号，以及操作名称（`summary` / `action`）
    - `created_at_from` / `created_at_to` 按操作时间筛选
    - 供应商账号只看本供应商；平台账号可传 `supplier_id` 筛选，不传则按可见范围
    """
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        operation_logs.list_operation_logs(
            db,
            actor=current_user,
            keyword=payload.keyword,
            supplier_id=payload.supplier_id,
            actor_user_id=payload.actor_user_id,
            action=payload.action,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            created_at_from=payload.created_at_from,
            created_at_to=payload.created_at_to,
            pagination=pagination,
        )
    )
