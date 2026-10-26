"""敦煌多店铺纠纷订单汇总。

v1：dh.dispute.processing.list — 进行中纠纷订单
v2：dh.order.disputeopen.list — 开启中的纠纷订单
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import bad_request
from app.core.store_types import StoreType
from app.models.store import Store
from app.services.commerce.multi_store import (
    StoreRunError,
    resolve_stores,
    resolve_stores_by_supplier,
)
from app.services.dhgate.orders import list_dispute_processing, list_order_dispute_open
from app.services.dhgate.store_context import get_dhgate_client
from app.services.suppliers import get_supplier

_DEFAULT_PAGE_NO = 1
_DEFAULT_PAGE_SIZE = 100


@dataclass
class StoreDisputeCallError:
    source: str
    message: str


@dataclass
class StoreDisputeProcessingResult:
    """单店进行中纠纷（v1）查询结果。"""

    store_id: int
    store_name: str
    store_identifier: str
    dispute_processing: dict[str, Any] | None = None
    call_errors: list[StoreDisputeCallError] = field(default_factory=list)


@dataclass
class StoresDisputeProcessingSummary:
    """所有店铺进行中纠纷的合并汇总。"""

    dispute_processing_list: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SupplierDisputeProcessingSummary:
    supplier_id: int
    dispute_status: str
    page_num: int
    page_size: int
    start_time: str | None = None
    end_time: str | None = None
    stores: list[StoreDisputeProcessingResult] = field(default_factory=list)
    stores_summary: StoresDisputeProcessingSummary = field(
        default_factory=StoresDisputeProcessingSummary
    )
    errors: list[StoreRunError] = field(default_factory=list)
    raw_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class StoreDisputeOpenResult:
    """单店纠纷开启订单（v2）查询结果。"""

    store_id: int
    store_name: str
    store_identifier: str
    dispute_open: dict[str, Any] | None = None
    call_errors: list[StoreDisputeCallError] = field(default_factory=list)


@dataclass
class StoresDisputeOpenSummary:
    """所有店铺纠纷开启订单的合并汇总。"""

    dispute_open_list: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SupplierDisputeOpenSummary:
    supplier_id: int
    page_no: int
    page_size: int
    stores: list[StoreDisputeOpenResult] = field(default_factory=list)
    stores_summary: StoresDisputeOpenSummary = field(
        default_factory=StoresDisputeOpenSummary
    )
    errors: list[StoreRunError] = field(default_factory=list)
    # 联调用：各店敦煌原始调用明细（含 store_id / store_identifier）
    raw_calls: list[dict[str, Any]] = field(default_factory=list)


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


def _extract_list_items(
    payload: dict[str, Any] | None,
    key: str,
) -> list[dict[str, Any]]:
    if not payload:
        return []
    items = payload.get(key)
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _resolve_dispute_stores(
    db: Session,
    *,
    supplier_id: int,
    store_id: int | None,
) -> list[Store]:
    """
    解析纠纷汇总的店铺范围。

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


def _fetch_store_dispute_processing(
    db: Session,
    store: Store,
    *,
    dispute_status: str,
    page_num: int,
    page_size: int,
    start_time: str | None,
    end_time: str | None,
) -> tuple[StoreDisputeProcessingResult, list[dict[str, Any]]]:
    client = get_dhgate_client(db, store.id)
    client.clear_call_history()
    result = StoreDisputeProcessingResult(
        store_id=store.id,
        store_name=store.name,
        store_identifier=store.identifier,
    )

    result.dispute_processing = list_dispute_processing(
        client,
        dispute_status=dispute_status,
        page_num=page_num,
        page_size=page_size,
        start_time=start_time,
        end_time=end_time,
    )

    raw_calls = _annotate_raw_calls(
        client.call_history,
        store_id=store.id,
        store_identifier=store.identifier,
    )
    return result, raw_calls


def _build_processing_stores_summary(
    stores: list[StoreDisputeProcessingResult],
) -> StoresDisputeProcessingSummary:
    """合并各店铺 dispute_processing 中的 disputeList。"""
    dispute_processing_list: list[dict[str, Any]] = []
    for store in stores:
        for item in _extract_list_items(store.dispute_processing, "disputeList"):
            dispute_processing_list.append(
                {
                    **item,
                    "store_id": store.store_id,
                    "store_identifier": store.store_identifier,
                }
            )
    return StoresDisputeProcessingSummary(
        dispute_processing_list=dispute_processing_list
    )


