"""敦煌 SKU 基础信息表写入（sku_base_info_dh）。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import Pagination
from app.core.errors import bad_request, not_found
from app.core.sku_code import SKU_VARIANT_PG_REGEX, normalize_sku_code
from app.models.sku_base_info_dh import SkuBaseInfoDh
from app.schemas.common import PageData
from app.schemas.utils import (
    DhSkuBaseInfoPublic,
    DhgateUpdateSkuBaseInfoFailedItem,
    DhgateUpdateSkuBaseInfoPublic,
)

_PRICE_PREFIX_RE = re.compile(r"^[\s$￥€£]+")
_PRICE_CLEAN_RE = re.compile(r"[,\s]")

# 批量导入默认供应商 / 系统操作人
DEFAULT_SUPPLIER_ID = 0
DEFAULT_UPDATED_BY = 0

SKU_BASE_INFO_REQUIRED_FIELDS = {"sku_code", "sku_series", "unit_price"}


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


def parse_optional_weight_kg(raw: Any) -> Decimal | None:
    """解析重量 kg；空值视为未填写。"""
    text = _as_text(raw)
    if not text:
        return None
    text = _PRICE_CLEAN_RE.sub("", text)
    try:
        weight = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"weight_kg 无法解析：{raw!r}") from exc
    if weight < 0:
        raise ValueError(f"weight_kg 不能为负数：{weight}")
    return weight.quantize(Decimal("0.001"))


def parse_optional_positive_int(raw: Any, *, field_name: str) -> int | None:
    """解析正整数；空值视为未填写。"""
    text = _as_text(raw)
    if not text:
        return None
    try:
        value = int(Decimal(text))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} 无法解析：{raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{field_name} 必须为正整数：{value}")
    return value


def parse_optional_template_name(raw: Any) -> str | None:
    """解析物流模板名称；空值视为未填写。"""
    text = _as_text(raw)
    if not text:
        return None
    if len(text) > 128:
        raise ValueError("shipping_template_name 超过 128 字符")
    return text


def _to_public(row: SkuBaseInfoDh) -> DhSkuBaseInfoPublic:
    return DhSkuBaseInfoPublic(
        supplier_id=row.supplier_id,
        sku_code=row.sku_code,
        sku_series=row.sku_series,
        unit_price=row.unit_price,
        shipping_template_name=row.shipping_template_name,
        weight_kg=row.weight_kg,
        packing_quantity=row.packing_quantity,
        min_wholesale_qty=row.min_wholesale_qty,
    )


def list_sku_base_infos(
    db: Session,
    *,
    supplier_id: int,
    keyword: str | None,
    pagination: Pagination,
) -> PageData[DhSkuBaseInfoPublic]:
    """按供应商分页列出 sku_base_info_dh；keyword 对 sku_code 模糊匹配。

    排除同型号变体（如 BD001-1 / BD001-2），仅保留基型号（BD001）。
    """
    if supplier_id <= 0:
        raise bad_request("supplier_id 无效")

    # PostgreSQL：sku_code !~ '^[A-Za-z]+[0-9]+-[0-9]+$'
    not_variant = ~SkuBaseInfoDh.sku_code.op("~")(SKU_VARIANT_PG_REGEX)
    stmt = select(SkuBaseInfoDh).where(
        SkuBaseInfoDh.supplier_id == supplier_id,
        not_variant,
    )
    count_stmt = (
        select(func.count())
        .select_from(SkuBaseInfoDh)
        .where(
            SkuBaseInfoDh.supplier_id == supplier_id,
            not_variant,
        )
    )
    kw = (keyword or "").strip()
    if kw:
        like = f"%{kw}%"
        stmt = stmt.where(SkuBaseInfoDh.sku_code.ilike(like))
        count_stmt = count_stmt.where(SkuBaseInfoDh.sku_code.ilike(like))

    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(
        stmt.order_by(SkuBaseInfoDh.sku_code.asc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()
    return PageData(
        items=[_to_public(row) for row in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def get_sku_base_info(
    db: Session,
    *,
    supplier_id: int,
    sku_code: str,
) -> DhSkuBaseInfoPublic:
    """按供应商 + SKU 型号查询基础信息（sku_code 先统一清洗再查表）。"""
    if supplier_id <= 0:
        raise bad_request("supplier_id 无效")
    code = normalize_sku_code(sku_code)
    if not code:
        raise bad_request("sku_code 不能为空")

    row = db.scalar(
        select(SkuBaseInfoDh).where(
            SkuBaseInfoDh.supplier_id == supplier_id,
            SkuBaseInfoDh.sku_code == code,
        )
    )
    if row is None:
        raise not_found(f"未找到 SKU 基础信息：supplier_id={supplier_id}, sku_code={code}")

    return _to_public(row)


def upsert_sku_base_infos_from_items(
    db: Session,
    *,
    items: list[dict[str, str]],
    supplier_id: int = DEFAULT_SUPPLIER_ID,
    updated_by: int = DEFAULT_UPDATED_BY,
) -> DhgateUpdateSkuBaseInfoPublic:
    """
    按 Excel 提取行批量 upsert sku_base_info_dh。

    必填：sku_code / sku_series / unit_price
    可选：shipping_template_name / weight_kg / packing_quantity / min_wholesale_qty
    唯一键：supplier_id + sku_code
    """
    now = datetime.now(timezone.utc)
    success_count = 0
    created_count = 0
    updated_count = 0
    failed_items: list[DhgateUpdateSkuBaseInfoFailedItem] = []

    # 同一批次内后写覆盖先写，避免重复键冲突
    pending: dict[str, dict[str, Any]] = {}
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            failed_items.append(
                DhgateUpdateSkuBaseInfoFailedItem(
                    sku_code="",
                    error_message=f"第 {idx + 1} 行数据格式无效",
                )
            )
            continue

        raw_sku_code = _as_text(item.get("sku_code"))
        sku_code = normalize_sku_code(raw_sku_code)
        sku_series = _as_text(item.get("sku_series"))
        try:
            if not sku_code:
                raise ValueError("缺少 sku_code")
            if not sku_series:
                raise ValueError("缺少 sku_series")
            unit_price = parse_unit_price(item.get("unit_price"))
            shipping_template_name = parse_optional_template_name(
                item.get("shipping_template_name")
            )
            weight_kg = parse_optional_weight_kg(item.get("weight_kg"))
            packing_quantity = parse_optional_positive_int(
                item.get("packing_quantity"),
                field_name="packing_quantity",
            )
            min_wholesale_qty = parse_optional_positive_int(
                item.get("min_wholesale_qty"),
                field_name="min_wholesale_qty",
            )
        except ValueError as exc:
            failed_items.append(
                DhgateUpdateSkuBaseInfoFailedItem(
                    sku_code=raw_sku_code or sku_code,
                    error_message=str(exc),
                )
            )
            continue

        pending[sku_code] = {
            "sku_code": sku_code,
            "sku_series": sku_series,
            "unit_price": unit_price,
            "shipping_template_name": shipping_template_name,
            "weight_kg": weight_kg,
            "packing_quantity": packing_quantity,
            "min_wholesale_qty": min_wholesale_qty,
        }

    if not pending:
        return DhgateUpdateSkuBaseInfoPublic(
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
        select(SkuBaseInfoDh).where(
            SkuBaseInfoDh.supplier_id == supplier_id,
            SkuBaseInfoDh.sku_code.in_(codes),
        )
    ).all()
    by_code = {row.sku_code: row for row in existing_rows}

    for sku_code, payload in pending.items():
        row = by_code.get(sku_code)
        if row is None:
            db.add(
                SkuBaseInfoDh(
                    supplier_id=supplier_id,
                    sku_code=payload["sku_code"],
                    sku_series=payload["sku_series"],
                    unit_price=payload["unit_price"],
                    shipping_template_name=payload["shipping_template_name"],
                    weight_kg=payload["weight_kg"],
                    packing_quantity=payload["packing_quantity"],
                    min_wholesale_qty=payload["min_wholesale_qty"],
                    updated_at=now,
                    updated_by=updated_by,
                )
            )
            created_count += 1
        else:
            row.sku_series = payload["sku_series"]
            row.unit_price = payload["unit_price"]
            row.shipping_template_name = payload["shipping_template_name"]
            row.weight_kg = payload["weight_kg"]
            row.packing_quantity = payload["packing_quantity"]
            row.min_wholesale_qty = payload["min_wholesale_qty"]
            row.updated_at = now
            row.updated_by = updated_by
            updated_count += 1
        success_count += 1

    db.commit()
    return DhgateUpdateSkuBaseInfoPublic(
        supplier_id=supplier_id,
        updated_by=updated_by,
        success_count=success_count,
        created_count=created_count,
        updated_count=updated_count,
        failed_count=len(failed_items),
        failed_items=failed_items,
    )
