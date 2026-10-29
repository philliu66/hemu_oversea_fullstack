"""TikTok Shop 卖家授权：授权链接、回调建档、按 open_id 刷新 token。"""

from __future__ import annotations

import logging
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.errors import AppError, bad_request
from app.core.store_types import StoreType
from app.models.store import Store
from app.models.store_tts import StoreTts, StoreTtsOauthPending
from app.services.dhgate.response import raise_reauth_required
from app.services.tiktok.client import fetch_authorized_shops, request_json

logger = logging.getLogger("app")

_SELLER_USER_TYPE = 0
_REFRESH_BUFFER_MINUTES = 5
_NAME_MAX = 100
_CODE_MAX = 100

_row_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


@dataclass(frozen=True)
class TiktokShopPayload:
    shop_id: str
    shop_code: str
    cipher: str
    name: str
    region: str | None
    seller_type: str | None


@dataclass(frozen=True)
class TiktokOauthResult:
    message: str
    store_id: int | None


def _lock_key(supplier_id: int, open_id: str) -> str:
    return f"{supplier_id}:{open_id}"


def _get_lock(key: str) -> threading.Lock:
    with _locks_guard:
        lock = _row_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _row_locks[key] = lock
        return lock


def ensure_tiktok_config() -> None:
    if not settings.TIKTOK_APP_KEY or not settings.TIKTOK_APP_SECRET:
        raise bad_request("未配置 TikTok Shop App Key / App Secret")
    if not settings.TIKTOK_SERVICE_ID:
        raise bad_request("未配置 TikTok Shop Service ID")


def _authorize_url(state: str) -> str:
    base = settings.TIKTOK_AUTHORIZE_URL.strip()
    query = urlencode(
        {
            "service_id": settings.TIKTOK_SERVICE_ID,
            "state": state,
        }
    )
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}{query}"


def _create_pending(db: Session, *, supplier_id: int, actor_id: int) -> str:
    ensure_tiktok_config()
    state = secrets.token_hex(8)
    now = datetime.now(timezone.utc)
    pending = StoreTtsOauthPending(
        supplier_id=supplier_id,
        state=state,
        expires_at=now
        + timedelta(minutes=settings.TIKTOK_OAUTH_STATE_TTL_MINUTES),
        created_by=actor_id,
    )
    db.add(pending)
    db.commit()
    return _authorize_url(state)


def create_authorize_url_for_supplier(
    db: Session,
    *,
    supplier_id: int,
    actor_id: int,
) -> str:
    """首次授权：此时还没有店铺行，state 写在 pending 表。"""
    return _create_pending(db, supplier_id=supplier_id, actor_id=actor_id)


def create_authorize_url_for_store(
    db: Session,
    *,
    store: Store,
    actor_id: int,
) -> str:
    """重新授权：用这家店所属供应商发起，回调仍按返回的店铺建档或更新。"""
    if store.store_type != StoreType.TIKTOK.value:
        raise bad_request("当前店铺不是 TikTok 类型，无法走 TikTok 授权")
    if store.supplier_id is None:
        raise bad_request("店铺未绑定供应商")
    return _create_pending(db, supplier_id=store.supplier_id, actor_id=actor_id)


def _auth_base() -> str:
    return settings.TIKTOK_AUTH_BASE_URL.rstrip("/")


def _token_params(**extra: str) -> dict[str, str]:
    return {
        "app_key": settings.TIKTOK_APP_KEY,
        "app_secret": settings.TIKTOK_APP_SECRET,
        **extra,
    }


def _exchange_code(code: str) -> dict:
    ensure_tiktok_config()
    body = request_json(
        f"{_auth_base()}/api/v2/token/get",
        params=_token_params(auth_code=code, grant_type="authorized_code"),
    )
    data = body.get("data")
    if not isinstance(data, dict) or not data.get("access_token"):
        raise bad_request("TikTok 未返回 access_token")
    return data


