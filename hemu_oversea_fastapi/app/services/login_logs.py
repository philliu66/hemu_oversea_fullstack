from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import Pagination
from app.core.errors import bad_request, forbidden
from app.core.roles import Role
from app.core.security import Audience
from app.models.refresh_session import RefreshSession
from app.models.supplier import Supplier
from app.models.user import User
from app.models.user_login_log import UserLoginLog
from app.schemas.common import PageData
from app.schemas.logs import (
    LoginActivityDay,
    LoginActivitySpan,
    LoginActivitySummary,
    LoginActivityTimeline,
    LoginActivityUserOption,
    LoginLogPublic,
    LoginLogStatItem,
)
from app.services.supplier_scope import (
    assert_supplier_accessible,
    is_platform_role,
    is_supplier_portal_role,
    log_supplier_scope_filters,
)

# 与管理端展示时区一致，按自然日切活跃时长
_ACTIVITY_ZONE = ZoneInfo("Asia/Shanghai")
_ACTIVITY_MAX_DAYS = 31
_SUPPLIER_USER_ROLES = frozenset(
    {Role.SUPPLIER_ADMIN.value, Role.SUPPLIER_STAFF.value}
)


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
        supplier_id=user.supplier_id,
        audience=audience,
        login_at=now,
        logout_at=None,
        logout_reason=None,
        last_seen_at=now,
        active_until=None,
        idle_minutes=None,
        ip=ip,
        user_agent=_trim_user_agent(user_agent),
        refresh_jti=refresh_jti,
    )
    db.add(row)
    return row


def note_activity(
    db: Session,
    *,
    user: User,
    audience: Audience,
    ip: str | None = None,
    user_agent: str | None = None,
    refresh_jti: str | None = None,
) -> bool:
    """按距上次活跃的间隔节流更新，或在超过空闲阈值时结束本段并新开。

    返回是否写入了数据库。调用方决定是否 commit。不覆盖已有 last_seen_at 以外的关闭语义。
    """
    now = datetime.now(timezone.utc)
    preview = _open_row(db, user_id=user.id, audience=audience, lock=False)
    if preview is not None:
        gap = now - _as_utc(preview.last_seen_at)
        if gap < min(_touch_delta(), _idle_delta()):
            return False
    row = _open_row(db, user_id=user.id, audience=audience, lock=True)
    if row is None:
        jti = refresh_jti or _live_refresh_jti(db, user.id, audience)
        if not jti:
            return False
        open_session(
            db,
            user=user,
            audience=audience,
            refresh_jti=jti,
            ip=ip,
            user_agent=user_agent,
        )
        return True

    gap = now - _as_utc(row.last_seen_at)
    if gap >= _idle_delta():
        _finish_row(row, now=now, reason="idle")
        open_session(
            db,
            user=user,
            audience=audience,
            refresh_jti=refresh_jti or row.refresh_jti,
            ip=ip if ip is not None else row.ip,
            user_agent=user_agent if user_agent is not None else row.user_agent,
        )
        return True
    if gap >= _touch_delta():
        row.last_seen_at = now
        if ip is not None:
            row.ip = ip
        if user_agent is not None:
            row.user_agent = _trim_user_agent(user_agent)
        return True
    return False


def rotate_open_jti(
    db: Session,
    *,
    user_id: int,
    audience: Audience,
    new_jti: str,
) -> None:
    """换票后把未结束行指到新的 refresh jti，不改 last_seen_at。"""
    row = _lock_open_row(db, user_id=user_id, audience=audience)
    if row is None:
        return
    row.refresh_jti = new_jti


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
    _finish_row(row, now=datetime.now(timezone.utc), reason=reason)


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
        _finish_row(row, now=now, reason=reason)


