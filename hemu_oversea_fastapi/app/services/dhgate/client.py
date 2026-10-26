"""敦煌开放平台业务 API HTTP 客户端。"""

from __future__ import annotations

import json
import logging
import time
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Literal

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import bad_request
from app.models.store import Store
from app.services.dhgate.oauth import (
    DHGATE_HTTP_HEADERS,
    ensure_valid_access_token,
    refresh_access_token,
)
from app.services.dhgate.response import (
    extract_result,
    is_token_expired,
    parse_http_response,
    raise_if_error,
    raise_reauth_required,
)

logger = logging.getLogger("app")

HttpMethod = Literal["GET", "POST"]
_SENSITIVE_PARAM_KEYS = frozenset({"access_token", "client_secret"})
_OMIT_VALUE_PARAM_KEYS = frozenset({"imgBase64"})


@dataclass
class DhgateCallRecord:
    """单次敦煌 API 调用留痕（联调 / 排查用）。"""

    method: str
    version: str
    http_method: str
    params: dict[str, str]
    http_status: int
    response: dict[str, Any]


def _dhgate_api_url() -> str:
    if settings.DHGATE_USE_SANDBOX:
        return settings.DHGATE_SANDBOX_API_URL
    return settings.DHGATE_API_URL


def _stringify_params(params: dict) -> dict[str, str]:
    """标量转字符串；dict / list 按敦煌入参要求 JSON 序列化。"""
    encoded: dict[str, str] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            encoded[key] = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        else:
            encoded[key] = str(value)
    return encoded


def _request_timestamp_ms() -> str:
    """敦煌公共参数 timestamp：毫秒时间戳（北京时间 UTC+8，服务端容忍约 30 分钟）。"""
    return str(int(time.time() * 1000))


def _public_params(params: dict[str, str]) -> dict[str, str]:
    public: dict[str, str] = {}
    for key, value in params.items():
        if key in _SENSITIVE_PARAM_KEYS:
            continue
        if key in _OMIT_VALUE_PARAM_KEYS:
            public[key] = f"<omitted len={len(value)}>"
            continue
        public[key] = value
    return public


class DhgateClient:
    """敦煌业务 API 统一调用入口（自动携带 token、过期刷新、重试一次）。"""

    def __init__(self, db: Session, store: Store) -> None:
        self.db = db
        self.store = store
        self._call_history: list[DhgateCallRecord] = []

    @property
    def call_history(self) -> list[dict[str, Any]]:
        """本次 client 生命周期内的全部原始调用记录（可 JSON 序列化）。"""
        return [asdict(item) for item in self._call_history]

    @property
    def last_raw(self) -> dict[str, Any] | None:
        """最近一次原始响应（含 status）；无调用时为 None。"""
        if not self._call_history:
            return None
        return deepcopy(self._call_history[-1].response)

    def clear_call_history(self) -> None:
        self._call_history.clear()

    def call(
        self,
        method: str,
        *,
        version: str,
        params: dict | None = None,
        http_method: HttpMethod = "GET",
        timeout: float = 30.0,
    ) -> dict:
        access_token = ensure_valid_access_token(self.db, self.store)
        return self._call_once(
            method,
            version=version,
            params=params or {},
            access_token=access_token,
            http_method=http_method,
            timeout=timeout,
            retried=False,
        )

    def _record_call(
        self,
        *,
        method: str,
        version: str,
        http_method: str,
        request_params: dict[str, str],
        http_status: int,
        response_body: dict[str, Any],
    ) -> None:
        self._call_history.append(
            DhgateCallRecord(
                method=method,
                version=version,
                http_method=http_method,
                params=_public_params(request_params),
                http_status=http_status,
                response=deepcopy(response_body),
            )
        )

    def _call_once(
        self,
        method: str,
        *,
        version: str,
        params: dict,
        access_token: str,
        http_method: HttpMethod,
        timeout: float,
        retried: bool,
    ) -> dict:
        request_params = _stringify_params(
            {
                "method": method,
                "v": version,
                "access_token": access_token,
                "timestamp": _request_timestamp_ms(),
                **params,
            }
        )

        api_url = _dhgate_api_url()
        try:
            if http_method == "GET":
                response = httpx.get(
                    api_url,
                    params=request_params,
                    headers=DHGATE_HTTP_HEADERS,
                    timeout=timeout,
                )
            else:
                response = httpx.post(
                    api_url,
                    data=request_params,
                    headers=DHGATE_HTTP_HEADERS,
                    timeout=timeout,
                )
        except httpx.HTTPError as exc:
            logger.exception(
                "敦煌 API 网络失败 store_id=%s method=%s url=%s",
                self.store.id,
                method,
                api_url,
            )
            raise bad_request(f"请求敦煌 API 失败: {exc}") from exc

        data = parse_http_response(response)
        self._record_call(
            method=method,
            version=version,
            http_method=http_method,
            request_params=request_params,
            http_status=response.status_code,
            response_body=data,
        )

        if is_token_expired(data) and not retried:
            refresh_access_token(self.db, self.store)
            self.db.refresh(self.store)
            if not self.store.access_token:
                raise raise_reauth_required()
            return self._call_once(
                method,
                version=version,
                params=params,
                access_token=self.store.access_token,
                http_method=http_method,
                timeout=timeout,
                retried=True,
            )

        raise_if_error(data, http_status=response.status_code)
        return extract_result(data)
