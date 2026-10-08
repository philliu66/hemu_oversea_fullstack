"""敦煌 SKU 基础价格表写入（sku_base_price_dh）。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, not_found
from app.models.sku_base_price_dh import SkuBasePriceDh
from app.schemas.utils import (
    DhSkuBasePricePublic,
    DhgateUpdateSkuBasePriceFailedItem,
    DhgateUpdateSkuBasePricePublic,
)

_PRICE_PREFIX_RE = re.compile(r"^[\s$￥€£]+")
_PRICE_CLEAN_RE = re.compile(r"[,\s]")

# 批量导入默认供应商 / 系统操作人
DEFAULT_SUPPLIER_ID = 4
DEFAULT_UPDATED_BY = 0


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def parse_unit_price(raw: Any) -> Decimal:
    """解析售价：去掉 $ 等货币前缀与千分位逗号。"""
    text = _as_text(raw)
    if not text:
        raise ValueError("unit_price 为空")
    text = _PRICE_PREFIX_RE.sub("", text)
    text = _PRICE_CLEAN_RE.sub("", text)
    if not text:
        raise ValueError("unit_price 无效")
    try:
        price = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"unit_price 无法解析：{raw!r}") from exc
    if price < 0:
        raise ValueError(f"unit_price 不能为负数：{price}")
    return price.quantize(Decimal("0.01"))


def get_sku_base_price(
    db: Session,
    *,
    supplier_id: int,
    sku_code: str,
) -> DhSkuBasePricePublic:
    """按供应商 + SKU 型号查询基础价格。"""
    if supplier_id <= 0:
        raise bad_request("supplier_id 无效")
    code = _as_text(sku_code)
    if not code:
        raise bad_request("sku_code 不能为空")

    row = db.scalar(
        select(SkuBasePriceDh).where(
            SkuBasePriceDh.supplier_id == supplier_id,
            SkuBasePriceDh.sku_code == code,
        )
    )
    if row is None:
        raise not_found(f"未找到 SKU 基础价格：supplier_id={supplier_id}, sku_code={code}")

    return DhSkuBasePricePublic(
        supplier_id=row.supplier_id,
        sku_code=row.sku_code,
        sku_series=row.sku_series,
        unit_price=row.unit_price,
    )


def upsert_sku_base_prices_from_items(
    db: Session,
    *,
    items: list[dict[str, str]],
    supplier_id: int = DEFAULT_SUPPLIER_ID,
    updated_by: int = DEFAULT_UPDATED_BY,
) -> DhgateUpdateSkuBasePricePublic:
    """
    按 Excel 提取行批量 upsert sku_base_price_dh。

    期望字段：sku_code / sku_series / unit_price
    唯一键：supplier_id + sku_code
    """
    now = datetime.now(timezone.utc)
    success_count = 0
    created_count = 0
    updated_count = 0
    failed_items: list[DhgateUpdateSkuBasePriceFailedItem] = []

    # 同一批次内后写覆盖先写，避免重复键冲突
    pending: dict[str, dict[str, Any]] = {}
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            failed_items.append(
                DhgateUpdateSkuBasePriceFailedItem(
                    sku_code="",
                    error_message=f"第 {idx + 1} 行数据格式无效",
                )
            )
            continue

        sku_code = _as_text(item.get("sku_code"))
        sku_series = _as_text(item.get("sku_series"))
        try:
            if not sku_code:
                raise ValueError("缺少 sku_code")
            if not sku_series:
                raise ValueError("缺少 sku_series")
            unit_price = parse_unit_price(item.get("unit_price"))
        except ValueError as exc:
            failed_items.append(
                DhgateUpdateSkuBasePriceFailedItem(
                    sku_code=sku_code,
                    error_message=str(exc),
                )
            )
            continue

        pending[sku_code] = {
            "sku_code": sku_code,
            "sku_series": sku_series,
            "unit_price": unit_price,
        }

    if not pending:
        return DhgateUpdateSkuBasePricePublic(
            supplier_id=supplier_id,
            updated_by=updated_by,
            success_count=0,
            created_count=0,
            updated_count=0,
            failed_count=len(failed_items),
            failed_items=failed_items,
        )

    codes = list(pending.keys())
    existing_rows = db.scalars(
        select(SkuBasePriceDh).where(
            SkuBasePriceDh.supplier_id == supplier_id,
            SkuBasePriceDh.sku_code.in_(codes),
        )
    ).all()
    by_code = {row.sku_code: row for row in existing_rows}

    for sku_code, payload in pending.items():
        row = by_code.get(sku_code)
        if row is None:
            db.add(
                SkuBasePriceDh(
                    supplier_id=supplier_id,
                    sku_code=payload["sku_code"],
                    sku_series=payload["sku_series"],
                    unit_price=payload["unit_price"],
                    updated_at=now,
                    updated_by=updated_by,
                )
            )
            created_count += 1
        else:
            row.sku_series = payload["sku_series"]
            row.unit_price = payload["unit_price"]
            row.updated_at = now
            row.updated_by = updated_by
            updated_count += 1
        success_count += 1

    db.commit()
    return DhgateUpdateSkuBasePricePublic(
        supplier_id=supplier_id,
        updated_by=updated_by,
        success_count=success_count,
        created_count=created_count,
        updated_count=updated_count,
        failed_count=len(failed_items),
        failed_items=failed_items,
    )
