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


@router.post("/login/list", response_model=ApiResponse[PageData[LoginLogPublic]])
def list_login_logs(
    payload: LoginLogList,
    _current_user: User = Depends(require_perm("logs.view")),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[LoginLogPublic]]:
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        login_logs.list_login_logs(
            db,
            user_id=payload.user_id,
            username=payload.username,
            audience=payload.audience,
            ip=payload.ip,
            login_at_from=payload.login_at_from,
            login_at_to=payload.login_at_to,
            pagination=pagination,
        )
    )


@router.post("/login/stats", response_model=ApiResponse[list[LoginLogStatItem]])
def stats_login_logs(
    payload: LoginLogStats,
    _current_user: User = Depends(require_perm("logs.view")),
    db: Session = Depends(get_db),
) -> ApiResponse[list[LoginLogStatItem]]:
    return success(
        login_logs.stats_login_logs(
            db,
            grain=payload.grain,
            audience=payload.audience,
            login_at_from=payload.login_at_from,
            login_at_to=payload.login_at_to,
        )
    )


@router.post(
    "/operation/list",
    response_model=ApiResponse[PageData[OperationLogPublic]],
)
def list_operation_logs(
    payload: OperationLogList,
    _current_user: User = Depends(require_perm("logs.view")),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[OperationLogPublic]]:
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        operation_logs.list_operation_logs(
            db,
            actor_user_id=payload.actor_user_id,
            action=payload.action,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            created_at_from=payload.created_at_from,
            created_at_to=payload.created_at_to,
            pagination=pagination,
        )
    )
