#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量校验 / 覆盖敦煌商品 SKU 标价（跑批脚本）

按 product_dh.id 升序分批读取商品，对 sku_json 中每个 SKU 调用与
  POST /api/v1/admin/product/dh/skulistprice/get
相同的计算逻辑（calc_sku_list_price），对比原 retailPrice 与计算出的标价。

定价参考类目 cate_id 固定为 000000；供应商 / 店铺取商品自身字段。

用法（在 hemu_oversea_fastapi 根目录）：
  uv run python script/batch_check_sku_list_price.py [选项]

参数：
  --start-id      起始商品 id（默认 1，表示从 id>=1 开始）
  --batch-count   每批处理商品数（默认 10）
  --total-count   最多处理商品数（默认 0=全部）
  --is-cover      覆盖模式：将算出的标价写回 sku_json（及 raw_json.itemSkuList）

示例：
  # 从 id=1 起每批 10 个，校验全部，不覆盖
  uv run python script/batch_check_sku_list_price.py

  # 从 id=10 起，最多 20 个，每批 10，覆盖异常标价
  uv run python script/batch_check_sku_list_price.py --start-id 10 --batch-count 10 --total-count 20 --is-cover
"""

from __future__ import annotations

import argparse
import copy
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy import select

# 保证可从项目根目录导入 app.*
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.core.db import SessionLocal  # noqa: E402
from app.core.errors import AppError  # noqa: E402
from app.models.product_dh import ProductDh  # noqa: E402
from app.schemas.product import DH_REF_PRICING_CATE_ID  # noqa: E402
from app.services.sku_list_prices import calc_sku_list_price  # noqa: E402

_PRICE_QUANT = Decimal("0.01")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="分批校验商品 SKU 标价（可选覆盖写回）",
    )
    parser.add_argument(
        "--start-id",
        type=int,
        default=1,
        help="起始商品 id（默认 1，表示从该 id 起升序处理）",
    )
    parser.add_argument(
        "--batch-count",
        type=int,
        default=10,
        help="每批处理商品数量（默认 10）",
    )
    parser.add_argument(
        "--total-count",
        type=int,
        default=0,
        help="最多处理商品数量（默认 0=全部）",
    )
    parser.add_argument(
        "--is-cover",
        action="store_true",
        help="覆盖模式：将计算标价写回 sku_json / raw_json.itemSkuList",
    )
    return parser.parse_args()


def _validate_args(args: argparse.Namespace) -> None:
    if args.start_id < 1:
        raise SystemExit("--start-id 须 >= 1")
    if args.batch_count < 1:
        raise SystemExit("--batch-count 须 >= 1")
    if args.total_count < 0:
        raise SystemExit("--total-count 须 >= 0")


def _to_decimal(raw: Any) -> Decimal | None:
    if raw is None or raw == "":
        return None
    try:
        return Decimal(str(raw).strip()).quantize(_PRICE_QUANT)
    except (InvalidOperation, ValueError, ArithmeticError):
        return None


def _prices_differ(original: Decimal | None, calculated: Decimal) -> bool:
    if original is None:
        return True
    return original != calculated.quantize(_PRICE_QUANT)


def _iter_sku_items(sku_json: Any) -> list[dict[str, Any]]:
    if not isinstance(sku_json, list):
        return []
    return [item for item in sku_json if isinstance(item, dict)]


def _fetch_batch(
    db,
    *,
    start_id: int,
    limit: int,
) -> list[ProductDh]:
    stmt = (
        select(ProductDh)
        .where(ProductDh.id >= start_id)
        .order_by(ProductDh.id.asc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def _sync_raw_json_retail_price(
    raw_json: dict[str, Any] | None,
    *,
    sku_code: str,
    list_price: Decimal,
) -> dict[str, Any] | None:
    """同步更新 raw_json.itemSkuList 中同 skuCode 的 retailPrice。"""
    if not isinstance(raw_json, dict):
        return raw_json
    sku_list = raw_json.get("itemSkuList")
    if not isinstance(sku_list, list):
        return raw_json
    changed = False
    next_raw = copy.deepcopy(raw_json)
    next_list = next_raw.get("itemSkuList")
    if not isinstance(next_list, list):
        return raw_json
    for item in next_list:
        if not isinstance(item, dict):
            continue
        if str(item.get("skuCode") or "").strip() != sku_code:
            continue
        item["retailPrice"] = float(list_price)
        changed = True
    return next_raw if changed else raw_json


def _process_product(
    db,
    product: ProductDh,
    *,
    is_cover: bool,
) -> dict[str, Any]:
    """
    处理单个商品。

    返回：
      {
        "product_id", "item_code",
        "anomaly_skus": [{sku_code, calculated_price, original_price, error?}],
        "sku_checked", "covered_count",
      }
    """
    sku_items = _iter_sku_items(product.sku_json)
    anomaly_skus: list[dict[str, Any]] = []
    covered_count = 0
    sku_checked = 0
    next_sku_json: list[dict[str, Any]] | None = None
    next_raw_json = product.raw_json

    for sku in sku_items:
        sku_code = str(sku.get("skuCode") or "").strip()
        if not sku_code:
            continue
        sku_checked += 1
        original_price = _to_decimal(sku.get("retailPrice"))

        try:
            result = calc_sku_list_price(
                db,
                supplier_id=int(product.supplier_id),
                sku_code=sku_code,
                store_id=int(product.store_id),
                cate_id=DH_REF_PRICING_CATE_ID,
            )
            calculated = result.list_price.quantize(_PRICE_QUANT)
        except AppError as exc:
            anomaly_skus.append(
                {
                    "sku_code": sku_code,
                    "calculated_price": None,
                    "original_price": (
                        str(original_price) if original_price is not None else None
                    ),
                    "error": exc.message,
                }
            )
            continue
        except Exception as exc:  # noqa: BLE001
            anomaly_skus.append(
                {
                    "sku_code": sku_code,
                    "calculated_price": None,
                    "original_price": (
                        str(original_price) if original_price is not None else None
                    ),
                    "error": str(exc),
                }
            )
            continue

        if _prices_differ(original_price, calculated):
            anomaly_skus.append(
                {
                    "sku_code": sku_code,
                    "calculated_price": str(calculated),
                    "original_price": (
                        str(original_price) if original_price is not None else None
                    ),
                }
            )

        if is_cover:
            if next_sku_json is None:
                next_sku_json = copy.deepcopy(sku_items)
            for item in next_sku_json:
                if str(item.get("skuCode") or "").strip() != sku_code:
                    continue
                item["retailPrice"] = float(calculated)
                covered_count += 1
                break
            next_raw_json = _sync_raw_json_retail_price(
                next_raw_json if isinstance(next_raw_json, dict) else product.raw_json,
                sku_code=sku_code,
                list_price=calculated,
            )

    if is_cover and next_sku_json is not None and covered_count > 0:
        product.sku_json = next_sku_json
        if next_raw_json is not None:
            product.raw_json = next_raw_json
        db.add(product)
        db.commit()

    return {
        "product_id": product.id,
        "item_code": product.item_code,
        "anomaly_skus": anomaly_skus,
        "sku_checked": sku_checked,
        "covered_count": covered_count,
    }


def _print_batch_report(
    *,
    batch_no: int,
    processed_in_batch: int,
    anomaly_products: list[dict[str, Any]],
    is_cover: bool,
) -> None:
    print("")
    print("=" * 60)
    print(f"批次 #{batch_no} 结束")
    print(f"本批处理商品数：{processed_in_batch}")
    print(f"本批异常商品数：{len(anomaly_products)}")
    if is_cover:
        print("（覆盖模式已开启）")
    if not anomaly_products:
        print("本批无异常数据")
        print("=" * 60)
        return

    print("异常数据（按商品维度）：")
    for product in anomaly_products:
        print(
            f"  商品 id={product['product_id']} item_code={product['item_code']}"
        )
        for sku in product["anomaly_skus"]:
            if sku.get("error"):
                print(
                    f"    - sku_code={sku['sku_code']} "
                    f"original_price={sku['original_price']} "
                    f"calculated_price=None "
                    f"error={sku['error']}"
                )
            else:
                print(
                    f"    - sku_code={sku['sku_code']} "
                    f"original_price={sku['original_price']} "
                    f"calculated_price={sku['calculated_price']}"
                )
    print("=" * 60)


def main() -> None:
    args = _parse_args()
    _validate_args(args)

    print(
        "开始批量校验 SKU 标价："
        f"start_id={args.start_id}, batch_count={args.batch_count}, "
        f"total_count={args.total_count or '全部'}, is_cover={args.is_cover}, "
        f"cate_id={DH_REF_PRICING_CATE_ID}"
    )

    cursor_id = args.start_id
    total_processed = 0
    total_anomaly_products = 0
    total_covered = 0
    batch_no = 0

    db = SessionLocal()
    try:
        while True:
            if args.total_count > 0 and total_processed >= args.total_count:
                break

            remain = (
                args.total_count - total_processed
                if args.total_count > 0
                else args.batch_count
            )
            limit = min(args.batch_count, remain) if args.total_count > 0 else args.batch_count

            products = _fetch_batch(db, start_id=cursor_id, limit=limit)
            if not products:
                print(f"\n无更多商品（cursor_id>={cursor_id}），结束。")
                break

            batch_no += 1
            anomaly_products: list[dict[str, Any]] = []
            batch_covered = 0

            for product in products:
                result = _process_product(db, product, is_cover=args.is_cover)
                batch_covered += int(result["covered_count"] or 0)
                if result["anomaly_skus"]:
                    anomaly_products.append(result)

            total_processed += len(products)
            total_anomaly_products += len(anomaly_products)
            total_covered += batch_covered
            cursor_id = products[-1].id + 1

            _print_batch_report(
                batch_no=batch_no,
                processed_in_batch=len(products),
                anomaly_products=anomaly_products,
                is_cover=args.is_cover,
            )
            if args.is_cover:
                print(f"本批覆盖写回 SKU 数：{batch_covered}")

            print(
                f"累计：已处理商品 {total_processed}，"
                f"异常商品 {total_anomaly_products}，"
                f"下一 cursor_id={cursor_id}"
            )
    finally:
        db.close()

    print("")
    print("#" * 60)
    print("全部结束")
    print(f"合计处理商品：{total_processed}")
    print(f"合计异常商品：{total_anomaly_products}")
    if args.is_cover:
        print(f"合计覆盖 SKU 数：{total_covered}")
    print("#" * 60)


if __name__ == "__main__":
    main()
