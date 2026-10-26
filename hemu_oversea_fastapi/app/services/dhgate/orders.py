"""敦煌订单相关 API 封装。

文档：https://open.dhgate.com/docs/api （Order API / 2.7）
"""

from __future__ import annotations

from typing import Any

from app.core.errors import AppError, bad_request
from app.services.dhgate.client import DhgateClient

# dh.order.disputeopen.list 在没有纠纷中订单时返回的空结果，不是调用失败。
_EMPTY_DISPUTE_OPEN_CODE = "105"
_EMPTY_DISPUTE_OPEN_MESSAGE = "无符合查询条件的订单"


def list_orders(
    client: DhgateClient,
    *,
    page_no: int,
    page_size: int,
    **filters: Any,
) -> dict:
    """
    订单列表（对接官方 Order API 后在此实现 client.call）。

    示例（method / version 以官方文档为准）：
        return client.call(
            "dh.order.list.get",
            version="2.0",
            params={"pageNo": page_no, "pageSize": page_size, **filters},
            http_method="GET",
        )
    """
    raise bad_request(
        "敦煌订单列表接口尚未对接：请在 app/services/dhgate/orders.py 中配置官方 method"
    )


def list_dispute_processing(
    client: DhgateClient,
    *,
    dispute_status: str,
    page_num: int = 1,
    page_size: int = 100,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict[str, Any]:
    """
    获取进行中纠纷订单列表（v1）。

    method: dh.dispute.processing.list
    version: 1.0
    必填 disputeStatus；可选 startTime、endTime、pageNum、pageSize。

    返回：
    - disputeList：进行中纠纷订单列表
    - total / pageNum / pageSize：总条数与分页信息
    """
    status = str(dispute_status or "").strip()
    if not status:
        raise bad_request("dispute_status 不能为空")
    if page_num < 1:
        raise bad_request("page_num 不能小于 1")
    if page_size < 1 or page_size > 200:
        raise bad_request("page_size 须在 1～200 之间")

    params: dict[str, Any] = {
        "disputeStatus": status,
        "pageNum": page_num,
        "pageSize": page_size,
    }
    start = str(start_time or "").strip()
    if start:
        params["startTime"] = start
    end = str(end_time or "").strip()
    if end:
        params["endTime"] = end

    return client.call(
        "dh.dispute.processing.list",
        version="1.0",
        params=params,
        http_method="POST",
    )


def list_order_dispute_open(
    client: DhgateClient,
    *,
    page_no: int,
    page_size: int,
    dispute_type: str | None = None,
    buyer_nick_name: str | None = None,
    order_no: str | None = None,
) -> dict[str, Any]:
    """
    获取 seller 纠纷开启订单列表（v2）。

    method: dh.order.disputeopen.list
    version: 2.0
    官方仅支持 POST；必填 pageNo、pageSize。

    返回：
    - orderDisputeOpenInfos：开启中纠纷订单列表
    - pages / count：总页数、总条数

    店铺没有纠纷中订单时，敦煌返回状态码 105「无符合查询条件的订单」，按空列表处理。
    """
    if page_no < 1:
        raise bad_request("page_no 不能小于 1")
    if page_size < 1 or page_size > 200:
        raise bad_request("page_size 须在 1～200 之间")

    params: dict[str, Any] = {
        "pageNo": page_no,
        "pageSize": page_size,
    }
    dtype = str(dispute_type or "").strip()
    if dtype:
        params["disputeType"] = dtype
    nick = str(buyer_nick_name or "").strip()
    if nick:
        params["buyerNickName"] = nick
    ono = str(order_no or "").strip()
    if ono:
        params["orderNo"] = ono

    try:
        return client.call(
            "dh.order.disputeopen.list",
            version="2.0",
            params=params,
            http_method="POST",
        )
    except AppError as exc:
        if _is_empty_dispute_open_error(exc):
            return {
                "orderDisputeOpenInfos": [],
                "pages": 0,
                "count": 0,
            }
        raise


def _is_empty_dispute_open_error(exc: AppError) -> bool:
    """纠纷开启列表无订单：状态码 105，或文案为「无符合查询条件的订单」。"""
    data = exc.data or {}
    if str(data.get("dhgate_error_code") or "") == _EMPTY_DISPUTE_OPEN_CODE:
        return True
    return _EMPTY_DISPUTE_OPEN_MESSAGE in (exc.message or "")
