from fastapi import APIRouter

from app.api.admin import router as admin_router
from app.api.app import router as app_router
from app.api.common import router as common_router
from app.api.errors import router as errors_router

# TODO: 联调稳定后恢复公共 Header 校验（X-Sign / X-Timestamp / X-Channel）
# from fastapi import Depends
# from app.core.client_headers import get_common_headers
# api_router = APIRouter(dependencies=[Depends(get_common_headers)])

# 路由注册顺序配合 openapi_tags：admin → common → app → errors
api_router = APIRouter()
api_router.include_router(admin_router)
api_router.include_router(common_router)
api_router.include_router(app_router)
api_router.include_router(errors_router)
