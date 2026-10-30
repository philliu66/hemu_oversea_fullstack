from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import bad_request, too_many_requests, unauthorized
from app.core.roles import ADMIN_PORTAL_ROLES, APP_PORTAL_ROLES
from app.core.security import (
    Audience,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.login_attempt import LoginAttempt
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.schemas.auth import AuthLoginResponse, TokenPair
from app.schemas.user import UserPublic
from app.services import login_logs
from app.services import permissions as perm_service

APP_ROLES: frozenset[str] = frozenset(role.value for role in APP_PORTAL_ROLES)
ADMIN_ROLES: frozenset[str] = frozenset(role.value for role in ADMIN_PORTAL_ROLES)

_AUDIENCE_ROLES: dict[Audience, frozenset[str]] = {
    "app": APP_ROLES,
    "admin": ADMIN_ROLES,
}

_WRONG_CREDENTIALS = "用户名或密码错误"


def issue_tokens(
    db: Session,
    user: User,
    audience: Audience,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[TokenPair, str]:
    refresh = create_refresh_token(str(user.id), audience)
    db.add(
        RefreshSession(
            user_id=user.id,
            jti=refresh.jti,
            audience=audience,
            expires_at=refresh.expires_at,
            ip=ip,
            user_agent=_trim_user_agent(user_agent),
        )
    )
    tokens = TokenPair(
        access_token=create_access_token(str(user.id), audience),
        refresh_token=refresh.token,
    )
    return tokens, refresh.jti


def login_for_audience(
    db: Session,
    *,
    username: str,
    password: str,
    audience: Audience,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AuthLoginResponse:
    _assert_not_locked(db, username, audience)
    user = db.scalar(
        select(User).where(User.username == username, User.deleted_at.is_(None))
    )
    if user is None or not verify_password(password, user.hashed_password):
        _record_failure(db, username, audience, ip)
        db.commit()
        raise unauthorized(_WRONG_CREDENTIALS)
    if not user.is_active:
        raise unauthorized("账号已停用")
    if user.role not in _AUDIENCE_ROLES[audience]:
        _record_failure(db, username, audience, ip)
        db.commit()
        raise unauthorized(_WRONG_CREDENTIALS)

    _clear_failures(db, username, audience)
    if audience == "admin":
        _revoke_all(db, user.id, audience, login_reason="kicked")
    tokens, refresh_jti = issue_tokens(
        db, user, audience, ip=ip, user_agent=user_agent
    )
    login_logs.open_session(
        db,
        user=user,
        audience=audience,
        refresh_jti=refresh_jti,
        ip=ip,
        user_agent=user_agent,
    )
    db.commit()
    return AuthLoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        user=UserPublic(**perm_service.to_user_public_dict(user, db)),
    )


def refresh_for_audience(
    db: Session,
    *,
    refresh_token: str,
    audience: Audience,
    ip: str | None = None,
    user_agent: str | None = None,
) -> TokenPair:
    try:
        payload = decode_token(refresh_token, "refresh", audience)
        user_id = int(payload.subject)
    except (TokenError, ValueError):
        raise unauthorized()

    session = db.scalar(select(RefreshSession).where(RefreshSession.jti == payload.jti))
    if session is None or session.user_id != user_id or session.audience != audience:
        raise unauthorized()

    now = datetime.now(timezone.utc)
    if session.revoked_at is not None:
        _revoke_all(db, user_id, audience, login_reason="kicked")
        db.commit()
        raise unauthorized()
    if _as_utc(session.expires_at) <= now:
        raise unauthorized()

    user = db.get(User, user_id)
    if user is None or user.is_deleted or not user.is_active:
        raise unauthorized()
    if user.role not in _AUDIENCE_ROLES[audience]:
        raise unauthorized()

    login_logs.note_activity(
        db,
        user=user,
        audience=audience,
        ip=ip,
        user_agent=user_agent,
        refresh_jti=payload.jti,
    )
    session.revoked_at = now
    tokens, new_jti = issue_tokens(db, user, audience, ip=ip, user_agent=user_agent)
    login_logs.rotate_open_jti(
        db,
        user_id=user.id,
        audience=audience,
        new_jti=new_jti,
    )
    db.commit()
    return tokens


def logout_for_audience(
    db: Session,
    *,
    refresh_token: str,
    audience: Audience,
) -> None:
    try:
        payload = decode_token(refresh_token, "refresh", audience)
    except TokenError:
        raise unauthorized()

    session = db.scalar(select(RefreshSession).where(RefreshSession.jti == payload.jti))
    if session is not None and session.audience == audience and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
    login_logs.close_by_jti(
        db,
        refresh_jti=payload.jti,
        reason="logout",
    )
    db.commit()


def logout_all_for_audience(db: Session, *, user_id: int, audience: Audience) -> None:
    _revoke_all(db, user_id, audience, login_reason="logout_all")
    db.commit()


def revoke_all_sessions(db: Session, user_id: int) -> None:
    """作废该用户所有端的 refresh，不 commit。"""
    _revoke_all(db, user_id, login_reason="kicked")


def change_password(
    db: Session,
    user: User,
    *,
    old_password: str,
    new_password: str,
) -> None:
    """改密：old/new 均为明文，后端 Argon2 校验并入库。"""
    if not verify_password(old_password, user.hashed_password):
        raise bad_request("原密码错误")
    if old_password == new_password:
        raise bad_request("新密码不能与原密码相同")
    user.hashed_password = hash_password(new_password)
    _revoke_all(db, user.id, login_reason="password_change")
    db.commit()


def _assert_not_locked(db: Session, username: str, audience: Audience) -> None:
    window_start = datetime.now(timezone.utc) - timedelta(minutes=settings.LOGIN_WINDOW_MINUTES)
    db.execute(
        delete(LoginAttempt).where(
            LoginAttempt.username == username,
            LoginAttempt.audience == audience,
            LoginAttempt.created_at < window_start,
        )
    )
    count = db.scalar(
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            LoginAttempt.username == username,
            LoginAttempt.audience == audience,
            LoginAttempt.created_at >= window_start,
        )
    ) or 0
    if count >= settings.LOGIN_MAX_ATTEMPTS:
        raise too_many_requests(retry_after=settings.LOGIN_WINDOW_MINUTES * 60)


def _record_failure(
    db: Session,
    username: str,
    audience: Audience,
    ip: str | None,
) -> None:
    db.add(LoginAttempt(username=username, audience=audience, ip=ip))


def _clear_failures(db: Session, username: str, audience: Audience) -> None:
    db.execute(
        delete(LoginAttempt).where(
            LoginAttempt.username == username,
            LoginAttempt.audience == audience,
        )
    )


def _revoke_all(
    db: Session,
    user_id: int,
    audience: Audience | None = None,
    *,
    login_reason: str = "kicked",
) -> None:
    now = datetime.now(timezone.utc)
    stmt = (
        update(RefreshSession)
        .where(
            RefreshSession.user_id == user_id,
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    if audience is not None:
        stmt = stmt.where(RefreshSession.audience == audience)
    db.execute(stmt)
    login_logs.close_open_sessions(
        db,
        user_id=user_id,
        reason=login_reason,
        audience=audience,
    )


def _trim_user_agent(user_agent: str | None) -> str | None:
    if user_agent is None:
        return None
    return user_agent[:255]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
