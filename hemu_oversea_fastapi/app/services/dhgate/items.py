"""敦煌 Product API（卖家产品）封装。

文档：
- dh.item.get$2.0（卖家获取产品详情）
  https://open.dhgate.com/docs/api/detail/7ef9fd6dd5374492babbe5a74894b343
"""

from __future__ import annotations

from typing import Any

from app.core.errors import bad_request
from app.services.dhgate.client import DhgateClient

_DEFAULT_SITE_ID = "EN"
_ALLOWED_SITE_IDS = frozenset({"EN", "RU", "ES", "ID"})


def get_item(
    client: DhgateClient,
    *,
    item_code: str,
    site_id: str = _DEFAULT_SITE_ID,
) -> dict[str, Any]:
    """
    获取卖家产品详情。

    method: dh.item.get
    version: 2.0

    item_code 通常来自 dh.item.list；site_id 默认 EN（英语站）。
    """
    code = str(item_code or "").strip()
    if not code:
        raise bad_request("item_code 不能为空（商品编码 itemCode）")

    site = str(site_id or _DEFAULT_SITE_ID).strip().upper() or _DEFAULT_SITE_ID
    if site not in _ALLOWED_SITE_IDS:
        raise bad_request("site_id 仅支持 EN / RU / ES / ID")

    return client.call(
        "dh.item.get",
        version="2.0",
        params={
            "itemCode": code,
            "siteId": site,
        },
        http_method="GET",
    )
