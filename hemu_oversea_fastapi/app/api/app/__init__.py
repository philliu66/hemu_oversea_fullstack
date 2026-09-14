from fastapi import APIRouter

from app.api.app.auth import router as auth_router
from app.api.app.users import router as users_router

router = APIRouter(prefix="/app")
router.include_router(auth_router)
router.include_router(users_router)
