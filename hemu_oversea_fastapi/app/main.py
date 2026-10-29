import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.common.test_api import reorder_dhgate_openapi_paths
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


# Swagger /docs 分组顺序：admin → common → app → 其它
# 敦煌联调统一为 common:testAPI:dhgate：单店在前，多店编排整体在最后
openapi_tags = [
    # —— admin ——
    {"name": "admin:auth", "description": "管理端认证"},
    {"name": "admin:users", "description": "管理端用户管理"},
    {"name": "admin:permissions", "description": "管理端权限"},
    {"name": "admin:roles", "description": "管理端角色"},
    {"name": "admin:staff", "description": "管理端员工"},
    {"name": "admin:suppliers", "description": "管理端供应商管理"},
    {"name": "admin:stores", "description": "管理端店铺管理"},
    {"name": "admin:product", "description": "管理端商品管理"},
    {"name": "admin:categories", "description": "管理端商品分类"},
    {"name": "admin:mission", "description": "管理端任务管理"},
    {"name": "admin:templates", "description": "管理端模板"},
    {"name": "admin:sku", "description": "管理端 SKU"},
    {"name": "admin:logs", "description": "管理端系统日志"},
    # —— common ——
    {"name": "common:ping", "description": "公共探活"},
    {
        "name": "common:utils",
        "description": "全局工具类接口（含第三方 OAuth、敦煌商品页 RSC 联调等）",
    },
    {"name": "common:testAPI:dhgate", "description": "敦煌开放平台联调"},
    # —— app / 其它 ——
    {"name": "app:auth", "description": "App 端认证"},
    {"name": "app:users", "description": "App 端用户"},
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


def _openapi() -> dict:
    """生成 OpenAPI，并把敦煌联调接口按同类排到一起。"""
    if getattr(app, "_dhgate_docs_ready", False) and app.openapi_schema:
        return app.openapi_schema
    app.openapi_schema = None
    schema = FastAPI.openapi(app)
    schema["paths"] = reorder_dhgate_openapi_paths(schema.get("paths") or {})
    app.openapi_schema = schema
    app._dhgate_docs_ready = True
    return schema


app.openapi = _openapi


@app.get("/", response_model=ApiResponse[dict])
def root() -> ApiResponse[dict]:
    return success(data={"message": "Hello World"})
