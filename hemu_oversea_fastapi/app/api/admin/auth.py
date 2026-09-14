from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_admin_user
from app.models.user import User
from app.schemas.auth import (
    AdminLoginRequest,
    AuthLoginResponse,
    CaptchaResponse,
    LoginRequest,
    PasswordChangeRequest,
    RefreshRequest,
    TokenPair,
)
from app.schemas.common import ApiResponse, success
from app.services.auth import (
    change_password,
    login_for_audience,
    logout_all_for_audience,
    logout_for_audience,
    refresh_for_audience,
)
from app.services.captcha import create_captcha, verify_captcha

router = APIRouter(prefix="/auth", tags=["admin:auth"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    return ip, request.headers.get("user-agent")


@router.post(
    "/auto-login",
    response_model=ApiResponse[AuthLoginResponse],
    summary="[联调] 免验证码自动登录",
)
def auto_login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ApiResponse[AuthLoginResponse]:
    """仅账号密码登录，跳过图形验证码；返回与 /login 相同。仅供 /docs 联调。"""
    ip, user_agent = _client_meta(request)
    return success(
        login_for_audience(
            db,
            username=payload.username,
            password=payload.password,
            audience="admin",
            ip=ip,
            user_agent=user_agent,
        )
    )


@router.get("/captcha", response_model=ApiResponse[CaptchaResponse])
def get_captcha(db: Session = Depends(get_db)) -> ApiResponse[CaptchaResponse]:
    """管理端登录页获取图形验证码（4 位字母或数字）。"""
    return success(create_captcha(db, audience="admin"))


@router.post("/login", response_model=ApiResponse[AuthLoginResponse])
def login(
    payload: AdminLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ApiResponse[AuthLoginResponse]:
    """管理端登录：校验图形验证码；密码为明文，后端 Argon2 校验。返回 token + 用户信息。"""
    verify_captcha(
        db,
        captcha_id=payload.captcha_id,
        code=payload.captcha_code,
        audience="admin",
    )
    ip, user_agent = _client_meta(request)
    return success(
        login_for_audience(
            db,
            username=payload.username,
            password=payload.password,
            audience="admin",
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
            audience="admin",
            ip=ip,
            user_agent=user_agent,
        )
    )


@router.post("/logout", response_model=ApiResponse[dict])
def logout(payload: RefreshRequest, db: Session = Depends(get_db)) -> ApiResponse[dict]:
    logout_for_audience(db, refresh_token=payload.refresh_token, audience="admin")
    return success({})


@router.post("/logout-all", response_model=ApiResponse[dict])
def logout_all(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    logout_all_for_audience(db, user_id=current_user.id, audience="admin")
    return success({})


@router.post("/password", response_model=ApiResponse[dict])
def update_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    """修改当前登录用户密码；old/new 均为明文。"""
    change_password(
        db,
        current_user,
        old_password=payload.old_password,
        new_password=payload.new_password,
    )
    return success({})
