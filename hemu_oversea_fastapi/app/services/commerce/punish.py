"""敦煌多店铺处罚信息汇总。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.errors import AppError, bad_request
from app.core.store_types import StoreType
from app.models.store import Store
from app.services.commerce.multi_store import (
    StoreRunError,
    resolve_stores,
    resolve_stores_by_supplier,
)
from app.services.dhgate.base import list_punish, list_punish_brand
from app.services.dhgate.store_context import get_dhgate_client
from app.services.suppliers import get_supplier

_BJ = ZoneInfo("Asia/Shanghai")
_DEFAULT_PAGE_NO = 1
_DEFAULT_PAGE_SIZE = 100
_MAX_QUERY_DAYS = 365


@dataclass
class StorePunishCallError:
    source: str
    message: str


@dataclass
class StorePunishResult:
    store_id: int
    store_name: str
    store_identifier: str
    punish: dict[str, Any] | None = None
    punish_brand: dict[str, Any] | None = None
    punish_other: dict[str, Any] | None = None
    call_errors: list[StorePunishCallError] = field(default_factory=list)


@dataclass
class StoresPunishSummary:
    """所有店铺三种处罚列表的合并汇总。"""

    punish_list: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SupplierPunishSummary:
    supplier_id: int
    query_days: int
    start_date: str
    end_date: str
    page_no: int
    page_size: int
    stores: list[StorePunishResult] = field(default_factory=list)
    stores_summary: StoresPunishSummary = field(default_factory=StoresPunishSummary)
    errors: list[StoreRunError] = field(default_factory=list)


def _date_range_by_days(query_days: int) -> tuple[str, str]:
    """
    按查询天数计算起止日期（北京时间，含当天）。

    例：query_days=7 → end=今天，start=今天往前共 7 天（含今天）。
    """
    if query_days < 1:
        raise bad_request("query_days 必须大于等于 1")
    if query_days > _MAX_QUERY_DAYS:
        raise bad_request(f"query_days 不能超过 {_MAX_QUERY_DAYS}（敦煌接口时间跨度上限约 1 年）")

    today = datetime.now(_BJ).date()
    start = today - timedelta(days=query_days - 1)
    return start.isoformat(), today.isoformat()


def _safe_call(source: str, fn) -> tuple[dict[str, Any] | None, StorePunishCallError | None]:
    try:
        return fn(), None
    except AppError as exc:
        return None, StorePunishCallError(source=source, message=exc.message)
    except Exception as exc:
        return None, StorePunishCallError(source=source, message=str(exc))


def _fetch_store_punish(
    db: Session,
    store: Store,
    *,
    start_date: str,
    end_date: str,
    page_no: int,
    page_size: int,
) -> StorePunishResult:
    client = get_dhgate_client(db, store.id)
    result = StorePunishResult(
        store_id=store.id,
        store_name=store.name,
        store_identifier=store.identifier,
    )

    punish, err = _safe_call(
        "punish",
        lambda: list_punish(
            client,
            start_date=start_date,
            end_date=end_date,
            page_no=page_no,
            page_size=page_size,
        ),
    )
    result.punish = punish
    if err:
        result.call_errors.append(err)

    brand, err = _safe_call(
        "punish_brand",
        lambda: list_punish_brand(
            client,
            third_type="brand",
            page_no=page_no,
            page_size=page_size,
        ),
    )
    result.punish_brand = brand
    if err:
        result.call_errors.append(err)

    other, err = _safe_call(
        "punish_other",
        lambda: list_punish_brand(
            client,
            third_type="other",
            page_no=page_no,
            page_size=page_size,
        ),
    )
    result.punish_other = other
    if err:
        result.call_errors.append(err)

    return result


def _extract_punish_info_list(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not payload:
        return []
    items = payload.get("punishInfoList")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _build_stores_summary(stores: list[StorePunishResult]) -> StoresPunishSummary:
    """合并各店铺 punish / punish_brand / punish_other 中的 punishInfoList。"""
    punish_list: list[dict[str, Any]] = []
    for store in stores:
        for payload in (store.punish, store.punish_brand, store.punish_other):
            for item in _extract_punish_info_list(payload):
                punish_list.append(
                    {
                        **item,
                        "store_id": store.store_id,
                        "store_identifier": store.store_identifier,
                    }
                )
    return StoresPunishSummary(punish_list=punish_list)


def _resolve_punish_stores(
    db: Session,
    *,
    supplier_id: int,
    store_id: int | None,
) -> list[Store]:
    """
    解析处罚汇总的店铺范围。

    - 传 store_id：仅查该店铺（须属于 supplier_id）
    - 不传 store_id：查该供应商下全部已授权敦煌店铺
    """
    get_supplier(db, supplier_id)

    if store_id is not None:
        stores = resolve_stores(
            db,
            store_ids=[store_id],
            store_type=StoreType.DHGATE,
            require_oauth=True,
        )
        if not stores:
            raise bad_request("未找到已授权的敦煌店铺")
        store = stores[0]
        if store.supplier_id != supplier_id:
            raise bad_request("店铺不属于该供应商")
        return stores

    stores = resolve_stores_by_supplier(
        db,
        supplier_id=supplier_id,
        store_type=StoreType.DHGATE,
        require_oauth=True,
    )
    if not stores:
        raise bad_request("该供应商下未找到已授权的敦煌店铺")
    return stores


def summarize_supplier_punish(
    db: Session,
    *,
    supplier_id: int,
    query_days: int,
    store_id: int | None = None,
    page_no: int = _DEFAULT_PAGE_NO,
    page_size: int = _DEFAULT_PAGE_SIZE,
) -> SupplierPunishSummary:
    """
    汇总处罚信息。

    - supplier_id 必传
    - store_id 选传：传入则只查该店，不传则查该供应商下全部已授权敦煌店铺

    每个店铺调用：
    1. dh.punish.list.get（起止日期由 query_days 推算）
    2. dh.punish.brand.list.get thirdType=brand
    3. dh.punish.brand.list.get thirdType=other
    """
    stores = _resolve_punish_stores(
        db,
        supplier_id=supplier_id,
        store_id=store_id,
    )
    start_date, end_date = _date_range_by_days(query_days)

    summary = SupplierPunishSummary(
        supplier_id=supplier_id,
        query_days=query_days,
        start_date=start_date,
        end_date=end_date,
        page_no=page_no,
        page_size=page_size,
    )

    for store in stores:
        try:
            summary.stores.append(
                _fetch_store_punish(
                    db,
                    store,
                    start_date=start_date,
                    end_date=end_date,
                    page_no=page_no,
                    page_size=page_size,
                )
            )
        except AppError as exc:
            summary.errors.append(
                StoreRunError(
                    store_id=store.id,
                    store_name=store.name,
                    store_type=store.store_type,
                    message=exc.message,
                )
            )
        except Exception as exc:
            summary.errors.append(
                StoreRunError(
                    store_id=store.id,
                    store_name=store.name,
                    store_type=store.store_type,
                    message=str(exc),
                )
            )

    summary.stores_summary = _build_stores_summary(summary.stores)
    return summary