def list_login_logs(
    db: Session,
    *,
    actor: User,
    keyword: str | None,
    supplier_id: int | None,
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
    filters.extend(
        log_supplier_scope_filters(
            db,
            actor,
            supplier_id,
            UserLoginLog.supplier_id,
        )
    )
    keyword_filter = _keyword_filter(keyword)
    if keyword_filter is not None:
        filters.append(keyword_filter)

    count_stmt = (
        select(func.count(UserLoginLog.id))
        .select_from(UserLoginLog)
        .outerjoin(User, User.id == UserLoginLog.user_id)
    )
    list_stmt = select(UserLoginLog, User).outerjoin(
        User,
        User.id == UserLoginLog.user_id,
    )
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)
    total = db.scalar(count_stmt) or 0
    pairs = db.execute(
        list_stmt.order_by(UserLoginLog.login_at.desc(), UserLoginLog.id.desc())
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


def stats_login_logs(
    db: Session,
    *,
    actor: User,
    supplier_id: int | None,
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
    filters.extend(
        log_supplier_scope_filters(
            db,
            actor,
            supplier_id,
            UserLoginLog.supplier_id,
        )
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


def list_activity_users(
    db: Session,
    *,
    actor: User,
    supplier_id: int | None,
) -> list[LoginActivityUserOption]:
    supplier_id = _activity_supplier_id(db, actor, supplier_id)
    rows = db.scalars(
        select(User)
        .where(
            User.supplier_id == supplier_id,
            User.deleted_at.is_(None),
            User.role.in_(_SUPPLIER_USER_ROLES),
        )
        .order_by(User.nickname.asc(), User.id.asc())
    ).all()
    return [
        LoginActivityUserOption(
            id=row.id,
            username=row.username,
            nickname=row.nickname,
            email=row.email,
            phone=row.phone,
        )
        for row in rows
    ]


def summarize_login_activity(
    db: Session,
    *,
    actor: User,
    user_id: int,
    supplier_id: int | None,
    time_from: datetime,
    time_to: datetime,
) -> LoginActivitySummary:
    user = _activity_user(db, actor, user_id, supplier_id)
    window_start, window_end = _activity_window(time_from, time_to)
    rows = _activity_rows(db, user, window_start, window_end)
    now = datetime.now(timezone.utc)
    days: list[LoginActivityDay] = []
    for cursor in _dates_in_window(window_start, window_end):
        day_start, day_end = _day_bounds(cursor)
        slice_start = max(day_start, window_start)
        slice_end = min(day_end, window_end)
        minutes = 0
        for row in rows:
            minutes += _overlap_minutes(
                _segment_bounds(row, now),
                slice_start,
                slice_end,
            )
        days.append(LoginActivityDay(date=cursor, active_minutes=minutes))
    return LoginActivitySummary(
        user_id=user.id,
        nickname=user.nickname,
        username=user.username,
        time_from=window_start,
        time_to=window_end,
        total_minutes=sum(item.active_minutes for item in days),
        days=days,
    )


def timeline_login_activity(
    db: Session,
    *,
    actor: User,
    user_id: int,
    supplier_id: int | None,
    time_from: datetime,
    time_to: datetime,
) -> LoginActivityTimeline:
    user = _activity_user(db, actor, user_id, supplier_id)
    window_start, window_end = _activity_window(time_from, time_to)
    rows = _activity_rows(db, user, window_start, window_end)
    now = datetime.now(timezone.utc)
    spans: list[LoginActivitySpan] = []
    for row in rows:
        start, end = _segment_bounds(row, now)
        clipped_start = max(start, window_start)
        clipped_end = min(end, window_end)
        if clipped_end <= clipped_start:
            continue
        spans.append(
            LoginActivitySpan(
                start=clipped_start,
                end=clipped_end,
                active_minutes=_overlap_minutes((start, end), window_start, window_end),
                activity_status=_activity_status(row, now),
            )
        )
    spans.sort(key=lambda item: item.start)
    return LoginActivityTimeline(
        time_from=window_start,
        time_to=window_end,
        total_minutes=sum(item.active_minutes for item in spans),
        spans=spans,
    )


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


def _keyword_filter(keyword: str | None):
    text = (keyword or "").strip()
    if not text:
        return None
    pattern = f"%{text}%"
    return or_(
        User.nickname.ilike(pattern),
        User.email.ilike(pattern),
        User.phone.ilike(pattern),
    )


def _load_supplier_names(db: Session, supplier_ids: set[int]) -> dict[int, str]:
    if not supplier_ids:
        return {}
    rows = db.execute(
        select(Supplier.id, Supplier.name).where(Supplier.id.in_(supplier_ids))
    ).all()
    return {row.id: row.name for row in rows}


def _finish_row(row: UserLoginLog, *, now: datetime, reason: str) -> None:
    """结束一行。不改 last_seen_at。"""
    row.logout_at = now
    row.logout_reason = reason
    last_seen = _as_utc(row.last_seen_at)
    idle_deadline = last_seen + _idle_delta()
    if reason == "idle":
        row.active_until = idle_deadline
        row.idle_minutes = settings.LOGIN_LOG_IDLE_MINUTES
        return
    if reason == "kicked":
        row.active_until = min(now, idle_deadline)
        if now >= idle_deadline:
            row.idle_minutes = settings.LOGIN_LOG_IDLE_MINUTES
        return
    row.active_until = now


def _open_row(
    db: Session,
    *,
    user_id: int,
    audience: Audience,
    lock: bool,
) -> UserLoginLog | None:
    stmt = (
        select(UserLoginLog)
        .where(
            UserLoginLog.user_id == user_id,
            UserLoginLog.audience == audience,
            UserLoginLog.logout_at.is_(None),
        )
        .order_by(UserLoginLog.id.desc())
        .limit(1)
    )
    if lock:
        stmt = stmt.with_for_update()
    return db.scalar(stmt)


def _lock_open_row(
    db: Session,
    *,
    user_id: int,
    audience: Audience,
) -> UserLoginLog | None:
    return _open_row(db, user_id=user_id, audience=audience, lock=True)


def _live_refresh_jti(db: Session, user_id: int, audience: Audience) -> str | None:
    return db.scalar(
        select(RefreshSession.jti)
        .where(
            RefreshSession.user_id == user_id,
            RefreshSession.audience == audience,
            RefreshSession.revoked_at.is_(None),
        )
        .order_by(RefreshSession.id.desc())
        .limit(1)
    )


def _touch_delta() -> timedelta:
    return timedelta(minutes=max(settings.LOGIN_LOG_TOUCH_MINUTES, 0))


def _idle_delta() -> timedelta:
    return timedelta(minutes=max(settings.LOGIN_LOG_IDLE_MINUTES, 1))


def _activity_status(row: UserLoginLog, now: datetime) -> str:
    if row.logout_at is not None:
        return "ended"
    if now - _as_utc(row.last_seen_at) >= _idle_delta():
        return "idle"
    return "active"


def _to_public(
    row: UserLoginLog,
    *,
    user: User | None,
    supplier_names: dict[int, str],
) -> LoginLogPublic:
    now = datetime.now(timezone.utc)
    if row.active_until is not None:
        end_at = row.active_until
    elif row.logout_at is not None:
        end_at = row.logout_at
    else:
        end_at = row.last_seen_at
    login_at = _as_utc(row.login_at)
    online_seconds = max(0, int((_as_utc(end_at) - login_at).total_seconds()))
    return LoginLogPublic(
        id=row.id,
        user_id=row.user_id,
        username=row.username,
        nickname=user.nickname if user is not None else None,
        email=user.email if user is not None else None,
        phone=user.phone if user is not None else None,
        supplier_id=row.supplier_id,
        supplier_name=(
            supplier_names.get(row.supplier_id) if row.supplier_id is not None else None
        ),
        audience=row.audience,
        login_at=row.login_at,
        logout_at=row.logout_at,
        logout_reason=row.logout_reason,
        last_seen_at=row.last_seen_at,
        active_until=row.active_until,
        idle_minutes=row.idle_minutes,
        activity_status=_activity_status(row, now),
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


def _activity_supplier_id(db: Session, actor: User, supplier_id: int | None) -> int:
    if is_supplier_portal_role(actor.role):
        if actor.supplier_id is None:
            raise bad_request("当前账号未绑定供应商")
        return actor.supplier_id
    if is_platform_role(actor.role):
        if supplier_id is None:
            raise bad_request("请指定供应商")
        assert_supplier_accessible(db, actor, supplier_id)
        return supplier_id
    raise forbidden()


def _activity_user(
    db: Session,
    actor: User,
    user_id: int,
    supplier_id: int | None,
) -> User:
    supplier_id = _activity_supplier_id(db, actor, supplier_id)
    user = db.get(User, user_id)
    if user is None or user.is_deleted:
        raise bad_request("用户不存在")
    if user.supplier_id != supplier_id or user.role not in _SUPPLIER_USER_ROLES:
        raise forbidden("无权查看该用户的活跃情况")
    return user


def _activity_window(time_from: datetime, time_to: datetime) -> tuple[datetime, datetime]:
    start = _as_utc(time_from)
    end = _as_utc(time_to)
    if end <= start:
        raise bad_request("结束时间必须晚于开始时间")
    if end - start > timedelta(days=_ACTIVITY_MAX_DAYS):
        raise bad_request(f"查询跨度不能超过 {_ACTIVITY_MAX_DAYS} 天")
    return start, end


def _dates_in_window(start: datetime, end: datetime) -> list[date]:
    first = start.astimezone(_ACTIVITY_ZONE).date()
    last = (end - timedelta(microseconds=1)).astimezone(_ACTIVITY_ZONE).date()
    days: list[date] = []
    cursor = first
    while cursor <= last:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def _day_bounds(on_date: date) -> tuple[datetime, datetime]:
    start = datetime(on_date.year, on_date.month, on_date.day, tzinfo=_ACTIVITY_ZONE)
    return start.astimezone(timezone.utc), (start + timedelta(days=1)).astimezone(
        timezone.utc
    )


def _segment_bounds(row: UserLoginLog, now: datetime) -> tuple[datetime, datetime]:
    start = _as_utc(row.login_at)
    if row.active_until is not None:
        end = _as_utc(row.active_until)
    elif row.logout_at is not None:
        end = _as_utc(row.logout_at)
    else:
        last_seen = _as_utc(row.last_seen_at)
        idle_minutes = row.idle_minutes or settings.LOGIN_LOG_IDLE_MINUTES
        idle_deadline = last_seen + timedelta(minutes=max(idle_minutes, 1))
        end = last_seen if now < idle_deadline else idle_deadline
    if end < start:
        end = start
    return start, end


def _overlap_minutes(
    bounds: tuple[datetime, datetime],
    window_start: datetime,
    window_end: datetime,
) -> int:
    start = max(bounds[0], window_start)
    end = min(bounds[1], window_end)
    if end <= start:
        return 0
    return int(round((end - start).total_seconds() / 60))


def _activity_rows(
    db: Session,
    user: User,
    range_start: datetime,
    range_end: datetime,
) -> list[UserLoginLog]:
    return list(
        db.scalars(
            select(UserLoginLog)
            .where(
                UserLoginLog.user_id == user.id,
                UserLoginLog.supplier_id == user.supplier_id,
                UserLoginLog.login_at < range_end,
                or_(
                    UserLoginLog.active_until > range_start,
                    (UserLoginLog.active_until.is_(None))
                    & (UserLoginLog.logout_at > range_start),
                    (UserLoginLog.active_until.is_(None))
                    & (UserLoginLog.logout_at.is_(None)),
                ),
            )
            .order_by(UserLoginLog.login_at.asc(), UserLoginLog.id.asc())
        ).all()
    )
