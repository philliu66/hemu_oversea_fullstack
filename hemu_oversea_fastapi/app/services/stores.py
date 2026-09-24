from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.deps import Pagination
from app.core.errors import conflict, not_found
from app.core.store_types import StoreType
from app.models.store import Store
from app.schemas.common import PageData
from app.schemas.store import (
    StoreAftersaleTemplatePublic,
    StoreDetailPublic,
    StorePublic,
    StoreShippingTemplatePublic,
)
from app.services.dhgate.items import list_item_aftersale
from app.services.dhgate.logistics import list_shipping_templates
from app.services.dhgate.store_context import get_dhgate_client
from app.services.suppliers import get_supplier


def _get_alive_store(db: Session, store_id: int) -> Store:
    store = db.get(Store, store_id)
    if store is None or store.is_deleted:
        raise not_found("店铺不存在")
    return store


def _conflict_from_integrity(exc: IntegrityError) -> Exception:
    detail = str(exc.orig).lower() if exc.orig is not None else str(exc).lower()
    if "identifier" in detail:
        return conflict("店铺标识已存在")
    return conflict("店铺信息冲突")


def _to_public(store: Store) -> StorePublic:
    return StorePublic(
        id=store.id,
        supplier_id=store.supplier_id,
        store_type=store.store_type,
        name=store.name,
        identifier=store.identifier,
        oauth_status=store.oauth_status,
        refresh_token_expires_at=store.refresh_token_expires_at,
        created_by=store.creator.username if store.creator else None,
        updated_by=store.updater.username if store.updater else None,
        created_at=store.created_at,
        updated_at=store.updated_at,
    )


def _to_detail_public(store: Store) -> StoreDetailPublic:
    return StoreDetailPublic(
        id=store.id,
        supplier_id=store.supplier_id,
        store_type=store.store_type,
        name=store.name,
        identifier=store.identifier,
        account=store.account,
        password=store.password,
        oauth_status=store.oauth_status,
        refresh_token_expires_at=store.refresh_token_expires_at,
        created_by=store.creator.username if store.creator else None,
        updated_by=store.updater.username if store.updater else None,
        created_at=store.created_at,
        updated_at=store.updated_at,
    )


def _load_store_with_actors(db: Session, store_id: int) -> Store:
    store = db.scalar(
        select(Store)
        .options(
            joinedload(Store.creator),
            joinedload(Store.updater),
        )
        .where(Store.id == store_id, Store.deleted_at.is_(None))
    )
    if store is None:
        raise not_found("店铺不存在")
    return store


def create_store(
    db: Session,
    *,
    store_type: StoreType,
    name: str,
    identifier: str,
    account: str,
    password: str,
    actor_id: int,
    supplier_id: int,
) -> StorePublic:
    get_supplier(db, supplier_id)
    store = Store(
        supplier_id=supplier_id,
        store_type=store_type.value,
        name=name,
        identifier=identifier,
        account=account,
        password=password,
        created_by=actor_id,
        updated_by=actor_id,
    )
    db.add(store)
    try:
        db.commit()
        db.refresh(store)
    except IntegrityError as exc:
        db.rollback()
        raise _conflict_from_integrity(exc) from exc
    return _to_public(_load_store_with_actors(db, store.id))


def list_stores(
    db: Session,
    *,
    keyword: str | None,
    store_type: StoreType | None,
    supplier_id: int | None,
    pagination: Pagination,
) -> PageData[StorePublic]:
    filters = [Store.deleted_at.is_(None)]
    if keyword:
        pattern = f"%{keyword}%"
        filters.append(
            or_(
                Store.name.ilike(pattern),
                Store.identifier.ilike(pattern),
                Store.account.ilike(pattern),
            )
        )
    if store_type is not None:
        filters.append(Store.store_type == store_type.value)
    if supplier_id is not None:
        filters.append(Store.supplier_id == supplier_id)

    count_stmt = select(func.count()).select_from(Store).where(*filters)
    stmt = (
        select(Store)
        .options(
            joinedload(Store.creator),
            joinedload(Store.updater),
        )
        .where(*filters)
    )

    total = db.scalar(count_stmt) or 0
    rows = db.scalars(
        stmt.order_by(Store.id.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).unique().all()
    return PageData(
        items=[_to_public(row) for row in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def get_store(db: Session, store_id: int) -> Store:
    return _get_alive_store(db, store_id)


def get_store_detail(db: Session, store_id: int) -> StoreDetailPublic:
    return _to_detail_public(_load_store_with_actors(db, store_id))


def update_store(
    db: Session,
    *,
    store_id: int,
    actor_id: int,
    store_type: StoreType | None = None,
    name: str | None = None,
    identifier: str | None = None,
    account: str | None = None,
    password: str | None = None,
) -> StorePublic:
    store = _get_alive_store(db, store_id)
    if store_type is not None:
        store.store_type = store_type.value
    if name is not None:
        store.name = name
    if identifier is not None:
        store.identifier = identifier
    if account is not None:
        store.account = account
    if password is not None:
        store.password = password
    store.updated_by = actor_id
    try:
        db.commit()
        db.refresh(store)
    except IntegrityError as exc:
        db.rollback()
        raise _conflict_from_integrity(exc) from exc
    return _to_public(_load_store_with_actors(db, store.id))


def soft_delete_store(db: Session, *, store_id: int, actor_id: int) -> None:
    store = _get_alive_store(db, store_id)
    store.deleted_at = datetime.now(timezone.utc)
    store.updated_by = actor_id
    db.commit()


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_text(item: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        text = _as_text(item.get(key))
        if text:
            return text
    return None


def _is_aftersale_deleted(item: dict[str, Any]) -> bool:
    status = item.get("status")
    if status is None:
        return False
    return str(status).strip() in {"0", "false", "False"}


def list_store_aftersale_templates(
    db: Session, store_id: int
) -> list[StoreAftersaleTemplatePublic]:
    """查询店铺售后模板，数据来自 dh.item.aftersale.list。"""
    client = get_dhgate_client(db, store_id)
    data = list_item_aftersale(client)
    raw_list = data.get("afterSaleList") if isinstance(data, dict) else None
    if not isinstance(raw_list, list):
        return []
    templates: list[StoreAftersaleTemplatePublic] = []
    for item in raw_list:
        if not isinstance(item, dict) or _is_aftersale_deleted(item):
            continue
        template_id = _first_text(item, "afterSaleTemplateId")
        if not template_id:
            continue
        templates.append(
            StoreAftersaleTemplatePublic(
                after_sale_template_id=template_id,
                name=_first_text(item, "name", "templateName", "afterSaleTemplateName"),
                if_template_default=_first_text(item, "ifTemplateDefault"),
            )
        )
    return templates


def list_store_shipping_templates(
    db: Session, store_id: int
) -> list[StoreShippingTemplatePublic]:
    """查询店铺物流（运费）模板，数据来自 dh.shipping.template.list。"""
    client = get_dhgate_client(db, store_id)
    data = list_shipping_templates(client)
    raw_list = data.get("shippingModelList") if isinstance(data, dict) else None
    if not isinstance(raw_list, list):
        return []
    templates: list[StoreShippingTemplatePublic] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        template_id = _first_text(item, "shippingTempId", "shippingModelId")
        if not template_id:
            continue
        templates.append(
            StoreShippingTemplatePublic(
                shipping_model_id=template_id,
                name=_first_text(
                    item, "modelName", "shippingModelName", "name", "templateName"
                ),
                model_type=_first_text(item, "modelType"),
            )
        )
    return templates