def _refresh_token(refresh_token: str) -> dict:
    ensure_tiktok_config()
    body = request_json(
        f"{_auth_base()}/api/v2/token/refresh",
        params=_token_params(refresh_token=refresh_token, grant_type="refresh_token"),
    )
    data = body.get("data")
    if not isinstance(data, dict) or not data.get("access_token"):
        raise bad_request("TikTok 未返回 access_token")
    return data


def _parse_expire(value: object, *, now: datetime) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if number >= 1_000_000_000_000:
        return datetime.fromtimestamp(number / 1000, tz=timezone.utc)
    if number >= 1_000_000_000:
        return datetime.fromtimestamp(number, tz=timezone.utc)
    if number < 0:
        return None
    return now + timedelta(seconds=number)


def _normalize_expires_at(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _format_scopes(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return ",".join(parts) or None
    text = str(value).strip()
    return text or None


def _require_seller(token_data: dict) -> None:
    raw = token_data.get("user_type")
    if raw is None or raw == "":
        return
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise bad_request(
            f"不支持的授权类型 user_type={raw}，请使用卖家账号授权"
        ) from None
    if value != _SELLER_USER_TYPE:
        raise bad_request(f"不支持的授权类型 user_type={value}，请使用卖家账号授权")


def _apply_token_fields(row: StoreTts, token_data: dict, *, now: datetime) -> None:
    row.access_token = str(token_data["access_token"])
    incoming_refresh = token_data.get("refresh_token")
    if isinstance(incoming_refresh, str) and incoming_refresh.strip():
        row.refresh_token = incoming_refresh.strip()
    row.access_token_expires_at = _parse_expire(
        token_data.get("access_token_expire_in"),
        now=now,
    )
    row.refresh_token_expires_at = _parse_expire(
        token_data.get("refresh_token_expire_in"),
        now=now,
    )
    row.granted_scopes = _format_scopes(token_data.get("granted_scopes"))
    raw_user_type = token_data.get("user_type")
    if raw_user_type is not None and raw_user_type != "":
        row.user_type = int(raw_user_type)
    open_id = token_data.get("open_id")
    if isinstance(open_id, str) and open_id.strip():
        row.open_id = open_id.strip()
    row.oauth_authorized_at = now


def _sync_tokens(
    db: Session,
    *,
    supplier_id: int,
    open_id: str,
    token_data: dict,
    now: datetime,
) -> None:
    rows = db.scalars(
        select(StoreTts).where(
            StoreTts.supplier_id == supplier_id,
            StoreTts.open_id == open_id,
            StoreTts.deleted_at.is_(None),
        )
    ).all()
    for row in rows:
        _apply_token_fields(row, token_data, now=now)


def refresh_access_token(db: Session, row: StoreTts) -> StoreTts:
    """刷新后按同一供应商、同一 open_id 更新全部店铺行。"""
    if row.deleted_at is not None:
        raise bad_request("店铺已删除")
    if not row.refresh_token:
        raise raise_reauth_required("店铺缺少 refresh_token，请重新授权")

    now = datetime.now(timezone.utc)
    refresh_expires = _normalize_expires_at(row.refresh_token_expires_at)
    if refresh_expires is not None and refresh_expires <= now:
        raise raise_reauth_required("TikTok 授权已过期，请重新授权")

    lock = _get_lock(_lock_key(row.supplier_id, row.open_id))
    with lock:
        db.refresh(row)
        if not row.refresh_token:
            raise raise_reauth_required("店铺缺少 refresh_token，请重新授权")
        token_data = _refresh_token(row.refresh_token)
        _require_seller(token_data)
        open_id = token_data.get("open_id") or row.open_id
        if not isinstance(open_id, str) or not open_id.strip():
            raise bad_request("TikTok 未返回 open_id")
        open_id = open_id.strip()
        _sync_tokens(
            db,
            supplier_id=row.supplier_id,
            open_id=row.open_id,
            token_data=token_data,
            now=now,
        )
        if open_id != row.open_id:
            _sync_tokens(
                db,
                supplier_id=row.supplier_id,
                open_id=open_id,
                token_data=token_data,
                now=now,
            )
        db.commit()
        db.refresh(row)
        logger.info(
            "TikTok refresh token 成功 supplier_id=%s open_id=%s",
            row.supplier_id,
            open_id,
        )
        return row


def ensure_valid_access_token(db: Session, row: StoreTts) -> str:
    """返回可用 access_token。临近过期时刷新，并写回同一 open_id 的各行。"""
    if row.deleted_at is not None:
        raise bad_request("店铺已删除")
    if not row.access_token:
        raise raise_reauth_required("店铺未授权 TikTok，请先完成授权")

    now = datetime.now(timezone.utc)
    expires = _normalize_expires_at(row.access_token_expires_at)
    buffer = timedelta(minutes=_REFRESH_BUFFER_MINUTES)
    if expires is None or expires <= now + buffer:
        row = refresh_access_token(db, row)
    if not row.access_token:
        raise raise_reauth_required("店铺未授权 TikTok，请先完成授权")
    return row.access_token


def _consume_pending(db: Session, state: str | None) -> tuple[int, int | None]:
    if not state or len(state) > 20:
        raise bad_request("无效的 state")
    pending = db.scalar(
        select(StoreTtsOauthPending).where(StoreTtsOauthPending.state == state)
    )
    if pending is None:
        raise bad_request("授权 state 无效或已失效，请重新发起授权")

    now = datetime.now(timezone.utc)
    expires_at = pending.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    supplier_id = pending.supplier_id
    actor_id = pending.created_by
    db.delete(pending)
    if expires_at < now:
        db.commit()
        raise bad_request("授权 state 已过期，请重新发起授权")
    db.commit()
    return supplier_id, actor_id


def _clip(value: str, limit: int) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[:limit]


def _normalize_shops(raw_shops: list[dict]) -> list[TiktokShopPayload]:
    shops: list[TiktokShopPayload] = []
    seen: set[str] = set()
    for item in raw_shops:
        shop_id = str(item.get("id") or "").strip()
        cipher = str(item.get("cipher") or "").strip()
        code = str(item.get("code") or "").strip() or shop_id
        if not shop_id or not cipher:
            raise bad_request("TikTok 返回的店铺缺少 shop_id 或 shop_cipher")
        if shop_id in seen:
            continue
        seen.add(shop_id)
        name = str(item.get("name") or "").strip() or code or "TikTok店铺"
        region = str(item.get("region") or "").strip() or None
        seller_type = str(item.get("seller_type") or "").strip() or None
        shops.append(
            TiktokShopPayload(
                shop_id=shop_id,
                shop_code=_clip(code, _CODE_MAX),
                cipher=cipher,
                name=_clip(name, _NAME_MAX),
                region=_clip(region, 16) if region else None,
                seller_type=_clip(seller_type, 32) if seller_type else None,
            )
        )
    return shops


def _load_tts_by_shop_id(db: Session, shop_id: str) -> StoreTts | None:
    return db.scalar(
        select(StoreTts)
        .options(joinedload(StoreTts.store))
        .where(
            StoreTts.shop_id == shop_id,
            StoreTts.deleted_at.is_(None),
        )
    )


def _upsert_shops(
    db: Session,
    *,
    supplier_id: int,
    actor_id: int | None,
    shops: list[TiktokShopPayload],
    token_data: dict,
    now: datetime,
) -> list[Store]:
    open_id = token_data.get("open_id")
    if not isinstance(open_id, str) or not open_id.strip():
        raise bad_request("TikTok 未返回 open_id")
    open_id = open_id.strip()

    existing_rows: dict[str, StoreTts] = {}
    previous_open_ids: set[str] = set()
    for shop in shops:
        row = _load_tts_by_shop_id(db, shop.shop_id)
        if row is None:
            continue
        if row.supplier_id != supplier_id:
            raise bad_request(f"店铺 {shop.shop_code} 已属于其他供应商")
        if row.store is None or row.store.deleted_at is not None:
            raise bad_request(f"店铺 {shop.shop_code} 数据不一致，请联系管理员")
        existing_rows[shop.shop_id] = row
        if row.open_id:
            previous_open_ids.add(row.open_id)

    touched: list[Store] = []
    for shop in shops:
        row = existing_rows.get(shop.shop_id)
        if row is None:
            store = Store(
                supplier_id=supplier_id,
                store_type=StoreType.TIKTOK.value,
                name=shop.name,
                identifier=shop.shop_code,
                base_discount=Decimal("0"),
                account="",
                password="",
                created_by=actor_id,
                updated_by=actor_id,
            )
            db.add(store)
            db.flush()
            row = StoreTts(
                store_id=store.id,
                supplier_id=supplier_id,
                shop_id=shop.shop_id,
                shop_cipher=shop.cipher,
                shop_code=shop.shop_code,
                region=shop.region,
                seller_type=shop.seller_type,
                open_id=open_id,
            )
            _apply_token_fields(row, token_data, now=now)
            db.add(row)
            touched.append(store)
            continue

        store = row.store
        store.name = shop.name
        store.identifier = shop.shop_code
        store.updated_by = actor_id
        row.shop_cipher = shop.cipher
        row.shop_code = shop.shop_code
        row.region = shop.region
        row.seller_type = shop.seller_type
        row.open_id = open_id
        _apply_token_fields(row, token_data, now=now)
        touched.append(store)

    db.flush()
    open_ids = {open_id, *previous_open_ids}
    for current_open_id in open_ids:
        if not current_open_id:
            continue
        _sync_tokens(
            db,
            supplier_id=supplier_id,
            open_id=current_open_id,
            token_data=token_data,
            now=now,
        )
    return touched


def _success_message(shops: list[TiktokShopPayload]) -> str:
    shown = "、".join(f"{shop.name}（{shop.region or '-'}）" for shop in shops[:8])
    suffix = "" if len(shops) <= 8 else f" 等{len(shops)}家"
    return f"已同步 {len(shops)} 家店铺：{shown}{suffix}"


def _resolve_callback_state(state: str | None) -> str | None:
    """正式回调用 TikTok 带回的 state。测试店铺不带 state 时，改用环境变量里预留的值。"""
    text = (state or "").strip()
    if text and text not in {"null", "None"}:
        return text
    fallback = settings.TIKTOK_AUTH_TEST_STORE_STATE.strip()
    return fallback or None


def handle_oauth_callback(
    db: Session,
    *,
    code: str | None,
    state: str | None,
) -> TiktokOauthResult:
    """校验 state、换 token、按 Get Authorized Shops 建档或更新。"""
    if not code or code in {"null", "None"}:
        raise bad_request("缺少授权码 code")

    supplier_id, actor_id = _consume_pending(db, _resolve_callback_state(state))
    try:
        token_data = _exchange_code(code)
        _require_seller(token_data)
        raw_shops = fetch_authorized_shops(str(token_data["access_token"]))
        shops = _normalize_shops(raw_shops)
        if not shops:
            raise bad_request("这次授权没有返回店铺")
        now = datetime.now(timezone.utc)
        touched = _upsert_shops(
            db,
            supplier_id=supplier_id,
            actor_id=actor_id,
            shops=shops,
            token_data=token_data,
            now=now,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        detail = str(exc.orig).lower() if exc.orig is not None else str(exc).lower()
        if "identifier" in detail:
            raise bad_request("店铺标识已存在，无法自动建档") from exc
        raise bad_request("TikTok 店铺写入冲突") from exc
    except AppError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("TikTok 授权建档失败 supplier_id=%s", supplier_id)
        raise

    logger.info(
        "TikTok OAuth 授权成功 supplier_id=%s shops=%s",
        supplier_id,
        len(shops),
    )
    return TiktokOauthResult(
        message=_success_message(shops),
        store_id=touched[0].id if touched else None,
    )


def build_frontend_redirect(
    *,
    ok: bool,
    store_id: int | None = None,
    message: str = "",
) -> str:
    """302 到现有前端 /callback，与敦煌共用 DHGATE_FRONTEND_REDIRECT_URI。"""
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
