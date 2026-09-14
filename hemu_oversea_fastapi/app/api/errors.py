from fastapi import APIRouter, Query

from app.core.errors import not_found
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/errors", tags=["errors"])


@router.get("/missing", response_model=ApiResponse[dict])
def missing() -> ApiResponse[dict]:
    raise not_found("示例：资源不存在")


@router.get("/boom", response_model=ApiResponse[dict])
def boom() -> ApiResponse[dict]:
    raise RuntimeError("示例：未处理异常")


@router.get("/validate", response_model=ApiResponse[dict])
def validate(q: str = Query(min_length=3)) -> ApiResponse[dict]:
    return ApiResponse(data={"q": q})