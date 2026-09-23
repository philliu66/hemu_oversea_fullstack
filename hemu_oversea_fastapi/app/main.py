import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.router import api_router
from app.core.config import settings
from app.core.db import engine
from app.core.errors import register_exception_handlers
from app.core.middleware import RequestIdMiddleware
from app.core.seed import ensure_seed_users
from app.schemas.common import ApiResponse, success

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup")
    ensure_seed_users()
    yield
    engine.dispose()
    logger.info("shutdown")


openapi_tags = [
    {"name": "admin:auth", "description": "管理端认证"},
    {"name": "admin:users", "description": "管理端用户管理"},
    {"name": "admin:suppliers", "description": "管理端供应商管理"},
    {"name": "admin:stores", "description": "管理端店铺管理"},
    {"name": "admin:product", "description": "管理端商品管理"},
    {"name": "admin:categories", "description": "管理端商品分类"},
    {"name": "admin:mission", "description": "管理端任务管理"},
    {"name": "app:auth", "description": "App 端认证"},
    {"name": "app:users", "description": "App 端用户"},
    {"name": "common:ping", "description": "公共探活"},
    {"name": "common:utils", "description": "全局工具类接口（含第三方 OAuth 回调等）"},
    {
        "name": "common:testAPI:dhgate",
        "description": "敦煌 API 联调（单店官方接口 + 多店 commerce 编排，仅调试）",
    },
    {"name": "health", "description": "健康检查"},
    {"name": "errors", "description": "错误示例"},
]

app = FastAPI(
    title="hemu_oversea_fastapi",
    lifespan=lifespan,
    openapi_tags=openapi_tags,
    swagger_ui_parameters={"docExpansion": "none"},
)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)
app.include_router(health_router)
app.include_router(api_router, prefix="/api/v1")


@app.get("/", response_model=ApiResponse[dict])
def root() -> ApiResponse[dict]:
    return success(data={"message": "Hello World"})
