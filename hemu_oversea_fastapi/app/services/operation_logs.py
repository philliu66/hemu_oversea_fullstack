from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import Pagination
from app.models.user import User
from app.models.user_operation_log import UserOperationLog
from app.schemas.common import PageData
from app.schemas.logs import OperationLogPublic

ACTION_MISSION_CREATE = "mission.create"


def record_operation(
    db: Session,
    *,
    actor: User,
    action: str,
    resource_type: str,
    resource_id: str,
    summary: str,
    detail: dict[str, Any] | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    status: str = "success",
) -> UserOperationLog:
    """Append an operation log row; caller owns the transaction (no commit)."""
    row = UserOperationLog(
        actor_user_id=actor.id,
        actor_username=actor.username,
        actor_role=actor.role,
        org_type=actor.org_type,
        supplier_id=actor.supplier_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        summary=summary[:512],
        detail=detail,
        ip=ip,
        user_agent=_trim_user_agent(user_agent),
        status=status,
    )
    db.add(row)
    return row


def list_operation_logs(
    db: Session,
    *,
    actor_user_id: int | None,
    action: str | None,
    resource_type: str | None,
    resource_id: str | None,
    created_at_from,
    created_at_to,
    pagination: Pagination,
) -> PageData[OperationLogPublic]:
    filters: list = []
    if actor_user_id is not None:
        filters.append(UserOperationLog.actor_user_id == actor_user_id)
    if action and action.strip():
        filters.append(UserOperationLog.action == action.strip())
    if resource_type and resource_type.strip():
        filters.append(UserOperationLog.resource_type == resource_type.strip())
    if resource_id and resource_id.strip():
        filters.append(UserOperationLog.resource_id == resource_id.strip())
    if created_at_from is not None:
        filters.append(UserOperationLog.created_at >= created_at_from)
    if created_at_to is not None:
        filters.append(UserOperationLog.created_at <= created_at_to)

    count_stmt = select(func.count()).select_from(UserOperationLog)
    list_stmt = select(UserOperationLog)
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(
        list_stmt.order_by(
            UserOperationLog.created_at.desc(),
            UserOperationLog.id.desc(),
        )
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()
    return PageData(
        items=[_to_public(row) for row in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def _to_public(row: UserOperationLog) -> OperationLogPublic:
    return OperationLogPublic(
        id=row.id,
        actor_user_id=row.actor_user_id,
        actor_username=row.actor_username,
        actor_role=row.actor_role,
        org_type=row.org_type,
        supplier_id=row.supplier_id,
        action=row.action,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        summary=row.summary,
        detail=row.detail,
        ip=row.ip,
        user_agent=row.user_agent,
        status=row.status,
        created_at=row.created_at,
    )


def _trim_user_agent(user_agent: str | None) -> str | None:
    if user_agent is None:
        return None
    return user_agent[:255]
