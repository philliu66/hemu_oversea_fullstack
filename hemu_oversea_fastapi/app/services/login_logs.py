from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import Pagination
from app.core.security import Audience
from app.models.user import User
from app.models.user_login_log import UserLoginLog
from app.schemas.common import PageData
from app.schemas.logs import LoginLogPublic, LoginLogStatItem


def open_session(
    db: Session,
    *,
    user: User,
    audience: Audience,
    refresh_jti: str,
    ip: str | None = None,
    user_agent: str | None = None,
) -> UserLoginLog:
    now = datetime.now(timezone.utc)
    row = UserLoginLog(
        user_id=user.id,
        username=user.username,
        audience=audience,
        login_at=now,
        logout_at=None,
        logout_reason=None,
        last_seen_at=now,
        ip=ip,
        user_agent=_trim_user_agent(user_agent),
        refresh_jti=refresh_jti,
    )
    db.add(row)
    return row


def touch_session(
    db: Session,
    *,
    old_jti: str,
    new_jti: str,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    row = db.scalar(
        select(UserLoginLog).where(
            UserLoginLog.refresh_jti == old_jti,
            UserLoginLog.logout_at.is_(None),
        )
    )
    if row is None:
        return
    now = datetime.now(timezone.utc)
    row.last_seen_at = now
    row.refresh_jti = new_jti
    if ip is not None:
        row.ip = ip
    if user_agent is not None:
        row.user_agent = _trim_user_agent(user_agent)


def close_by_jti(
    db: Session,
    *,
    refresh_jti: str,
    reason: str,
) -> None:
    row = db.scalar(
        select(UserLoginLog).where(
            UserLoginLog.refresh_jti == refresh_jti,
            UserLoginLog.logout_at.is_(None),
        )
    )
    if row is None:
        return
    now = datetime.now(timezone.utc)
    row.logout_at = now
    row.last_seen_at = now
    row.logout_reason = reason


def close_open_sessions(
    db: Session,
    *,
    user_id: int,
    reason: str,
    audience: Audience | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    stmt = select(UserLoginLog).where(
        UserLoginLog.user_id == user_id,
        UserLoginLog.logout_at.is_(None),
    )
    if audience is not None:
        stmt = stmt.where(UserLoginLog.audience == audience)
    rows = db.scalars(stmt).all()
    for row in rows:
        row.logout_at = now
        row.last_seen_at = now
        row.logout_reason = reason


def list_login_logs(
    db: Session,
    *,
    user_id: int | None,
    username: str | None,
    audience: str | None,
    ip: str | None,
    login_at_from: datetime | None,
    login_at_to: datetime | None,
    pagination: Pagination,
) -> PageData[LoginLogPublic]:
    filters = _list_filters(
        user_id=user_id,
        username=username,
        audience=audience,
        ip=ip,
        login_at_from=login_at_from,
        login_at_to=login_at_to,
    )
    count_stmt = select(func.count()).select_from(UserLoginLog)
    list_stmt = select(UserLoginLog)
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(
        list_stmt.order_by(UserLoginLog.login_at.desc(), UserLoginLog.id.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()
    return PageData(
        items=[_to_public(row) for row in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def stats_login_logs(
    db: Session,
    *,
    grain: str,
    audience: str | None,
    login_at_from: datetime | None,
    login_at_to: datetime | None,
) -> list[LoginLogStatItem]:
    trunc = func.date_trunc(grain, UserLoginLog.login_at).label("bucket")
    filters = _list_filters(
        user_id=None,
        username=None,
        audience=audience,
        ip=None,
        login_at_from=login_at_from,
        login_at_to=login_at_to,
    )
    stats_stmt = select(
        trunc,
        func.count().label("login_count"),
        func.count(func.distinct(UserLoginLog.user_id)).label("unique_user_count"),
    )
    if filters:
        stats_stmt = stats_stmt.where(*filters)
    rows = db.execute(
        stats_stmt.group_by(trunc).order_by(trunc.asc())
    ).all()
    return [
        LoginLogStatItem(
            bucket=row.bucket,
            login_count=row.login_count,
            unique_user_count=row.unique_user_count,
        )
        for row in rows
    ]


def _list_filters(
    *,
    user_id: int | None,
    username: str | None,
    audience: str | None,
    ip: str | None,
    login_at_from: datetime | None,
    login_at_to: datetime | None,
) -> list:
    filters: list = []
    if user_id is not None:
        filters.append(UserLoginLog.user_id == user_id)
    if username and username.strip():
        filters.append(UserLoginLog.username.ilike(f"%{username.strip()}%"))
    if audience:
        filters.append(UserLoginLog.audience == audience)
    if ip and ip.strip():
        filters.append(UserLoginLog.ip == ip.strip())
    if login_at_from is not None:
        filters.append(UserLoginLog.login_at >= login_at_from)
    if login_at_to is not None:
        filters.append(UserLoginLog.login_at <= login_at_to)
    return filters


def _to_public(row: UserLoginLog) -> LoginLogPublic:
    end_at = row.logout_at or row.last_seen_at
    login_at = _as_utc(row.login_at)
    end_at_utc = _as_utc(end_at)
    online_seconds = max(0, int((end_at_utc - login_at).total_seconds()))
    return LoginLogPublic(
        id=row.id,
        user_id=row.user_id,
        username=row.username,
        audience=row.audience,
        login_at=row.login_at,
        logout_at=row.logout_at,
        logout_reason=row.logout_reason,
        last_seen_at=row.last_seen_at,
        online_seconds=online_seconds,
        ip=row.ip,
        user_agent=row.user_agent,
        refresh_jti=row.refresh_jti,
        created_at=row.created_at,
    )


def _trim_user_agent(user_agent: str | None) -> str | None:
    if user_agent is None:
        return None
    return user_agent[:255]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
