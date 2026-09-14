"""TikTok 平台适配（预留）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import bad_request
from app.core.store_types import StoreType
from app.models.store import Store


class TiktokPlatformAdapter:
    platform = StoreType.TIKTOK.value

    def list_orders(
        self,
        db: Session,
        store: Store,
        *,
        page_no: int,
        page_size: int,
        filters: dict[str, Any],
    ) -> dict[str, Any]:
        raise bad_request("TikTok 订单接口暂未开放")
