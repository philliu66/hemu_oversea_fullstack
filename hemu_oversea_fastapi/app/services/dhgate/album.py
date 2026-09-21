"""敦煌相册 / 产品图片 API。

文档：
- dh.album.img.upload$2.1（卖家上传产品图片）
  https://open.dhgate.com/docs/api/detail/c5d30420d69846c4baa7cba43d2ac03b
"""

from __future__ import annotations

import base64
import logging
import random
import time
from io import BytesIO
from typing import Any

import httpx
from PIL import Image, ImageEnhance, UnidentifiedImageError

from app.core.errors import bad_request
from app.services.dhgate.client import DhgateClient
from app.services.dhgate.items import get_item

logger = logging.getLogger("app")

_DH_IMAGE_PREFIX = "http://image.dhgate.com/"
_UPLOAD_TIMEOUT_SECONDS = 60.0
_DOWNLOAD_TIMEOUT_SECONDS = 30.0
_MAX_IMAGE_BYTES = 2 * 1024 * 1024
_DEFAULT_SITE_ID = "EN"


def build_dh_image_url(img_url: str | None) -> str | None:
    """相对路径补前缀 http://image.dhgate.com/；已是完整 URL 则原样返回。"""
    if img_url is None:
        return None
    text = str(img_url).strip()
    if not text:
        return None
    if text.startswith(("http://", "https://")):
        return text
    return f"{_DH_IMAGE_PREFIX}{text.lstrip('/')}"


def upload_album_image(
    client: DhgateClient,
    *,
    img_base64: str,
    img_name: str,
    fun_type: str = "albu",
) -> dict[str, Any]:
    """
    上传产品图片。

    method: dh.album.img.upload
    version: 2.1
    仅支持 POST；imgBase64 限制 2MB。
    """
    name = str(img_name or "").strip()
    payload = str(img_base64 or "").strip()
    if not name:
        raise bad_request("imgName 不能为空")
    if not payload:
        raise bad_request("imgBase64 不能为空")
    return client.call(
        "dh.album.img.upload",
        version="2.1",
        params={
            "funType": fun_type or "albu",
            "imgName": name,
            "imgBase64": payload,
        },
        http_method="POST",
        timeout=_UPLOAD_TIMEOUT_SECONDS,
    )


def upload_product_image(
    client: DhgateClient,
    *,
    image_bytes: bytes,
    image_filename: str | None = None,
) -> dict[str, Any]:
    """将本地图片文件上传到敦煌相册，返回不加前缀的图片信息。"""
    if not image_bytes:
        raise bad_request("上传文件为空")
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise bad_request("图片超过 2MB，无法上传敦煌相册")
    img_name = _ensure_image_filename(image_filename or "upload.jpg")
    img_b64 = base64.b64encode(image_bytes).decode("ascii")
    uploaded = upload_album_image(
        client,
        img_base64=img_b64,
        img_name=img_name,
    )
    if not isinstance(uploaded, dict):
        raise bad_request("上传成功但返回格式异常")
    result = _img_public(
        img_url=uploaded.get("imgUrl"),
        img_md5=uploaded.get("imgMd5"),
        img_type=uploaded.get("type"),
    )
    if not result.get("img_url"):
        raise bad_request("上传成功但未返回 imgUrl")
    return result


def tweak_and_upload_main_image(
    client: DhgateClient,
    *,
    item_code: str | None = None,
    image_bytes: bytes | None = None,
    image_filename: str | None = None,
    site_id: str = _DEFAULT_SITE_ID,
) -> dict[str, Any]:
    """
    取参考主图 → Pillow 微调防重复 → dh.album.img.upload。

    item_code 有值时：拉详情第一张图作为原主图，忽略上传文件。
    """
    code = str(item_code or "").strip()
    original_image_url: str | None = None
    source_name = image_filename or "main.jpg"

    if code:
        original_image_url, image_bytes = _load_main_image_from_item(
            client,
            item_code=code,
            site_id=site_id,
        )
        source_name = f"tweak_{code}.jpg"
    elif not image_bytes:
        raise bad_request("请上传 imgBase64 文件，或传入 item_code 以使用商品第一张主图")

    tweaked_bytes = tweak_image_bytes(image_bytes)
    img_name = _ensure_image_filename(source_name)
    img_b64 = base64.b64encode(tweaked_bytes).decode("ascii")
    uploaded = upload_album_image(
        client,
        img_base64=img_b64,
        img_name=img_name,
    )
    new_image_url = build_dh_image_url(
        str(uploaded.get("imgUrl") or "") if isinstance(uploaded, dict) else None
    )
    return {
        "upload": uploaded,
        "original_image_url": original_image_url,
        "new_image_url": new_image_url,
    }


