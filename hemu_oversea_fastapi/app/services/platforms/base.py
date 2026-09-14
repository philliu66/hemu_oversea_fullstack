"""多平台适配器抽象接口。"""

from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.models.store import Store


class PlatformAdapter(Protocol):
    """按店铺类型对接各平台 Open API 的统一能力面。"""

    platform: str

    def list_orders(
        self,
        db: Session,
        store: Store,
        *,
        page_no: int,
        page_size: int,
        filters: dict[str, Any],
    ) -> dict[str, Any]:
        """拉取平台侧订单列表（原始响应字段）。"""
