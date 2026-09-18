"""物流相关 API。

文档：
- dh.shipping.template.list$2.0（卖家获取运费模版列表）
  https://open.dhgate.com/docs/api/detail/f0327a8a79684b138d324b30f39b6777
"""

from __future__ import annotations

from typing import Any

from app.services.dhgate.client import DhgateClient


def list_shipping_templates(client: DhgateClient) -> dict[str, Any]:
    """
    获取运费模板列表基础信息。

    method: dh.shipping.template.list
    version: 2.0
    官方无业务入参，仅公共参数；Java 示例为 POST。
    列表项 shippingTempId 对应发布入参 shippingModelId。
    """
    return client.call(
        "dh.shipping.template.list",
        version="2.0",
        params={},
        http_method="POST",
    )
