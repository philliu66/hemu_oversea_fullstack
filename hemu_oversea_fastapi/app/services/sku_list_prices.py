"""SKU 标价计算（基础价 × 打包数 × (1−佣金率) / 店铺折扣）。"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.core.errors import bad_request
from app.schemas.product import (
    DH_REF_PRICING_CATE_ID,
    DhCommissionUnitPublic,
    DhSkuListPricePublic,
)
from app.services.commission_rates_dh import get_commission_rate_by_cate_id
from app.services.sku_base_infos_dh import get_sku_base_info
from app.services.stores import get_store_base_discount


def _to_rate_decimal(raw: str | Decimal | int | float | None) -> Decimal | None:
    """将 0.08 / '0.08' / '8' / '8%' 统一为小数费率。"""
    if raw is None:
        return None
    text = str(raw).strip().replace("%", "")
    if not text:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    if abs(value) > 1:
        value = value / Decimal("100")
    return value


def _bound_number(raw: str | None) -> Decimal | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _amount_in_unit(amount: Decimal, unit: DhCommissionUnitPublic) -> bool:
    left = _bound_number(unit.left_bound)
    right = _bound_number(unit.right_bound)

    if left is not None:
        if unit.left_bound_close is False:
            if not (amount > left):
                return False
        elif not (amount >= left):
            return False

    if right is not None:
        if unit.right_bound_close is False:
            if not (amount < right):
                return False
        elif not (amount <= right):
            return False

    return True


def match_commission_unit(
    amount: Decimal,
    units: list[DhCommissionUnitPublic],
) -> DhCommissionUnitPublic | None:
    """按成交金额匹配佣金阶梯区间。"""
    sorted_units = sorted(
        units,
        key=lambda u: (
            _bound_number(u.left_bound)
            if _bound_number(u.left_bound) is not None
            else Decimal("-Infinity")
        ),
    )
    for unit in sorted_units:
        if _amount_in_unit(amount, unit):
            return unit
    return None


def calc_sku_list_price(
    db: Session,
    *,
    supplier_id: int,
    sku_code: str,
    store_id: int,
    cate_id: str | None = None,
) -> DhSkuListPricePublic:
    """
    查询 SKU 基础信息并计算标价。

    标价 = 基础价格 × 打包数 ×（1 − 佣金率）/ 店铺折扣
    订单金额 = 基础价格 × 打包数 × 起订量（用于匹配类目佣金区间）
    """
    if store_id <= 0:
        raise bad_request("store_id 无效")

    cate = (cate_id or "").strip() or DH_REF_PRICING_CATE_ID

    base_info = get_sku_base_info(db, supplier_id=supplier_id, sku_code=sku_code)
    store = get_store_base_discount(db, store_id)
    commission = get_commission_rate_by_cate_id(db, cate_id=cate)

    packing_quantity = base_info.packing_quantity
    min_wholesale_qty = base_info.min_wholesale_qty
    if packing_quantity is None or packing_quantity <= 0:
        raise bad_request("SKU 基础信息缺少有效打包数，无法计算标价")
    if min_wholesale_qty is None or min_wholesale_qty <= 0:
        raise bad_request("SKU 基础信息缺少有效起订量，无法计算标价")

    unit_price = Decimal(base_info.unit_price)
    sales_unit = packing_quantity * min_wholesale_qty
    order_amount = (unit_price * Decimal(sales_unit)).quantize(Decimal("0.01"))

    matched = match_commission_unit(order_amount, commission.unit_list or [])
    if matched is None:
        raise bad_request(
            f"订单金额 {order_amount} 未匹配到类目 {cate} 的佣金区间"
        )
    commission_rate = _to_rate_decimal(matched.commission_rate)
    if commission_rate is None:
        raise bad_request("命中佣金区间但佣金率无效")

    base_discount = _to_rate_decimal(store.base_discount)
    if base_discount is None or base_discount <= 0:
        raise bad_request("店铺折扣率无效，无法计算标价")

    list_price = (
        unit_price * Decimal(packing_quantity) * (Decimal("1") - commission_rate)
    ) / base_discount
    list_price = list_price.quantize(Decimal("0.01"))

    return DhSkuListPricePublic(
        supplier_id=base_info.supplier_id,
        sku_code=base_info.sku_code,
        store_id=store_id,
        cate_id=cate,
        unit_price=unit_price.quantize(Decimal("0.01")),
        packing_quantity=packing_quantity,
        min_wholesale_qty=min_wholesale_qty,
        sales_unit=sales_unit,
        order_amount=order_amount,
        commission_rate=commission_rate,
        base_discount=base_discount,
        list_price=list_price,
    )