def _as_relative_img_url(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    for prefix in (
        "https://image.dhgate.com/",
        "http://image.dhgate.com/",
        "https://image.dhgate.com",
        "http://image.dhgate.com",
    ):
        if text.startswith(prefix):
            text = text[len(prefix) :].lstrip("/")
            break
    return text or None


def _img_public(
    *,
    img_url: Any = None,
    img_md5: Any = None,
    img_type: Any = None,
) -> dict[str, str | None]:
    md5 = str(img_md5).strip() if img_md5 not in (None, "") else None
    kind = str(img_type).strip() if img_type not in (None, "") else None
    return {
        "img_url": _as_relative_img_url(img_url),
        "img_md5": md5 or None,
        "type": kind or None,
    }


def tweak_product_image(
    client: DhgateClient,
    *,
    image_url: str | None = None,
    image_bytes: bytes | None = None,
    image_filename: str | None = None,
    original_img_url: str | None = None,
    original_img_md5: str | None = None,
    original_type: str | None = None,
) -> dict[str, Any]:
    """微调并上传产品图，返回不加前缀的原图 / 微调后图片信息。"""
    source_url = str(image_url or original_img_url or "").strip() or None
    if source_url:
        result = tweak_and_upload_from_url(
            client,
            image_url=source_url,
            image_filename=image_filename,
        )
    elif image_bytes:
        result = tweak_and_upload_main_image(
            client,
            image_bytes=image_bytes,
            image_filename=image_filename,
        )
    else:
        raise bad_request("请上传 img_base64 文件，或传入 img_url")

    uploaded = result.get("upload") if isinstance(result.get("upload"), dict) else {}
    original = _img_public(
        img_url=original_img_url or source_url or result.get("original_image_url"),
        img_md5=original_img_md5,
        img_type=original_type,
    )
    tweaked = _img_public(
        img_url=uploaded.get("imgUrl"),
        img_md5=uploaded.get("imgMd5"),
        img_type=original_type or uploaded.get("type"),
    )
    if not tweaked.get("img_url"):
        raise bad_request("微调上传成功但未返回 imgUrl")
    return {"original": original, "tweaked": tweaked}


def tweak_and_upload_from_url(
    client: DhgateClient,
    *,
    image_url: str,
    image_filename: str | None = None,
) -> dict[str, Any]:
    """按已有主图 URL 下载 → 微调 → 上传，不重复调用 dh.item.get。"""
    original_url = build_dh_image_url(image_url)
    if not original_url:
        raise bad_request("主图 imgUrl 为空，无法微调上传")
    image_bytes = _download_image(original_url)
    result = tweak_and_upload_main_image(
        client,
        image_bytes=image_bytes,
        image_filename=image_filename or "tweak_main.jpg",
    )
    result["original_image_url"] = original_url
    return result


def tweak_image_bytes(image_bytes: bytes) -> bytes:
    """轻微调整亮度/对比度并扰动少量像素，降低主图 MD5 重复判定。"""
    if not image_bytes:
        raise bad_request("参考主图为空，无法微调")
    try:
        image = Image.open(BytesIO(image_bytes))
        image.load()
    except UnidentifiedImageError as exc:
        raise bad_request("无法识别参考主图，请上传 jpg/png 等常见图片") from exc

    if image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")
    elif image.mode == "L":
        image = image.convert("RGB")

    image = ImageEnhance.Brightness(image).enhance(1.008)
    image = ImageEnhance.Contrast(image).enhance(1.006)
    _nudge_pixels(image)
    return _encode_jpeg_under_limit(image)


def _load_main_image_from_item(
    client: DhgateClient,
    *,
    item_code: str,
    site_id: str,
) -> tuple[str, bytes]:
    detail = get_item(client, item_code=item_code, site_id=site_id)
    images = detail.get("itemImgList") if isinstance(detail, dict) else None
    if not isinstance(images, list) or not images:
        raise bad_request("商品详情没有 itemImgList，无法取第一张主图")
    first = images[0]
    if not isinstance(first, dict):
        raise bad_request("商品第一张主图格式异常")
    original_url = build_dh_image_url(str(first.get("imgUrl") or ""))
    if not original_url:
        raise bad_request("商品第一张主图 imgUrl 为空")
    return original_url, _download_image(original_url)


def _download_image(url: str) -> bytes:
    try:
        response = httpx.get(url, timeout=_DOWNLOAD_TIMEOUT_SECONDS, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise bad_request(f"下载原主图失败: {exc}") from exc
    data = response.content
    if not data:
        raise bad_request("下载原主图失败：响应为空")
    return data


def _nudge_pixels(image: Image.Image) -> None:
    pixels = image.load()
    width, height = image.size
    if width <= 0 or height <= 0:
        return
    rng = random.Random(time.time_ns())
    count = min(24, width * height)
    for _ in range(count):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        pixel = pixels[x, y]
        if not isinstance(pixel, tuple) or len(pixel) < 3:
            continue
        red, green, blue = pixel[0], pixel[1], pixel[2]
        pixels[x, y] = (
            _clamp_color(red + rng.randint(-2, 2)),
            _clamp_color(green + rng.randint(-2, 2)),
            _clamp_color(blue + rng.randint(-2, 2)),
        )
    corner = pixels[width - 1, height - 1]
    if isinstance(corner, tuple) and len(corner) >= 3:
        pixels[width - 1, height - 1] = (
            _clamp_color(corner[0] + 1),
            corner[1],
            corner[2],
        )


def _clamp_color(value: int) -> int:
    return max(0, min(255, value))


def _encode_jpeg_under_limit(image: Image.Image) -> bytes:
    for quality in (93, 88, 82, 75, 65):
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        data = buffer.getvalue()
        if len(data) <= _MAX_IMAGE_BYTES:
            return data
    raise bad_request("微调后图片仍超过 2MB，无法上传敦煌相册")


def _ensure_image_filename(name: str) -> str:
    text = str(name or "").strip() or "main.jpg"
    lowered = text.lower()
    if lowered.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")):
        if not lowered.endswith((".jpg", ".jpeg")):
            stem = text.rsplit(".", 1)[0]
            return f"{stem or 'main'}.jpg"
        return text
    return f"{text}.jpg"
