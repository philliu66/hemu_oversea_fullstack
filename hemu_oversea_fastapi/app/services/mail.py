"""通用邮件发送服务（阿里云邮件推送 DirectMail）。

业务侧只依赖本模块的 send_email，不直接耦合阿里云 SDK。
鉴权与发信地址等均从环境变量 / Settings 读取，禁止在代码中硬编码密钥。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from alibabacloud_dm20151123 import models as dm_models
from alibabacloud_dm20151123.client import Client as DmClient
from alibabacloud_tea_openapi import models as open_api_models
from Tea.exceptions import TeaException

from app.core.config import settings
from app.core.errors import bad_request

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MailSendResult:
    """邮件发送结果（供业务与 API 使用）。"""

    ok: bool
    to: str
    subject: str
    request_id: str | None = None
    env_id: str | None = None


def _normalize_recipients(to: str | list[str]) -> str:
    if isinstance(to, str):
        parts = [p.strip() for p in to.split(",")]
    else:
        parts = [str(p).strip() for p in to]
    recipients = [p for p in parts if p]
    if not recipients:
        raise bad_request("收件人不能为空")
    if len(recipients) > 100:
        raise bad_request("单次收件人最多 100 个")
    return ",".join(recipients)


def _require_dm_settings() -> tuple[str, str, str]:
    access_key_id = (settings.ALIYUN_RAM_ACCESS_KEY_ID or "").strip()
    access_key_secret = (settings.ALIYUN_RAM_ACCESS_KEY_SECRET or "").strip()
    account_name = (settings.ALIYUN_DM_ACCOUNT_NAME or "").strip()
    if not access_key_id or not access_key_secret:
        raise bad_request(
            "未配置阿里云 RAM 密钥：请设置环境变量 "
            "ALIYUN_RAM_ACCESS_KEY_ID / ALIYUN_RAM_ACCESS_KEY_SECRET"
        )
    if not account_name:
        raise bad_request(
            "未配置发信地址：请设置环境变量 ALIYUN_DM_ACCOUNT_NAME"
        )
    return access_key_id, access_key_secret, account_name


def _create_dm_client(access_key_id: str, access_key_secret: str) -> DmClient:
    config = open_api_models.Config(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
    )
    config.endpoint = (settings.ALIYUN_DM_ENDPOINT or "dm.aliyuncs.com").strip()
    region = (settings.ALIYUN_DM_REGION_ID or "").strip()
    if region:
        config.region_id = region
    return DmClient(config)


def send_email(
    *,
    to: str | list[str],
    subject: str,
    html: str | None = None,
    text: str | None = None,
    from_alias: str | None = None,
    tag_name: str | None = None,
) -> MailSendResult:
    """
    通过阿里云 DirectMail SingleSendMail 发送单封邮件。

    - html / text 至少传一个且非空
    - 发信地址、密钥来自 Settings（环境变量）
    """
    recipients = _normalize_recipients(to)
    subject_text = (subject or "").strip()
    if not subject_text:
        raise bad_request("邮件主题不能为空")
    if len(subject_text) > 100:
        raise bad_request("邮件主题长度不能超过 100 个字符")

    html_body = (html or "").strip() or None
    text_body = (text or "").strip() or None
    if not html_body and not text_body:
        raise bad_request("html 与 text 至少传一个且非空")

    access_key_id, access_key_secret, account_name = _require_dm_settings()
    alias = (from_alias or "").strip() or None
    tag = (tag_name or "").strip() or None

    request = dm_models.SingleSendMailRequest(
        account_name=account_name,
        address_type=int(settings.ALIYUN_DM_ADDRESS_TYPE),
        reply_to_address=bool(settings.ALIYUN_DM_REPLY_TO_ADDRESS),
        to_address=recipients,
        subject=subject_text,
        html_body=html_body,
        text_body=text_body,
        from_alias=alias,
        tag_name=tag,
    )

    client = _create_dm_client(access_key_id, access_key_secret)
    try:
        response = client.single_send_mail(request)
    except TeaException as exc:
        message = getattr(exc, "message", None) or str(exc)
        data = getattr(exc, "data", None)
        recommend = None
        if isinstance(data, dict):
            recommend = data.get("Recommend")
            message = data.get("Message") or message
        logger.warning(
            "DirectMail send failed: %s recommend=%s",
            message,
            recommend,
        )
        raise bad_request(f"邮件发送失败：{message}") from exc
    except Exception as exc:  # noqa: BLE001 — 统一转为业务可读错误
        logger.exception("DirectMail unexpected error")
        raise bad_request(f"邮件发送失败：{exc}") from exc

    body = getattr(response, "body", None)
    request_id = getattr(body, "request_id", None) if body is not None else None
    env_id = getattr(body, "env_id", None) if body is not None else None
    if request_id is None:
        request_id = getattr(response, "request_id", None)

    logger.info(
        "DirectMail sent ok to=%s subject=%s request_id=%s",
        recipients,
        subject_text,
        request_id,
    )
    return MailSendResult(
        ok=True,
        to=recipients,
        subject=subject_text,
        request_id=str(request_id) if request_id is not None else None,
        env_id=str(env_id) if env_id is not None else None,
    )
