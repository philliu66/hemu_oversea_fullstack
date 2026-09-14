"""敦煌网开放平台 OAuth2（Authorization Code + Refresh Token）。"""

from __future__ import annotations

import logging
import secrets
import threading
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import bad_request, not_found
from app.core.store_types import StoreType
from app.models.store import Store
from app.services.dhgate.response import raise_reauth_required

logger = logging.getLogger("app")

# 敦煌文档：Refresh Token 有效期约 30 天
_REFRESH_TOKEN_DEFAULT_DAYS = 30

_store_locks: dict[int, threading.Lock] = {}
_locks_guard = threading.Lock()


def _get_store_lock(store_id: int) -> threading.Lock:
    with _locks_guard:
        lock = _store_locks.get(store_id)
        if lock is None:
            lock = threading.Lock()
            _store_locks[store_id] = lock
        return lock


def ensure_dhgate_config() -> None:
    if not settings.DHGATE_APP_KEY or not settings.DHGATE_APP_SECRET:
        raise bad_request("未配置敦煌开放平台 App Key / App Secret")
    if not settings.DHGATE_REDIRECT_URI:
        raise bad_request("未配置敦煌 OAuth 回调地址 DHGATE_REDIRECT_URI")


def parse_expires_at(expires_in: int | str | None, *, now: datetime) -> datetime:
    """敦煌 expires_in 单位为毫秒；若数值较小则按秒处理。"""
    if expires_in is None:
        return now + timedelta(days=1)
    value = int(expires_in)
    if value > 10_000_000:
        return now + timedelta(milliseconds=value)
    return now + timedelta(seconds=value)


