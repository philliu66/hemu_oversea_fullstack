from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_MINUTES: int = 15
    CAPTCHA_LENGTH: int = 4
    CAPTCHA_EXPIRE_SECONDS: int = 300
    BOOTSTRAP_PASSWORD: str = "123456"
    BOOTSTRAP_SUPPLIER_ID: int = 1
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # 敦煌开放平台 OAuth2
    DHGATE_APP_KEY: str = ""
    DHGATE_APP_SECRET: str = ""
    DHGATE_REDIRECT_URI: str = (
        "http://127.0.0.1:8000/api/v1/common/oauth/dhgate/callback"
    )
    DHGATE_FRONTEND_REDIRECT_URI: str = "http://localhost:8000/callback"
    DHGATE_AUTHORIZE_URL: str = "https://secure.dhgate.com/dop/oauth2/authorize"
    DHGATE_TOKEN_URL: str = "https://secure.dhgate.com/dop/oauth2/access_token"
    DHGATE_API_URL: str = "http://api.dhgate.com/dop/router"
    DHGATE_SANDBOX_API_URL: str = "http://sandbox.api.dhgate.com/dop/router"
    DHGATE_USE_SANDBOX: bool = False
    DHGATE_OAUTH_SCOPE: str = "basic"
    DHGATE_OAUTH_STATE_TTL_MINUTES: int = 10
    DHGATE_TOKEN_REFRESH_BUFFER_MINUTES: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
