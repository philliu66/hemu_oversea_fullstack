import base64
import io
import random
import string
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import bad_request
from app.core.security import Audience
from app.models.captcha import Captcha
from app.schemas.auth import CaptchaResponse

# 排除易混淆字符：0/O、1/I/l
_CAPTCHA_ALPHABET = "".join(
    ch for ch in (string.ascii_uppercase + string.digits) if ch not in {"0", "O", "1", "I"}
)


def create_captcha(db: Session, *, audience: Audience) -> CaptchaResponse:
    code = _random_code(settings.CAPTCHA_LENGTH)
    captcha_id = uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.CAPTCHA_EXPIRE_SECONDS)

    db.add(
        Captcha(
            captcha_id=captcha_id,
            code=code,
            audience=audience,
            expires_at=expires_at,
        )
    )
    db.commit()

    return CaptchaResponse(
        captcha_id=captcha_id,
        image_base64=_render_image_base64(code),
        expires_in=settings.CAPTCHA_EXPIRE_SECONDS,
    )


def verify_captcha(
    db: Session,
    *,
    captcha_id: str,
    code: str,
    audience: Audience,
) -> None:
    """校验验证码：成功后标记已用。供后续登录接口调用。"""
    row = db.scalar(select(Captcha).where(Captcha.captcha_id == captcha_id))
    now = datetime.now(timezone.utc)

    if row is None or row.audience != audience:
        raise bad_request("验证码错误")
    if row.used_at is not None:
        raise bad_request("验证码错误")
    if _as_utc(row.expires_at) <= now:
        raise bad_request("验证码错误")

    # 一经校验即作废并落库，避免请求失败回滚后同一验证码可重试
    row.used_at = now
    matched = row.code.upper() == (code or "").strip().upper()
    db.commit()
    if not matched:
        raise bad_request("验证码错误")


def _random_code(length: int) -> str:
    return "".join(random.choices(_CAPTCHA_ALPHABET, k=length))


def _load_captcha_font(size: int = 32) -> ImageFont.ImageFont:
    """优先用系统 TrueType 大字号；找不到再退回 Pillow 默认可缩放字体。"""
    candidates = [
        "arial.ttf",
        "Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _render_image_base64(code: str) -> str:
    width, height = 160, 56
    image = Image.new("RGB", (width, height), color=(245, 247, 250))
    draw = ImageDraw.Draw(image)
    font = _load_captcha_font(32)

    for _ in range(6):
        start = (random.randint(0, width), random.randint(0, height))
        end = (random.randint(0, width), random.randint(0, height))
        draw.line([start, end], fill=(180, 190, 200), width=1)

    for _ in range(60):
        xy = (random.randint(0, width - 1), random.randint(0, height - 1))
        draw.point(xy, fill=(random.randint(120, 200),) * 3)

    slot = width / (len(code) + 1)
    for index, char in enumerate(code):
        bbox = font.getbbox(char)
        char_w = bbox[2] - bbox[0]
        char_h = bbox[3] - bbox[1]
        x = int(slot * (index + 1) - char_w / 2)
        y = random.randint(max(2, (height - char_h) // 2 - 4), max(2, (height - char_h) // 2 + 4))
        draw.text(
            (x, y),
            char,
            fill=(random.randint(20, 80), random.randint(20, 80), random.randint(20, 80)),
            font=font,
        )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
