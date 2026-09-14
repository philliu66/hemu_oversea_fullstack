"""店铺类型 → 平台适配器注册表。"""

from __future__ import annotations

from app.core.errors import bad_request
from app.core.store_types import StoreType
from app.services.platforms.base import PlatformAdapter
from app.services.platforms.dhgate.adapter import DhgatePlatformAdapter
from app.services.platforms.tiktok.adapter import TiktokPlatformAdapter

_ADAPTERS: dict[str, PlatformAdapter] = {
    StoreType.DHGATE.value: DhgatePlatformAdapter(),
    StoreType.TIKTOK.value: TiktokPlatformAdapter(),
}


def get_adapter(store_type: str) -> PlatformAdapter:
    adapter = _ADAPTERS.get(store_type)
    if adapter is None:
        raise bad_request(f"不支持的店铺平台类型: {store_type}")
    return adapter
