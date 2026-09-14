import logging
from typing import Annotated

from fastapi import Header
from pydantic import BaseModel

logger = logging.getLogger("app")


class CommonHeaders(BaseModel):
    sign: str | None = None
    timestamp: str | None = None
    channel: int | None = None


def get_common_headers(
    sign: Annotated[str | None, Header(alias="X-Sign")] = None,
    timestamp: Annotated[str | None, Header(alias="X-Timestamp")] = None,
    channel: Annotated[str | None, Header(alias="X-Channel")] = None,
) -> CommonHeaders:
    """解析公共 Header。当前全部放行，只打日志；校验规则以后再补。"""
    parsed_channel: int | None = None
    if channel is not None and channel.strip() != "":
        try:
            parsed_channel = int(channel)
        except ValueError:
            logger.info("common headers invalid channel=%s", channel)

    headers = CommonHeaders(sign=sign, timestamp=timestamp, channel=parsed_channel)
    logger.info(
        "common headers sign=%s timestamp=%s channel=%s",
        headers.sign,
        headers.timestamp,
        headers.channel,
    )
    return headers
