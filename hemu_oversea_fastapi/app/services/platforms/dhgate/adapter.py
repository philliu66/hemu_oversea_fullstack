"""敦煌平台业务能力适配（对接 services.dhgate 底层 API）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.store_types import StoreType
from app.models.store import Store
from app.services.dhgate.client import DhgateClient
from app.services.dhgate.orders import list_orders as dhgate_list_orders
from app.services.dhgate.store_context import get_dhgate_store


class DhgatePlatformAdapter:
    platform = StoreType.DHGATE.value

    def _client(self, db: Session, store: Store) -> DhgateClient:
        store = get_dhgate_store(db, store.id)
        return DhgateClient(db, store)

    def list_orders(
        self,
        db: Session,
        store: Store,
        *,
        page_no: int,
        page_size: int,
        filters: dict[str, Any],
    ) -> dict[str, Any]:
        client = self._client(db, store)
        return dhgate_list_orders(
            client,
            page_no=page_no,
            page_size=page_size,
            **filters,
        )
