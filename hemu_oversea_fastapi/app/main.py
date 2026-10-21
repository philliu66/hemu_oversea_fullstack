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


# Swagger /docs 分组顺序：admin → common → app → 其它
# 敦煌联调子标签对齐 open.dhgate.com / dhgate_API.md 卖家 API 划分
openapi_tags = [
    # —— admin ——
    {"name": "admin:auth", "description": "管理端认证"},
    {"name": "admin:users", "description": "管理端用户管理"},
    {"name": "admin:permissions", "description": "管理端权限"},
    {"name": "admin:platform-roles", "description": "管理端平台角色"},
    {"name": "admin:platform-staff", "description": "管理端平台员工"},
    {"name": "admin:supplier-roles", "description": "管理端供应商角色"},
    {"name": "admin:suppliers", "description": "管理端供应商管理"},
    {"name": "admin:supplier-staff", "description": "管理端供应商员工"},
    {"name": "admin:stores", "description": "管理端店铺管理"},
    {"name": "admin:product", "description": "管理端商品管理"},
    {"name": "admin:categories", "description": "管理端商品分类"},
    {"name": "admin:mission", "description": "管理端任务管理"},
    {"name": "admin:templates", "description": "管理端模板"},
    {"name": "admin:sku", "description": "管理端 SKU"},
    {"name": "admin:logs", "description": "管理端登录与操作日志"},
    # —— common ——
    {"name": "common:ping", "description": "公共探活"},
    {
        "name": "common:utils",
        "description": "全局工具类接口（含第三方 OAuth、敦煌商品页 RSC 联调等）",
    },
    {
        "name": "common:testAPI:dhgate:album",
        "description": "敦煌联调 · 相册 API（官方 2.1，单店）",
    },
    {
        "name": "common:testAPI:dhgate:base",
        "description": "敦煌联调 · 基础 API（官方 2.2，单店；处罚等）",
    },
    {
        "name": "common:testAPI:dhgate:category",
        "description": "敦煌联调 · 类目 API（官方 2.3，单店）",
    },
    {
        "name": "common:testAPI:dhgate:logistics",
        "description": "敦煌联调 · 物流 API（官方 2.5，单店）",
    },
    {
        "name": "common:testAPI:dhgate:order",
        "description": "敦煌联调 · 订单 API（官方 2.7，单店；含纠纷）",
    },
    {
        "name": "common:testAPI:dhgate:product",
        "description": "敦煌联调 · 产品 API（官方 2.8，单店）",
    },
    {
        "name": "common:testAPI:dhgate:data",
        "description": "敦煌联调 · 数据 API(限免)（wis.core / detail / keywordtop10，单店）",
    },
    {
        "name": "common:testAPI:dhgate:value-added",
        "description": "敦煌联调 · 增值 API（广告消耗报表 seller.ad.*，单店）",
    },
    {
        "name": "common:testAPI:dhgate:public",
        "description": "敦煌联调 · 公共 API · 基础（官方 3.1，单店）",
    },
    {
        "name": "common:testAPI:dhgate:commerce",
        "description": "敦煌联调 · 多店铺编排（汇总/同步，仅调试）",
    },
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


@app.get("/", response_model=ApiResponse[dict])
def root() -> ApiResponse[dict]:
    return success(data={"message": "Hello World"})
