from fastapi import APIRouter

from app.api.common.oauth_dhgate import router as oauth_dhgate_router
from app.api.common.ping import router as ping_router
from app.api.common.test_api import router as test_api_router
from app.api.common.utils import router as utils_router

router = APIRouter(prefix="/common")
router.include_router(ping_router)
router.include_router(oauth_dhgate_router)
router.include_router(utils_router)
router.include_router(test_api_router)
