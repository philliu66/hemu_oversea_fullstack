"""敦煌纠纷开启订单字段 enrichment（巡检展示用）。

依据官方文档 dh.order.disputeopen.list$2.0：
- disputeStatus / orderStatus：编码 → 中文
- disputeOpenDate：纠纷开启时间（CST Date.toString → yyyy-MM-dd HH:mm:ss）
- isWarn：是否高风险/需特别注意 → is_high_risk
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

# dh.order.disputeopen.list orderDisputeOpenInfos.disputeStatus
_DISPUTE_STATUS_LABELS: dict[str, str] = {
    "106001": "协议纠纷-等待协议达成",
    "106003": "协议纠纷-协议已达成",
    "107001": "平台纠纷开启",
    "107002": "平台纠纷-dhgate审核中",
    "107003": "平台纠纷-裁决方案执行中",
    "109001": "售后纠纷开启",
    "109002": "售后纠纷裁决中",
}

# 请求入参 disputeType（1/2/3）；响应若带回同字段则一并映射
_DISPUTE_TYPE_LABELS: dict[str, str] = {
    "1": "协议纠纷",
    "2": "平台纠纷",
    "3": "售后纠纷",
}

# dh.order.disputeopen.list orderDisputeOpenInfos.orderStatus
_ORDER_STATUS_LABELS: dict[str, str] = {
    "111000": "订单取消",
    "101003": "等待买家付款",
    "102001": "买家已付款，等待平台确认",
    "103001": "等待发货",
    "105001": "买家申请退款，等待协商结果",
    "105002": "退款协议已达成",
    "105003": "部分退款后，等待发货",
    "105004": "买家取消退款申请",
    "103002": "已部分发货",
    "101009": "等待买家确认收货",
    "106001": "退款/退货协商中，等待协议达成",
    "106002": "买家投诉到平台",
    "106003": "协议已达成，执行中",
    "102006": "人工确认收货",
    "102007": "超过预定期限，自动确认收货",
    "102111": "交易成功",
    "111111": "交易关闭",
}

_JAVA_CST_DATE_RE = re.compile(
    r"^[A-Za-z]{3}\s+[A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+[A-Za-z]+\s+\d{4}$"
)

_TRUTHY = frozenset({"1", "true", "y", "yes", "high", "highrisk"})


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def dispute_status_label(value: Any) -> str | None:
    code = _as_str(value)
    if code is None:
        return None
    return _DISPUTE_STATUS_LABELS.get(code, code)


def dispute_type_label(value: Any) -> str | None:
    code = _as_str(value)
    if code is None:
        return None
    return _DISPUTE_TYPE_LABELS.get(code, code)


def order_status_label(value: Any) -> str | None:
    code = _as_str(value)
    if code is None:
        return None
    return _ORDER_STATUS_LABELS.get(code, code)


def format_dhgate_datetime(value: Any) -> str | None:
    """
    将敦煌时间转为 yyyy-MM-dd HH:mm:ss。

    支持：
    - Tue Sep 29 03:52:33 CST 2026（官方常见 Java Date.toString）
    - 已是 yyyy-MM-dd HH:mm:ss / yyyy-MM-dd 则规范化后返回
    """
    text = _as_str(value)
    if text is None:
        return None

    if _JAVA_CST_DATE_RE.match(text):
        parts = text.split()
        # weekday month day HH:MM:SS TZ year
        try:
            dt = datetime.strptime(
                f"{parts[0]} {parts[1]} {parts[2]} {parts[3]} {parts[5]}",
                "%a %b %d %H:%M:%S %Y",
            )
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return text

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

    return text


def _pick_first(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key not in row:
            continue
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return value
    return None


def _is_high_risk(row: dict[str, Any]) -> bool:
    # 官方字段 isWarn；兼容历史别名
    raw = _pick_first(
        row,
        (
            "isWarn",
            "is_warn",
            "isHighRisk",
            "highRisk",
            "highRiskOrder",
            "is_high_risk",
            "high_risk",
            "riskFlag",
        ),
    )
    if raw is None:
        return False
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return raw == 1
    return str(raw).strip().lower() in _TRUTHY


def enrich_dispute_open_item(item: dict[str, Any]) -> dict[str, Any]:
    """
    巡检展示用字段规范化。

    - disputeStatus / disputeType / orderStatus → 中文（保留 *Code）
    - disputeOpenDate → openTime（yyyy-MM-dd HH:mm:ss）
    - isWarn → is_high_risk
    - country / warnReason / orderTotalPrice：别名归一
    """
    row = dict(item)

    raw_status = row.get("disputeStatus")
    if _as_str(raw_status) is not None:
        row["disputeStatusCode"] = str(raw_status).strip()
        label = dispute_status_label(raw_status)
        if label is not None:
            row["disputeStatus"] = label

    raw_type = row.get("disputeType")
    if _as_str(raw_type) is not None:
        row["disputeTypeCode"] = str(raw_type).strip()
        label = dispute_type_label(raw_type)
        if label is not None:
            row["disputeType"] = label

    raw_order_status = _pick_first(
        row,
        ("orderStatus", "order_status", "orderStatusName"),
    )
    if _as_str(raw_order_status) is not None:
        row["orderStatusCode"] = str(raw_order_status).strip()
        label = order_status_label(raw_order_status)
        if label is not None:
            row["orderStatus"] = label

    # 官方：disputeOpenDate=纠纷开启时间；startedDate=下单日期（勿混用）
    raw_open_time = _pick_first(
        row,
        (
            "disputeOpenDate",
            "openTime",
            "disputeOpenTime",
            "dispute_open_date",
        ),
    )
    formatted_open = format_dhgate_datetime(raw_open_time)
    if formatted_open is not None:
        row["openTime"] = formatted_open
        row["disputeOpenDate"] = formatted_open

    country = _pick_first(
        row,
        (
            "country",
            "countryName",
            "countryCn",
            "buyerCountry",
            "receiveCountry",
            "shipToCountry",
            "shiptoCountry",
            "countryNameCn",
        ),
    )
    if country is not None:
        row["country"] = country

    warn_reason = _pick_first(
        row,
        (
            "warnReason",
            "warningReason",
            "warnMsg",
            "warningMsg",
            "riskReason",
            "riskWarnReason",
            "highRiskReason",
            "warn_reason",
        ),
    )
    if warn_reason is not None:
        row["warnReason"] = warn_reason

    amount = _pick_first(
        row,
        (
            "orderTotalPrice",
            "orderAmount",
            "actualPrice",
            "order_total_price",
        ),
    )
    if amount is not None:
        row["orderTotalPrice"] = amount

    row["is_high_risk"] = _is_high_risk(row)
    return row
