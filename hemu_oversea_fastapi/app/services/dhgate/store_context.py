"""敦煌店铺上下文：校验店铺类型与授权状态。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, not_found
from app.core.store_types import StoreType
from app.models.store import Store
from app.services.dhgate.client import DhgateClient
from app.services.dhgate.response import raise_reauth_required


def get_dhgate_store(db: Session, store_id: int) -> Store:
    store = db.get(Store, store_id)
    if store is None or store.is_deleted:
        raise not_found("店铺不存在")
    if store.store_type != StoreType.DHGATE.value:
        raise bad_request("当前店铺不是敦煌类型")
    if not store.access_token:
        raise raise_reauth_required("店铺未授权敦煌，请先完成授权")
    return store


def get_dhgate_store_by_identifier(db: Session, identifier: str) -> Store:
    key = str(identifier or "").strip()
    if not key:
        raise bad_request("store_identifier 不能为空")
    store = db.scalar(
        select(Store).where(
            Store.identifier == key,
            Store.deleted_at.is_(None),
        )
    )
    if store is None:
        raise not_found(f"店铺不存在：identifier={key}")
    if store.store_type != StoreType.DHGATE.value:
        raise bad_request("当前店铺不是敦煌类型")
    if not store.access_token:
        raise raise_reauth_required("店铺未授权敦煌，请先完成授权")
    return store


def get_dhgate_client(db: Session, store_id: int) -> DhgateClient:
    store = get_dhgate_store(db, store_id)
    return DhgateClient(db, store)


def get_dhgate_client_by_identifier(db: Session, identifier: str) -> DhgateClient:
    store = get_dhgate_store_by_identifier(db, identifier)
    return DhgateClient(db, store)
