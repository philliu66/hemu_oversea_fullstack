from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.deps import Pagination
from app.core.errors import conflict, not_found
from app.core.store_types import StoreType
from app.models.aftersale_template_dh import AftersaleTemplateDh
from app.models.shipping_template_dh import ShippingTemplateDh
from app.models.store import Store
from app.schemas.common import PageData
from app.schemas.store import (
    StoreAftersaleTemplatePublic,
    StoreDetailPublic,
    StorePublic,
    StoreShippingTemplatePublic,
)
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


def _is_aftersale_deleted_status(status: str | None) -> bool:
    if status is None:
        return False
    return str(status).strip() in {"0", "false", "False"}


def list_store_aftersale_templates(
    db: Session, store_id: int
) -> list[StoreAftersaleTemplatePublic]:
    """查询店铺售后模板，数据来自本地 aftersale_template_dh（排除已删除）。"""
    _get_alive_store(db, store_id)
    rows = db.scalars(
        select(AftersaleTemplateDh)
        .where(AftersaleTemplateDh.store_id == store_id)
        .order_by(AftersaleTemplateDh.id.asc())
    ).all()
    return [
        StoreAftersaleTemplatePublic(
            after_sale_template_id=row.after_sale_template_id,
            name=row.name,
            if_template_default=row.if_template_default,
        )
        for row in rows
        if not _is_aftersale_deleted_status(row.status)
    ]


def list_store_shipping_templates(
    db: Session, store_id: int
) -> list[StoreShippingTemplatePublic]:
    """查询店铺物流（运费）模板，数据来自本地 shipping_template_dh。"""
    _get_alive_store(db, store_id)
    rows = db.scalars(
        select(ShippingTemplateDh)
        .where(ShippingTemplateDh.store_id == store_id)
        .order_by(ShippingTemplateDh.id.asc())
    ).all()
    return [
        StoreShippingTemplatePublic(
            shipping_model_id=row.shipping_temp_id,
            name=row.model_name,
            model_type=row.model_type,
        )
        for row in rows
    ]
