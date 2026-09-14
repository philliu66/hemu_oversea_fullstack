from pydantic import BaseModel, Field

from app.schemas.user import UserPublic


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50, description="账号")
    password: str = Field(min_length=1, max_length=128, description="明文密码")
    captcha_id: str = Field(min_length=1, max_length=32, description="图形验证码 ID")
    captcha_code: str = Field(min_length=1, max_length=8, description="用户输入的验证码")


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthLoginResponse(TokenPair):
    """登录成功：token + 当前用户信息。"""

    user: UserPublic


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128, description="原明文密码")
    new_password: str = Field(min_length=6, max_length=128, description="新明文密码")


class CaptchaResponse(BaseModel):
    captcha_id: str
    image_base64: str = Field(description="PNG 的 Base64，不含 data: 前缀")
    expires_in: int = Field(description="有效秒数")
