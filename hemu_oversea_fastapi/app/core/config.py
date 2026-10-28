from functools import lru_cache
from pathlib import Path
from typing import Self
from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Docker Compose 与应用共用；未设置 DATABASE_URL 时由此组装连接串
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "hemu_oversea_fastapi"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5500
    # 可选覆盖（如 RDS 完整 DSN）；非空时优先于上面的 POSTGRES_*
    DATABASE_URL: str = ""

    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_MINUTES: int = 15
    CAPTCHA_LENGTH: int = 4
    CAPTCHA_EXPIRE_SECONDS: int = 300
    BOOTSTRAP_PASSWORD: str = "123456"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # 敦煌开放平台 OAuth2
    DHGATE_APP_KEY: str = ""
    DHGATE_APP_SECRET: str = ""
    DHGATE_REDIRECT_URI: str = (
        "http://127.0.0.1:8000/api/v1/common/oauth/dhgate/callback"
    )
    DHGATE_FRONTEND_REDIRECT_URI: str = "http://localhost:8000/admin/callback"
    DHGATE_AUTHORIZE_URL: str = "https://secure.dhgate.com/dop/oauth2/authorize"
    DHGATE_TOKEN_URL: str = "https://secure.dhgate.com/dop/oauth2/access_token"
    DHGATE_API_URL: str = "http://api.dhgate.com/dop/router"
    DHGATE_SANDBOX_API_URL: str = "http://sandbox.api.dhgate.com/dop/router"
    DHGATE_USE_SANDBOX: bool = False
    DHGATE_OAUTH_SCOPE: str = "basic"
    DHGATE_OAUTH_STATE_TTL_MINUTES: int = 10
    DHGATE_TOKEN_REFRESH_BUFFER_MINUTES: int = 5

    # TikTok Shop 卖家授权
    TIKTOK_APP_KEY: str = ""
    TIKTOK_APP_SECRET: str = ""
    TIKTOK_SERVICE_ID: str = ""
    TIKTOK_AUTHORIZE_URL: str = "https://services.tiktokshop.com/open/authorize"
    TIKTOK_AUTH_BASE_URL: str = "https://auth.tiktok-shops.com"
    TIKTOK_API_BASE_URL: str = "https://open-api.tiktokglobalshop.com"
    TIKTOK_OAUTH_STATE_TTL_MINUTES: int = 10

    # 阿里云 RAM（邮件推送 DirectMail 等共用）
    ALIYUN_RAM_ACCESS_KEY_ID: str = ""
    ALIYUN_RAM_ACCESS_KEY_SECRET: str = ""

    # 阿里云邮件推送 DirectMail
    ALIYUN_DM_ACCOUNT_NAME: str = ""  # 控制台已验证的发信地址
    ALIYUN_DM_REGION_ID: str = "cn-hangzhou"
    ALIYUN_DM_ENDPOINT: str = "dm.aliyuncs.com"
    ALIYUN_DM_ADDRESS_TYPE: int = 1  # 0=随机账号；1=发信地址
    ALIYUN_DM_REPLY_TO_ADDRESS: bool = True  # 是否启用控制台回信地址

    @model_validator(mode="after")
    def assemble_database_url(self) -> Self:
        if self.DATABASE_URL.strip():
            return self
        password = quote_plus(self.POSTGRES_PASSWORD)
        self.DATABASE_URL = (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
