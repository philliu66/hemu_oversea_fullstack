"""店铺授权链接分发：按 store_type 选择平台 OAuth 流程。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import bad_request, not_found
from app.core.store_types import StoreType
from app.models.store import Store
from app.services.dhgate import oauth as dhgate_oauth
from app.services import tiktok_oauth


def create_authorize_url(db: Session, *, store_id: int, actor_id: int) -> tuple[str, str]:
    """
    根据店铺类型生成授权链接。

    Returns:
        (authorize_url, store_type)
    """
    store = db.get(Store, store_id)
    if store is None or store.is_deleted:
        raise not_found("店铺不存在")

    store_type = store.store_type
    if store_type == StoreType.DHGATE.value:
        url = dhgate_oauth.create_authorize_url_for_store(
            db,
            store=store,
            actor_id=actor_id,
        )
        return url, store_type

    if store_type == StoreType.TIKTOK.value:
        url = tiktok_oauth.create_authorize_url_for_store(
            db,
            store=store,
            actor_id=actor_id,
        )
        return url, store_type

    raise bad_request(f"不支持的店铺类型: {store_type}")
