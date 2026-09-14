from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings

_password_hash = PasswordHash.recommended()

TokenType = Literal["access", "refresh"]
Audience = Literal["app", "admin"]


class TokenError(Exception):
    """JWT 无效、过期，或类型/受众不对。路由层再转成 401。"""


@dataclass(frozen=True)
class TokenPayload:
    subject: str
    jti: str
    token_type: TokenType
    audience: str


@dataclass(frozen=True)
class IssuedToken:
    token: str
    jti: str
    expires_at: datetime


def hash_password(plain_password: str) -> str:
    """入库：Argon2(明文)。"""
    return _password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码。"""
    try:
        return _password_hash.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(subject: str, audience: Audience) -> str:
    return _create_token(
        subject,
        "access",
        audience,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    ).token


def create_refresh_token(subject: str, audience: Audience) -> IssuedToken:
    return _create_token(
        subject,
        "refresh",
        audience,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(
    token: str,
    expected_type: TokenType,
    expected_audience: Audience | tuple[Audience, ...],
) -> TokenPayload:
    audience: str | list[str]
    if isinstance(expected_audience, tuple):
        audience = list(expected_audience)
    else:
        audience = expected_audience

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=audience,
        )
    except InvalidTokenError as exc:
        raise TokenError("无效或过期的令牌") from exc

    token_type = payload.get("typ")
    if token_type != expected_type:
        raise TokenError("令牌类型不正确")

    subject = payload.get("sub")
    jti = payload.get("jti")
    aud = payload.get("aud")
    if not subject or not jti or not aud:
        raise TokenError("令牌缺少必要字段")
    if not isinstance(aud, str):
        aud = aud[0] if aud else ""
    if not aud:
        raise TokenError("令牌缺少必要字段")
    return TokenPayload(
        subject=str(subject),
        jti=str(jti),
        token_type=expected_type,
        audience=aud,
    )


def _create_token(
    subject: str,
    token_type: TokenType,
    audience: Audience,
    expires_delta: timedelta,
) -> IssuedToken:
    now = datetime.now(timezone.utc)
    jti = uuid4().hex
    expires_at = now + expires_delta
    payload = {
        "sub": str(subject),
        "aud": audience,
        "typ": token_type,
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return IssuedToken(token=token, jti=jti, expires_at=expires_at)
