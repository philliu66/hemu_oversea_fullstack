"""敦煌开放平台业务 API 响应解析。"""

from __future__ import annotations

import httpx

from app.core.errors import AppError, bad_request

# 平台错误码：Access Token is expired or does not exist
TOKEN_EXPIRED_ERROR_CODE = "40"

_SUCCESS_CODES = frozenset({None, "00000000", 0, "0"})


def parse_http_response(response: httpx.Response) -> dict:
    try:
        data = response.json()
    except ValueError as exc:
        raise bad_request(
            f"敦煌 API 响应非 JSON status={response.status_code}"
        ) from exc
    if not isinstance(data, dict):
        raise bad_request("敦煌 API 响应格式异常")
    return data


def get_status_code(data: dict) -> str | None:
    status = data.get("status")
    if isinstance(status, dict):
        code = status.get("code")
        if code is not None:
            return str(code)
    return None


def get_status_message(data: dict) -> str:
    status = data.get("status")
    if isinstance(status, dict) and status.get("message"):
        return str(status["message"])
    if data.get("error_description"):
        return str(data["error_description"])
    if data.get("error"):
        return str(data["error"])
    return "敦煌 API 调用失败"


def format_status_error_message(data: dict) -> str:
    """拼接敦煌 status.message 与 subErrors.message，用 / 分隔。"""
    parts: list[str] = []
    status = data.get("status")
    if isinstance(status, dict):
        if status.get("message"):
            parts.append(str(status["message"]).strip())
        sub_errors = status.get("subErrors")
        if isinstance(sub_errors, list):
            for item in sub_errors:
                if not isinstance(item, dict):
                    continue
                message = item.get("message")
                if not message:
                    continue
                text = str(message).strip()
                if text and text not in parts:
                    parts.append(text)
    if parts:
        return "/".join(parts)
    if data.get("error_description"):
        return str(data["error_description"])
    if data.get("error"):
        return str(data["error"])
    return "敦煌 API 调用失败"


def is_success(data: dict) -> bool:
    if data.get("error"):
        return False
    code = get_status_code(data)
    return code in _SUCCESS_CODES


def is_token_expired(data: dict) -> bool:
    code = get_status_code(data)
    if code == TOKEN_EXPIRED_ERROR_CODE:
        return True
    message = get_status_message(data).lower()
    return "access token" in message and (
        "expired" in message or "does not exist" in message
    )


def is_refresh_token_expired(data: dict) -> bool:
    """刷新接口明确表示 refresh_token 已过期或无效。"""
    error = str(data.get("error") or "").strip().lower()
    if error == "invalid_grant":
        return True
    text = f"{error} {format_status_error_message(data)}".lower()
    if "refresh" not in text and "刷新" not in text:
        return False
    return any(
        marker in text
        for marker in (
            "expir",
            "invalid",
            "not exist",
            "does not exist",
            "过期",
            "失效",
            "无效",
            "不存在",
        )
    )


def raise_if_error(data: dict) -> None:
    if is_success(data):
        return
    message = format_status_error_message(data)
    code = get_status_code(data)
    raise bad_request(
        message,
        data={"dhgate_error_code": code, "dhgate_response": data},
    )


def extract_result(data: dict) -> dict:
    """成功响应中去掉 status 包装，返回业务字段。"""
    return {key: value for key, value in data.items() if key != "status"}


def raise_reauth_required(message: str = "敦煌授权已失效，请重新授权") -> AppError:
    return bad_request(message, data={"oauth_reauth_required": True})


def format_dhgate_error_message(exc: AppError, *, fallback: str = "敦煌 API 调用失败") -> str:
    """从 AppError 中拼出可读的敦煌官方错误信息（message/subErrors 用 / 分隔）。"""
    data = exc.data if isinstance(exc.data, dict) else {}
    response = data.get("dhgate_response")
    if isinstance(response, dict):
        return format_status_error_message(response)
    return (exc.message or "").strip() or fallback
