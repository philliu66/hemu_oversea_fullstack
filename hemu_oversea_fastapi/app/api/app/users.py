from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_app_user
from app.models.user import User
from app.schemas.common import ApiResponse, success
from app.schemas.user import UserPublic
from app.services import users as user_service

router = APIRouter(prefix="/users", tags=["app:users"])


@router.get("/me", response_model=ApiResponse[UserPublic])
def read_me(current_user: User = Depends(get_current_app_user)) -> ApiResponse[UserPublic]:
    return success(UserPublic.model_validate(current_user))


@router.delete("/me", response_model=ApiResponse[dict])
def delete_me(
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    user_service.soft_delete_self(db, current_user)
    return success({})
