import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app")


class ErrorCode:
    BAD_REQUEST = 40000
    UNAUTHORIZED = 40100
    FORBIDDEN = 40300
    NOT_FOUND = 40400
    CONFLICT = 40900
    TOO_MANY = 42900
    VALIDATION = 42200
    INTERNAL = 50000


_STATUS_TO_CODE = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.VALIDATION,
    429: ErrorCode.TOO_MANY,
    500: ErrorCode.INTERNAL,
}


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: int,
        message: str,
        data: dict | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.data = data


def bad_request(message: str, data: dict | None = None) -> AppError:
    return AppError(400, ErrorCode.BAD_REQUEST, message, data)


def unauthorized(message: str = "未登录或登录已过期") -> AppError:
    return AppError(401, ErrorCode.UNAUTHORIZED, message)


def forbidden(message: str = "权限不足") -> AppError:
    return AppError(403, ErrorCode.FORBIDDEN, message)


def not_found(message: str = "资源不存在") -> AppError:
    return AppError(404, ErrorCode.NOT_FOUND, message)


def conflict(message: str, data: dict | None = None) -> AppError:
    return AppError(409, ErrorCode.CONFLICT, message, data)


def too_many_requests(
    message: str = "尝试过于频繁，请稍后再试",
    *,
    retry_after: int = 60,
) -> AppError:
    return AppError(429, ErrorCode.TOO_MANY, message, {"retry_after": retry_after})


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _error_body(code: int, message: str, data: dict | None = None) -> dict:
    return {"code": code, "message": message, "data": data}


def _json_error(
    request: Request,
    status_code: int,
    code: int,
    message: str,
    data: dict | None = None,
    extra_headers: dict[str, str] | None = None,
) -> JSONResponse:
    headers = {"X-Request-ID": _request_id(request)}
    if extra_headers:
        headers.update(extra_headers)
    return JSONResponse(
        status_code=status_code,
        content=_error_body(code, message, data),
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        extra: dict[str, str] = {}
        if exc.status_code == 429 and exc.data and exc.data.get("retry_after") is not None:
            extra["Retry-After"] = str(exc.data["retry_after"])
        return _json_error(
            request,
            exc.status_code,
            exc.code,
            exc.message,
            exc.data,
            extra_headers=extra or None,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "请求失败"
        code = _STATUS_TO_CODE.get(exc.status_code, exc.status_code * 100)
        return _json_error(request, exc.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = []
        for item in exc.errors():
            loc = [str(part) for part in item["loc"] if part not in {"body", "query", "path"}]
            errors.append({"field": ".".join(loc), "message": item["msg"]})
        return _json_error(
            request,
            422,
            ErrorCode.VALIDATION,
            "请求参数校验失败",
            {"errors": errors},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("未处理异常 request_id=%s", _request_id(request))
        return _json_error(request, 500, ErrorCode.INTERNAL, "服务器内部错误")