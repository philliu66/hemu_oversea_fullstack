from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Pagination, require_admin_user, require_perm
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.logs import (
    LoginActivitySummary,
    LoginActivitySummaryQuery,
    LoginActivityTimeline,
    LoginActivityTimelineQuery,
    LoginActivityUserOption,
    LoginActivityUserQuery,
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
    分页查询一段连续活跃。

    - 权限码 `system.logs`
    - `keyword` 匹配用户昵称、邮箱、手机号
    - `login_at_from` / `login_at_to` 按本段开始时间筛选
    - 供应商账号只看本供应商；平台账号可传 `supplier_id` 筛选，不传则按可见范围
    - `activity_status`：`active` 活跃中，`idle` 非活跃但本段尚未结束，`ended` 已结束
    - 已结束时 `online_seconds` 算到 `active_until`；未结束时算到 `last_seen_at`
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
    "/login/activity/users",
    response_model=ApiResponse[list[LoginActivityUserOption]],
    summary="登录活跃可选用户",
)
def list_login_activity_users(
    payload: LoginActivityUserQuery,
    current_user: User = Depends(require_perm("system.logs")),
    db: Session = Depends(get_db),
) -> ApiResponse[list[LoginActivityUserOption]]:
    """按供应商返回可查看活跃情况的供应商用户。平台必须传 supplier_id。"""
    return success(
        login_logs.list_activity_users(
            db,
            actor=current_user,
            supplier_id=payload.supplier_id,
        )
    )


@router.post(
    "/login/activity/summary",
    response_model=ApiResponse[LoginActivitySummary],
    summary="登录活跃时长汇总",
)
def summarize_login_activity(
    payload: LoginActivitySummaryQuery,
    current_user: User = Depends(require_perm("system.logs")),
    db: Session = Depends(get_db),
) -> ApiResponse[LoginActivitySummary]:
    """
    按上海时区的自然日汇总某个用户在起止时间内的活跃分钟。

    不足一天的部分只计入与时间范围重叠的分钟。没有记录的日期返回 0。
    """
    return success(
        login_logs.summarize_login_activity(
            db,
            actor=current_user,
            user_id=payload.user_id,
            supplier_id=payload.supplier_id,
            time_from=payload.time_from,
            time_to=payload.time_to,
        )
    )


@router.post(
    "/login/activity/timeline",
    response_model=ApiResponse[LoginActivityTimeline],
    summary="登录活跃时段",
)
def timeline_login_activity(
    payload: LoginActivityTimelineQuery,
    current_user: User = Depends(require_perm("system.logs")),
    db: Session = Depends(get_db),
) -> ApiResponse[LoginActivityTimeline]:
    """返回某个用户在起止时间内的活跃区间，已裁到该时间范围。"""
    return success(
        login_logs.timeline_login_activity(
            db,
            actor=current_user,
            user_id=payload.user_id,
            supplier_id=payload.supplier_id,
            time_from=payload.time_from,
            time_to=payload.time_to,
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
