from fastapi import APIRouter

from app.schemas.common import ApiResponse, success

router = APIRouter(tags=["common:ping"])


@router.get("/ping", response_model=ApiResponse[dict])
def ping() -> ApiResponse[dict]:
    """公开探活，App 与管理端都可调用，无需登录。"""
    return success({"status": "pong"})
