"""TikTok Shop 请求签名与 Get Authorized Shops。"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import bad_request
from app.models.store_tts import StoreTts

logger = logging.getLogger("app")

SHOPS_PATH = "/authorization/202309/shops"


def sign_request(
    path: str,
    params: dict[str, str],
    body: str | None = None,
) -> str:
    """官方签名：secret + path + 排序 query + body + secret，HMAC-SHA256 小写十六进制。"""
    secret = settings.TIKTOK_APP_SECRET
    pieces = "".join(
        f"{key}{params[key]}"
        for key in sorted(params)
        if key not in ("sign", "access_token")
    )
    raw = f"{path}{pieces}"
    if body:
        raw += body
    message = f"{secret}{raw}{secret}"
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def _api_base() -> str:
    return settings.TIKTOK_API_BASE_URL.rstrip("/")


def request_json(
    url: str,
    *,
    params: dict[str, str],
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """GET 并要求 body.code == 0。失败时把 TikTok 的 message 抛给调用方。"""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params, headers=headers)
    except httpx.HTTPError as exc:
        logger.exception("TikTok 请求网络失败 url=%s", url.split("?", 1)[0])
        raise bad_request(f"请求 TikTok 失败: {exc}") from exc

    try:
        body = response.json()
    except ValueError as exc:
        logger.error(
            "TikTok 响应非 JSON status=%s url=%s",
            response.status_code,
            url.split("?", 1)[0],
        )
        raise bad_request("TikTok 返回异常") from exc

    if not isinstance(body, dict):
        raise bad_request("TikTok 返回异常")

    code = body.get("code")
    message = body.get("message") or "TikTok 请求失败"
    if response.status_code >= 400 or code not in (0, "0"):
        logger.warning(
            "TikTok 请求失败 status=%s code=%s message=%s request_id=%s",
            response.status_code,
            code,
            message,
            body.get("request_id"),
        )
        raise bad_request(str(message))
    return body


def fetch_authorized_shops(access_token: str) -> list[dict[str, Any]]:
    """GET /authorization/202309/shops。access_token 放请求头。"""
    if not settings.TIKTOK_APP_KEY or not settings.TIKTOK_APP_SECRET:
        raise bad_request("未配置 TikTok Shop App Key / App Secret")
    timestamp = str(int(time.time()))
    params = {
        "app_key": settings.TIKTOK_APP_KEY,
        "timestamp": timestamp,
    }
    params["sign"] = sign_request(SHOPS_PATH, params)
    body = request_json(
        f"{_api_base()}{SHOPS_PATH}",
        params=params,
        headers={
            "Content-Type": "application/json",
            "x-tts-access-token": access_token,
        },
    )
    data = body.get("data")
    shops = data.get("shops") if isinstance(data, dict) else None
    if not isinstance(shops, list):
        return []
    return [item for item in shops if isinstance(item, dict)]


class TiktokClient:
    """按一条 store_tts 取 token 与 shop_cipher，再调店铺接口。"""

    def __init__(self, db: Session, row: StoreTts) -> None:
        self.db = db
        self.row = row

    @property
    def shop_cipher(self) -> str:
        return self.row.shop_cipher

    def get_authorized_shops(self) -> list[dict[str, Any]]:
        from app.services.tiktok_oauth import ensure_valid_access_token

        token = ensure_valid_access_token(self.db, self.row)
        return fetch_authorized_shops(token)
