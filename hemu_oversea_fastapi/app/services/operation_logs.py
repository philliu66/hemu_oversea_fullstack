from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.deps import Pagination
from app.models.supplier import Supplier
from app.models.user import User
from app.models.user_operation_log import UserOperationLog
from app.schemas.common import PageData
from app.schemas.logs import OperationLogPublic
from app.services.supplier_scope import log_supplier_scope_filters

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
    actor: User,
    keyword: str | None,
    supplier_id: int | None,
    actor_user_id: int | None,
    action: str | None,
    resource_type: str | None,
    resource_id: str | None,
    created_at_from,
    created_at_to,
    pagination: Pagination,
) -> PageData[OperationLogPublic]:
    filters: list = []
    filters.extend(
        log_supplier_scope_filters(
            db,
            actor,
            supplier_id,
            UserOperationLog.supplier_id,
        )
    )
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
    keyword_filter = _keyword_filter(keyword)
    if keyword_filter is not None:
        filters.append(keyword_filter)

    count_stmt = (
        select(func.count(UserOperationLog.id))
        .select_from(UserOperationLog)
        .outerjoin(User, User.id == UserOperationLog.actor_user_id)
    )
    list_stmt = select(UserOperationLog, User).outerjoin(
        User,
        User.id == UserOperationLog.actor_user_id,
    )
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)
    total = db.scalar(count_stmt) or 0
    pairs = db.execute(
        list_stmt.order_by(
            UserOperationLog.created_at.desc(),
            UserOperationLog.id.desc(),
        )
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()
    supplier_names = _load_supplier_names(
        db,
        {row.supplier_id for row, _user in pairs if row.supplier_id is not None},
    )
    return PageData(
        items=[
            _to_public(row, user=user, supplier_names=supplier_names)
            for row, user in pairs
        ],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def _keyword_filter(keyword: str | None):
    text = (keyword or "").strip()
    if not text:
        return None
    pattern = f"%{text}%"
    return or_(
        User.nickname.ilike(pattern),
        User.email.ilike(pattern),
        User.phone.ilike(pattern),
        UserOperationLog.summary.ilike(pattern),
        UserOperationLog.action.ilike(pattern),
    )


def _load_supplier_names(db: Session, supplier_ids: set[int]) -> dict[int, str]:
    if not supplier_ids:
        return {}
    rows = db.execute(
        select(Supplier.id, Supplier.name).where(Supplier.id.in_(supplier_ids))
    ).all()
    return {row.id: row.name for row in rows}


def _to_public(
    row: UserOperationLog,
    *,
    user: User | None,
    supplier_names: dict[int, str],
) -> OperationLogPublic:
    return OperationLogPublic(
        id=row.id,
        actor_user_id=row.actor_user_id,
        actor_username=row.actor_username,
        nickname=user.nickname if user is not None else None,
        email=user.email if user is not None else None,
        phone=user.phone if user is not None else None,
        actor_role=row.actor_role,
        org_type=row.org_type,
        supplier_id=row.supplier_id,
        supplier_name=(
            supplier_names.get(row.supplier_id) if row.supplier_id is not None else None
        ),
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
