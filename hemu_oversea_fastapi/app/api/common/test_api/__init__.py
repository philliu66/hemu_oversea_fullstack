"""第三方平台 / 敦煌多店编排 API 联调入口（仅调试，非业务接口）。

- /testAPI/dhgate/*：单店官方接口
- /testAPI/dhgate/commerce/*：敦煌多店编排（处罚汇总、商品同步等）
"""

from fastapi import APIRouter

from app.api.common.test_api.commerce import router as commerce_test_router
from app.api.common.test_api.dhgate import router as dhgate_test_router

router = APIRouter(prefix="/testAPI")
router.include_router(dhgate_test_router)
router.include_router(commerce_test_router)
