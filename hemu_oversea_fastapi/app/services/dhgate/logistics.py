"""物流相关 API 封装（对接官方 Logistics API 后在此扩展）。"""

from __future__ import annotations

from app.core.errors import bad_request
from app.services.dhgate.client import DhgateClient


def list_logistics_methods(client: DhgateClient) -> dict:
    """物流方式列表（待对接官方 method）。"""
    raise bad_request(
        "敦煌物流接口尚未对接：请在 app/services/dhgate/logistics.py 中配置官方 method"
    )