def summarize_supplier_dispute_processing(
    db: Session,
    *,
    supplier_id: int,
    dispute_status: str,
    store_id: int | None = None,
    page_num: int = _DEFAULT_PAGE_NO,
    page_size: int = _DEFAULT_PAGE_SIZE,
    start_time: str | None = None,
    end_time: str | None = None,
) -> SupplierDisputeProcessingSummary:
    """
    汇总单店或多店进行中的纠纷订单（v1）。

    每个店铺调用：
    - dh.dispute.processing.list$1.0 → stores[].dispute_processing

    stores_summary.dispute_processing_list：
    合并各店 disputeList（附 store_id / store_identifier）。
    任一敦煌调用失败则整次汇总失败。
    """
    stores = _resolve_dispute_stores(
        db,
        supplier_id=supplier_id,
        store_id=store_id,
    )

    summary = SupplierDisputeProcessingSummary(
        supplier_id=supplier_id,
        dispute_status=dispute_status,
        page_num=page_num,
        page_size=page_size,
        start_time=start_time,
        end_time=end_time,
    )

    for store in stores:
        store_result, raw_calls = _fetch_store_dispute_processing(
            db,
            store,
            dispute_status=dispute_status,
            page_num=page_num,
            page_size=page_size,
            start_time=start_time,
            end_time=end_time,
        )
        summary.stores.append(store_result)
        summary.raw_calls.extend(raw_calls)

    summary.stores_summary = _build_processing_stores_summary(summary.stores)
    return summary


def _fetch_store_dispute_open(
    db: Session,
    store: Store,
    *,
    page_no: int,
    page_size: int,
) -> tuple[StoreDisputeOpenResult, list[dict[str, Any]]]:
    client = get_dhgate_client(db, store.id)
    client.clear_call_history()
    result = StoreDisputeOpenResult(
        store_id=store.id,
        store_name=store.name,
        store_identifier=store.identifier,
    )

    result.dispute_open = list_order_dispute_open(
        client,
        page_no=page_no,
        page_size=page_size,
    )

    raw_calls = _annotate_raw_calls(
        client.call_history,
        store_id=store.id,
        store_identifier=store.identifier,
    )
    return result, raw_calls


def _build_open_stores_summary(
    stores: list[StoreDisputeOpenResult],
) -> StoresDisputeOpenSummary:
    """合并各店铺 dispute_open 中的 orderDisputeOpenInfos。"""
    dispute_open_list: list[dict[str, Any]] = []
    for store in stores:
        for item in _extract_list_items(store.dispute_open, "orderDisputeOpenInfos"):
            dispute_open_list.append(
                {
                    **item,
                    "store_id": store.store_id,
                    "store_identifier": store.store_identifier,
                }
            )
    return StoresDisputeOpenSummary(dispute_open_list=dispute_open_list)


def summarize_supplier_dispute_open(
    db: Session,
    *,
    supplier_id: int,
    store_id: int | None = None,
    page_no: int = _DEFAULT_PAGE_NO,
    page_size: int = _DEFAULT_PAGE_SIZE,
) -> SupplierDisputeOpenSummary:
    """
    汇总单店或多店当前开启中的纠纷订单（v2）。

    - supplier_id 必传
    - store_id 选传：传入则只查该店，不传则查该供应商下全部已授权敦煌店铺
    - page_no / page_size：与处罚汇总接口默认一致（1 / 100）

    每个店铺调用：
    - dh.order.disputeopen.list$2.0 → stores[].dispute_open

    stores_summary.dispute_open_list：
    合并各店 orderDisputeOpenInfos（附 store_id / store_identifier）

    说明：官方纠纷开启列表无时间范围入参，返回的是当前仍处于开启状态的纠纷。
    任一敦煌调用失败则整次汇总失败。
    """
    stores = _resolve_dispute_stores(
        db,
        supplier_id=supplier_id,
        store_id=store_id,
    )

    summary = SupplierDisputeOpenSummary(
        supplier_id=supplier_id,
        page_no=page_no,
        page_size=page_size,
    )

    for store in stores:
        store_result, raw_calls = _fetch_store_dispute_open(
            db,
            store,
            page_no=page_no,
            page_size=page_size,
        )
        summary.stores.append(store_result)
        summary.raw_calls.extend(raw_calls)

    summary.stores_summary = _build_open_stores_summary(summary.stores)
    return summary