def _normalize_expires_at(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _request_token(payload: dict[str, str]) -> dict:
    ensure_dhgate_config()
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(settings.DHGATE_TOKEN_URL, data=payload)
    except httpx.HTTPError as exc:
        logger.exception("敦煌 token 接口网络失败")
        raise bad_request(f"请求敦煌 token 接口失败: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        logger.error(
            "敦煌 token 响应非 JSON status=%s body=%s",
            response.status_code,
            response.text,
        )
        raise bad_request("敦煌 token 接口返回异常") from exc

    status = data.get("status")
    status_code = status.get("code") if isinstance(status, dict) else None
    has_biz_error = status_code not in (None, "00000000", 0, "0")
    if response.status_code >= 400 or data.get("error") or has_biz_error:
        err = data.get("error_description") or data.get("error") or data
        if isinstance(status, dict) and status.get("message"):
            err = status["message"]
        logger.warning(
            "敦煌 token 接口失败 status=%s data=%s",
            response.status_code,
            data,
        )
        raise bad_request(f"敦煌 token 请求失败: {err}")

    if not data.get("access_token"):
        raise bad_request("敦煌未返回 access_token")
    return data


def apply_token_response(store: Store, token_data: dict, *, now: datetime) -> None:
    store.access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    if refresh_token:
        store.refresh_token = refresh_token
    store.access_token_expires_at = parse_expires_at(
        token_data.get("expires_in"),
        now=now,
    )
    store.refresh_token_expires_at = now + timedelta(days=_REFRESH_TOKEN_DEFAULT_DAYS)
    store.oauth_scope = token_data.get("scope") or settings.DHGATE_OAUTH_SCOPE
    store.oauth_authorized_at = now


def refresh_access_token(db: Session, store: Store) -> Store:
    """使用 refresh_token 刷新 access_token 并落库。"""
    if not store.refresh_token:
        raise raise_reauth_required("店铺缺少 refresh_token，请重新授权")

    refresh_expires = _normalize_expires_at(store.refresh_token_expires_at)
    now = datetime.now(timezone.utc)
    if refresh_expires is not None and refresh_expires < now:
        raise raise_reauth_required("敦煌 refresh_token 已过期，请重新授权")

    lock = _get_store_lock(store.id)
    with lock:
        db.refresh(store)
        if not store.refresh_token:
            raise raise_reauth_required("店铺缺少 refresh_token，请重新授权")

        token_data = _request_token(
            {
                "grant_type": "refresh_token",
                "refresh_token": store.refresh_token,
                "client_id": settings.DHGATE_APP_KEY,
                "client_secret": settings.DHGATE_APP_SECRET,
                "scope": settings.DHGATE_OAUTH_SCOPE,
            }
        )
        apply_token_response(store, token_data, now=now)
        db.commit()
        db.refresh(store)
        logger.info("敦煌 refresh token 成功 store_id=%s", store.id)
        return store


def ensure_valid_access_token(db: Session, store: Store) -> str:
    """返回可用的 access_token；临近过期时主动刷新。"""
    if not store.access_token:
        raise raise_reauth_required("店铺未授权敦煌，请先完成授权")

    refresh_expires = _normalize_expires_at(store.refresh_token_expires_at)
    now = datetime.now(timezone.utc)
    if refresh_expires is not None and refresh_expires < now:
        raise raise_reauth_required("敦煌 refresh_token 已过期，请重新授权")

    access_expires = _normalize_expires_at(store.access_token_expires_at)
    buffer = timedelta(minutes=settings.DHGATE_TOKEN_REFRESH_BUFFER_MINUTES)
    if access_expires is None or access_expires <= now + buffer:
        store = refresh_access_token(db, store)
    return store.access_token  # type: ignore[return-value]


def create_authorize_url_for_store(
    db: Session,
    *,
    store: Store,
    actor_id: int,
) -> str:
    """为已校验过的敦煌店铺生成授权页 URL，并把 state 落到店铺上（state 最长 20）。"""
    ensure_dhgate_config()
    if store.store_type != StoreType.DHGATE.value:
        raise bad_request("当前店铺不是敦煌类型，无法走敦煌授权")

    state = secrets.token_hex(8)  # 16 字符
    now = datetime.now(timezone.utc)
    store.oauth_pending_state = state
    store.oauth_pending_expires_at = now + timedelta(
        minutes=settings.DHGATE_OAUTH_STATE_TTL_MINUTES
    )
    store.updated_by = actor_id
    db.commit()

    query = urlencode(
        {
            "client_id": settings.DHGATE_APP_KEY,
            "response_type": "code",
            "redirect_uri": settings.DHGATE_REDIRECT_URI,
            "scope": settings.DHGATE_OAUTH_SCOPE,
            "state": state,
        }
    )
    return f"{settings.DHGATE_AUTHORIZE_URL}?{query}"


def create_authorize_url(db: Session, *, store_id: int, actor_id: int) -> str:
    """兼容旧调用：按店铺 ID 生成敦煌授权链接。"""
    store = db.get(Store, store_id)
    if store is None or store.is_deleted:
        raise not_found("店铺不存在")
    return create_authorize_url_for_store(db, store=store, actor_id=actor_id)


def _find_store_by_state(db: Session, state: str) -> Store:
    if not state or len(state) > 20:
        raise bad_request("无效的 state")

    store = db.scalar(
        select(Store).where(
            Store.oauth_pending_state == state,
            Store.deleted_at.is_(None),
        )
    )
    if store is None:
        raise bad_request("授权 state 无效或已失效，请重新发起授权")

    now = datetime.now(timezone.utc)
    expires_at = store.oauth_pending_expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at is None or expires_at < now:
        store.oauth_pending_state = None
        store.oauth_pending_expires_at = None
        db.commit()
        raise bad_request("授权 state 已过期，请重新发起授权")
    return store


def _exchange_code_for_token(code: str) -> dict:
    return _request_token(
        {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.DHGATE_APP_KEY,
            "client_secret": settings.DHGATE_APP_SECRET,
            "redirect_uri": settings.DHGATE_REDIRECT_URI,
            "scope": settings.DHGATE_OAUTH_SCOPE,
        }
    )


def handle_oauth_callback(
    db: Session,
    *,
    code: str | None,
    state: str | None,
) -> Store:
    """校验 state、用 code 换 token，并写入店铺。"""
    if not code:
        raise bad_request("缺少授权码 code")
    if not state:
        raise bad_request("缺少 state")

    store = _find_store_by_state(db, state)
    token_data = _exchange_code_for_token(code)

    now = datetime.now(timezone.utc)
    apply_token_response(store, token_data, now=now)
    store.oauth_pending_state = None
    store.oauth_pending_expires_at = None
    db.commit()
    db.refresh(store)
    logger.info("敦煌 OAuth 授权成功 store_id=%s", store.id)
    return store


def build_frontend_redirect(
    *,
    ok: bool,
    store_id: int | None = None,
    message: str = "",
) -> str:
    """
    跳转前端回调页，拼接友好展示参数：
    - status=success | fail
    - msg=授权成功 / 失败原因
    - store_id（可选）
    """
    base = settings.DHGATE_FRONTEND_REDIRECT_URI.rstrip("/")
    if ok:
        msg = (message or "授权成功").strip()[:200]
    else:
        msg = (message or "授权失败").strip()[:200]

    params: dict[str, str] = {
        "status": "success" if ok else "fail",
        "msg": msg,
    }
    if store_id is not None:
        params["store_id"] = str(store_id)
    return f"{base}?{urlencode(params)}"
