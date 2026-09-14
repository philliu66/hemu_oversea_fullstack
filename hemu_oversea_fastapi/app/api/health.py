from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.schemas.common import ApiResponse, success

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[dict])
def health(db: Session = Depends(get_db)) -> ApiResponse[dict]:
    db.execute(text("SELECT 1"))
    return success(
        {
            "status": "ok",
            "database": "ok",
            "dsn": settings.DATABASE_URL.split("@")[-1],
            "cors_origins": settings.CORS_ORIGINS,
        }
    )