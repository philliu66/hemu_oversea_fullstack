"""多店铺执行与店铺范围解析。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, bad_request
from app.core.store_types import StoreType
from app.models.store import Store

T = TypeVar("T")


@dataclass
class StoreRunError:
    store_id: int
    store_name: str
    store_type: str
    message: str


@dataclass
class MultiStoreResult(Generic[T]):
    items: list[T] = field(default_factory=list)
    errors: list[StoreRunError] = field(default_factory=list)


def resolve_stores(
    db: Session,
    *,
    store_ids: list[int] | None,
    store_type: StoreType | None,
    require_oauth: bool = True,
) -> list[Store]:
    """按 ID 或类型筛选未删除店铺；可选要求已授权。"""
    filters = [Store.deleted_at.is_(None)]
    if store_ids:
        filters.append(Store.id.in_(store_ids))
    if store_type is not None:
        filters.append(Store.store_type == store_type.value)
    if require_oauth:
        filters.append(Store.access_token.isnot(None))

    stores = db.scalars(
        select(Store).where(*filters).order_by(Store.id.asc())
    ).all()
    return list(stores)


def resolve_stores_by_supplier(
    db: Session,
    *,
    supplier_id: int,
    store_type: StoreType | None = None,
    require_oauth: bool = True,
) -> list[Store]:
    """按 stores.supplier_id 筛选店铺。"""
    filters = [
        Store.deleted_at.is_(None),
        Store.supplier_id == supplier_id,
    ]
    if store_type is not None:
        filters.append(Store.store_type == store_type.value)
    if require_oauth:
        filters.append(Store.access_token.isnot(None))

    stores = db.scalars(
        select(Store).where(*filters).order_by(Store.id.asc())
    ).all()
    return list(stores)


def run_for_stores(
    db: Session,
    *,
    store_ids: list[int] | None,
    store_type: StoreType | None,
    worker: Callable[[Session, Store], T],
    require_oauth: bool = True,
    continue_on_error: bool = False,
) -> MultiStoreResult[T]:
    """
    对范围内每个店铺执行 worker。

    默认遇错即失败。批量场景由调用方循环单次接口，不在一次请求里跳过失败店铺。
    """
    stores = resolve_stores(
        db,
        store_ids=store_ids,
        store_type=store_type,
        require_oauth=require_oauth,
    )
    if not stores:
        raise bad_request("未找到符合条件的店铺")

    result = MultiStoreResult[T]()
    for store in stores:
        try:
            item = worker(db, store)
            result.items.append(item)
        except AppError as exc:
            if not continue_on_error:
                raise
            result.errors.append(
                StoreRunError(
                    store_id=store.id,
                    store_name=store.name,
                    store_type=store.store_type,
                    message=exc.message,
                )
            )
        except Exception as exc:
            if not continue_on_error:
                raise
            result.errors.append(
                StoreRunError(
                    store_id=store.id,
                    store_name=store.name,
                    store_type=store.store_type,
                    message=str(exc),
                )
            )
    return result
