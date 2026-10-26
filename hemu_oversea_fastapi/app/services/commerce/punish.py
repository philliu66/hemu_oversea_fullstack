"""敦煌多店铺处罚信息汇总。

按供应商下单店或多店调用敦煌接口，汇总：
1. dh.punish.list.get — 平台处罚
2. dh.punish.brand.list.get thirdType=brand — 品牌商第三方投诉
3. dh.punish.brand.list.get thirdType=other — 其他第三方投诉
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.errors import bad_request
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
    """单店三类处罚查询结果。"""

    store_id: int
    store_name: str
    store_identifier: str
    punish: dict[str, Any] | None = None
    punish_brand: dict[str, Any] | None = None
    punish_other: dict[str, Any] | None = None
    call_errors: list[StorePunishCallError] = field(default_factory=list)


@dataclass
class StoresPunishSummary:
    """所有店铺三类处罚列表的合并汇总。"""

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
    # 联调用：各店敦煌原始调用明细（含 store_id / store_identifier）
    raw_calls: list[dict[str, Any]] = field(default_factory=list)


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


def _annotate_raw_calls(
    call_history: list[dict[str, Any]],
    *,
    store_id: int,
    store_identifier: str,
) -> list[dict[str, Any]]:
    return [
        {
            **item,
            "store_id": store_id,
            "store_identifier": store_identifier,
        }
        for item in call_history
    ]


def _fetch_store_punish(
    db: Session,
    store: Store,
    *,
    start_date: str,
    end_date: str,
    page_no: int,
    page_size: int,
) -> tuple[StorePunishResult, list[dict[str, Any]]]:
    client = get_dhgate_client(db, store.id)
    client.clear_call_history()
    result = StorePunishResult(
        store_id=store.id,
        store_name=store.name,
        store_identifier=store.identifier,
    )

    result.punish = list_punish(
        client,
        start_date=start_date,
        end_date=end_date,
        page_no=page_no,
        page_size=page_size,
    )
    result.punish_brand = list_punish_brand(
        client,
        third_type="brand",
        page_no=page_no,
        page_size=page_size,
    )
    result.punish_other = list_punish_brand(
        client,
        third_type="other",
        page_no=page_no,
        page_size=page_size,
    )

    raw_calls = _annotate_raw_calls(
        client.call_history,
        store_id=store.id,
        store_identifier=store.identifier,
    )
    return result, raw_calls


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
    汇总单店或多店的处罚信息（不含纠纷订单）。

    - supplier_id 必传
    - store_id 选传：传入则只查该店，不传则查该供应商下全部已授权敦煌店铺
    - page_no / page_size：三类处罚接口共用同一分页（默认 1 / 100）

    每个店铺调用：
    1. dh.punish.list.get（起止日期由 query_days 推算）→ stores[].punish
    2. dh.punish.brand.list.get thirdType=brand → stores[].punish_brand
    3. dh.punish.brand.list.get thirdType=other → stores[].punish_other

    stores_summary.punish_list：合并三类处罚的 punishInfoList（附 store_id / store_identifier）。
    任一敦煌调用失败则整次汇总失败。
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
        store_result, raw_calls = _fetch_store_punish(
            db,
            store,
            start_date=start_date,
            end_date=end_date,
            page_no=page_no,
            page_size=page_size,
        )
        summary.stores.append(store_result)
        summary.raw_calls.extend(raw_calls)

    summary.stores_summary = _build_stores_summary(summary.stores)
    return summary
