"""敦煌订单相关 API 封装。"""

from __future__ import annotations

from typing import Any

from app.core.errors import bad_request
from app.services.dhgate.client import DhgateClient


def list_orders(
    client: DhgateClient,
    *,
    page_no: int,
    page_size: int,
    **filters: Any,
) -> dict:
    """
    订单列表（对接官方 Order API 后在此实现 client.call）。

    示例（method / version 以官方文档为准）：
        return client.call(
            "dh.order.list.get",
            version="2.0",
            params={"pageNo": page_no, "pageSize": page_size, **filters},
            http_method="GET",
        )
    """
    raise bad_request(
        "敦煌订单列表接口尚未对接：请在 app/services/dhgate/orders.py 中配置官方 method"
    )
