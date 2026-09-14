from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_app_user
from app.models.user import User
from app.schemas.auth import (
    AuthLoginResponse,
    LoginRequest,
    PasswordChangeRequest,
    RefreshRequest,
    TokenPair,
)
from app.schemas.common import ApiResponse, success
from app.schemas.user import UserCreate, UserPublic
from app.services.auth import (
    change_password,
    login_for_audience,
    logout_all_for_audience,
    logout_for_audience,
    refresh_for_audience,
)
from app.services.users import create_user

router = APIRouter(prefix="/auth", tags=["app:auth"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    return ip, request.headers.get("user-agent")


@router.post("/register", status_code=201, response_model=ApiResponse[UserPublic])
def register(payload: UserCreate, db: Session = Depends(get_db)) -> ApiResponse[UserPublic]:
    user = create_user(
        db,
        username=payload.username,
        email=payload.email,
        password=payload.password,
        nickname=payload.nickname,
        phone=payload.phone,
        avatar_url=payload.avatar_url,
        role="app_user",
        org_type="none",
    )
    return success(UserPublic.model_validate(user))


@router.post("/login", response_model=ApiResponse[AuthLoginResponse])
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ApiResponse[AuthLoginResponse]:
    ip, user_agent = _client_meta(request)
    return success(
        login_for_audience(
            db,
            username=payload.username,
            password=payload.password,
            audience="app",
            ip=ip,
            user_agent=user_agent,
        )
    )


@router.post("/refresh", response_model=ApiResponse[TokenPair])
def refresh(
    payload: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ApiResponse[TokenPair]:
    ip, user_agent = _client_meta(request)
    return success(
        refresh_for_audience(
            db,
            refresh_token=payload.refresh_token,
            audience="app",
            ip=ip,
            user_agent=user_agent,
        )
    )


@router.post("/logout", response_model=ApiResponse[dict])
def logout(payload: RefreshRequest, db: Session = Depends(get_db)) -> ApiResponse[dict]:
    logout_for_audience(db, refresh_token=payload.refresh_token, audience="app")
    return success({})


@router.post("/logout-all", response_model=ApiResponse[dict])
def logout_all(
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    logout_all_for_audience(db, user_id=current_user.id, audience="app")
    return success({})


@router.post("/password", response_model=ApiResponse[dict])
def update_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    change_password(
        db,
        current_user,
        old_password=payload.old_password,
        new_password=payload.new_password,
    )
    return success({})
