"""敦煌商品批量更新（Excel / items 字段名与官网 API 一致）。"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, bad_request, not_found
from app.core.store_types import StoreType
from app.models.product_dh import ProductDh
from app.models.product_dh_update_log import ProductDhUpdateLog
from app.models.store import Store
from app.models.supplier import Supplier
from app.schemas.utils import (
    DhgateUpdateProductFailedItem,
    DhgateUpdateProductPublic,
)
from app.services.dhgate import (
    apply_package_weight_to_detail,
    build_item_update_payload,
    downshelf_items,
    get_item,
    get_item_html,
    update_item,
    upshelf_items,
)
from app.services.dhgate.client import DhgateClient
from app.services.dhgate.response import format_dhgate_error_message
from app.services.products_dh import persist_item_detail

logger = logging.getLogger("app")

_SOURCE_BATCH_EXCEL = "batch_excel"
_MAX_EXECUTE_ITEMS = 50
_DEFAULT_SITE_ID = "EN"
# 官网 update 特殊错误：需下架后再更新并上架
_ERR_IN_PROMOTION = "该产品正在参加促销活动"


def _as_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _dec_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    text = format(value, "f").rstrip("0").rstrip(".")
    return text if text else "0"


def _normalize_operator_id(operator_id: int) -> int | None:
    """0 表示系统操作者，落库为 NULL。"""
    if operator_id is None or int(operator_id) <= 0:
        return None
    return int(operator_id)


def _values_equal(left: Any, right: Any, *, as_decimal: bool = False) -> bool:
    if as_decimal:
        a = _as_decimal(left)
        b = _as_decimal(right)
        if a is None or b is None:
            return a is None and b is None
        return a == b
    return _as_int(left) == _as_int(right)


def _parse_package_item(raw: dict[str, str]) -> dict[str, Any]:
    """
    解析一条待更新包装重量数据。

    字段名与官网一致（扁平提取）：
    itemCode / grossWeight / baseQt / stepQt / stepWeight
    """
    code = str(raw.get("itemCode") or "").strip()
    if not code:
        raise bad_request("itemCode 不能为空")

    gross_weight = _as_decimal(raw.get("grossWeight"))
    step_weight = _as_decimal(raw.get("stepWeight"))
    base_qt = _as_int(raw.get("baseQt"))
    step_qt = _as_int(raw.get("stepQt"))
    missing: list[str] = []
    if gross_weight is None:
        missing.append("grossWeight")
    if base_qt is None:
        missing.append("baseQt")
    if step_qt is None:
        missing.append("stepQt")
    if step_weight is None:
        missing.append("stepWeight")
    if missing:
        raise bad_request(f"更新字段缺失或格式错误：{', '.join(missing)}")
    if gross_weight < 0 or step_weight < 0 or base_qt < 0 or step_qt < 0:
        raise bad_request("包装重量 / 件数不能为负数")

    return {
        "itemCode": code,
        "grossWeight": gross_weight,
        "baseQt": base_qt,
        "stepQt": step_qt,
        "stepWeight": step_weight,
    }


def _read_package_fields(detail: dict[str, Any]) -> dict[str, Any]:
    """从官网详情读取包装相关字段（键名与官网一致）。"""
    package = (
        detail.get("itemPackage") if isinstance(detail.get("itemPackage"), dict) else {}
    )
    weight_range = (
        package.get("itemWeigthRange")
        if isinstance(package.get("itemWeigthRange"), dict)
        else {}
    )
    return {
        "grossWeight": _as_decimal(package.get("grossWeight")),
        "baseQt": _as_int(weight_range.get("baseQt")),
        "stepQt": _as_int(weight_range.get("stepQt")),
        "stepWeight": _as_decimal(weight_range.get("stepWeight")),
    }


def _build_changes(
    before: dict[str, Any],
    target: dict[str, Any],
) -> list[dict[str, Any]]:
    specs = (
        (
            "itemPackage.grossWeight",
            "包装后重量",
            before.get("grossWeight"),
            target["grossWeight"],
            True,
        ),
        (
            "itemPackage.itemWeigthRange.baseQt",
            "买家购买",
            before.get("baseQt"),
            target["baseQt"],
            False,
        ),
        (
            "itemPackage.itemWeigthRange.stepQt",
            "买家每多买",
            before.get("stepQt"),
            target["stepQt"],
            False,
        ),
        (
            "itemPackage.itemWeigthRange.stepWeight",
            "增加重量",
            before.get("stepWeight"),
            target["stepWeight"],
            True,
        ),
    )
    changes: list[dict[str, Any]] = []
    for field, label, old, new, as_decimal in specs:
        if _values_equal(old, new, as_decimal=as_decimal):
            continue
        if as_decimal:
            changes.append(
                {
                    "field": field,
                    "label": label,
                    "before": _dec_str(_as_decimal(old)),
                    "after": _dec_str(_as_decimal(new)),
                }
            )
        else:
            changes.append(
                {
                    "field": field,
                    "label": label,
                    "before": _as_int(old),
                    "after": _as_int(new),
                }
            )
    return changes


def _summary_from_changes(changes: list[dict[str, Any]]) -> str:
    if not changes:
        return "包装重量与计重阶梯无变化"
    labels = "、".join(str(item.get("label") or "") for item in changes)
    return f"更新包装信息：{labels}（{len(changes)}项）"


def _update_item_with_special_handling(
    client: DhgateClient,
    *,
    payload: dict[str, Any],
    item_code: str,
    site_id: str,
) -> None:
    """先调 dh.item.update。促销中的商品先下架再更新并上架，其它敦煌错误原样抛出。"""
    try:
        update_item(client, payload)
        return
    except AppError as exc:
        message = format_dhgate_error_message(exc, fallback="更新商品失败")
        if _ERR_IN_PROMOTION not in message:
            raise

    # 促销中：下架 → 再更新 → 上架
    logger.info(
        "商品在促销中，先下架再更新后上架 itemCode=%s siteId=%s",
        item_code,
        site_id,
    )
    downshelf_items(client, item_codes=item_code, site_id=site_id)
    update_item(client, payload)
    upshelf_items(client, item_codes=item_code, site_id=site_id)


def _ensure_html_content(
    client: DhgateClient,
    detail: dict[str, Any],
    *,
    item_code: str,
    site_id: str,
) -> dict[str, Any]:
    item_base = detail.get("itemBase") if isinstance(detail.get("itemBase"), dict) else {}
    if item_base.get("htmlContent") not in (None, ""):
        return detail
    html_data = get_item_html(client, item_code=item_code, site_id=site_id)
    html_content = None
    if isinstance(html_data, dict):
        html_content = html_data.get("htmlContent")
    if html_content in (None, ""):
        return detail
    patched = dict(detail)
    base = dict(item_base)
    base["htmlContent"] = html_content
    patched["itemBase"] = base
    return patched


def _load_supplier_dhgate_stores(db: Session, supplier_id: int) -> dict[int, Store]:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise not_found("供应商不存在")

    rows = db.scalars(
        select(Store).where(
            Store.supplier_id == supplier_id,
            Store.store_type == StoreType.DHGATE.value,
            Store.deleted_at.is_(None),
        )
    ).all()
    if not rows:
        raise bad_request("该供应商下没有可用的敦煌店铺")

    stores: dict[int, Store] = {}
    for store in rows:
        if not store.access_token:
            logger.warning(
                "供应商店铺未授权敦煌，跳过缓存 store_id=%s identifier=%s",
                store.id,
                store.identifier,
            )
            continue
        stores[int(store.id)] = store
    if not stores:
        raise bad_request("该供应商下敦煌店铺均未授权，请先完成授权")
    return stores


def _find_product_for_item(
    db: Session,
    *,
    item_code: str,
    store_ids: set[int],
) -> ProductDh | None:
    """在供应商敦煌店铺范围内按 itemCode 查找本地商品；未找到返回 None。"""
    rows = db.scalars(
        select(ProductDh).where(
            ProductDh.item_code == item_code,
            ProductDh.store_id.in_(store_ids),
        )
    ).all()
    if not rows:
        return None

    # 同编码多站点时优先 EN
    preferred = [
        row
        for row in rows
        if str(row.site_id or "").upper() == _DEFAULT_SITE_ID
    ]
    candidates = preferred or list(rows)
    store_set = {int(row.store_id) for row in candidates}
    if len(store_set) > 1:
        raise bad_request(
            f"商品编码 {item_code} 在多个店铺中存在，无法唯一确定店铺"
        )
    return candidates[0]


def _fallback_store_id(store_ids: set[int]) -> int | None:
    """本地未命中商品时，取供应商下任一店铺写失败日志。"""
    if not store_ids:
        return None
    return int(sorted(store_ids)[0])


def _not_seed_error_message(item_code: str) -> str:
    return f"非种子商品；itemCode={item_code}"


def _get_client_for_store(
    clients: dict[int, DhgateClient],
    stores: dict[int, Store],
    db: Session,
    store_id: int,
) -> DhgateClient:
    cached = clients.get(store_id)
    if cached is not None:
        return cached
    store = stores.get(store_id)
    if store is None:
        raise bad_request(f"店铺 {store_id} 不在当前供应商敦煌店铺列表中，或未授权")
    client = DhgateClient(db, store)
    clients[store_id] = client
    return client


def _write_log(
    db: Session,
    *,
    store_id: int,
    item_code: str,
    site_id: str,
    operator_id: int | None,
    status: str,
    summary: str,
    changes: list[dict[str, Any]],
    error_message: str | None,
    product_dh_id: int | None,
) -> int | None:
    row = ProductDhUpdateLog(
        product_dh_id=product_dh_id,
        store_id=store_id,
        item_code=item_code,
        site_id=site_id,
        operator_id=operator_id,
        source=_SOURCE_BATCH_EXCEL,
        status=status,
        summary=summary,
        changes=changes or None,
        error_message=error_message,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row.id


def execute_dhgate_product_updates(
    db: Session,
    *,
    supplier_id: int,
    items: list[dict[str, str]],
    dry_run: bool = False,
    operator_id: int = 0,
) -> DhgateUpdateProductPublic:
    """
    按供应商加载敦煌店铺，再按 itemCode 定位店铺 token，
    逐条：get 详情 → 按官网字段改详情 → update 原样提交。

    items 每项字段名与官网一致，当前包装重量场景：
    itemCode / grossWeight / baseQt / stepQt / stepWeight

    官方 update 特殊错误处理：
    - 本地 product_dh 未找到：记失败，error_message=「非种子商品；itemCode=...」
    - 含「该产品正在参加促销活动」：下架 → 再 update → 上架
    - 其它敦煌接口错误：原样抛出

    dry_run=false：真实调敦煌更新，并同步本地 product_dh、写变更日志。
    dry_run=true：仅试跑对比，不写敦煌、不落库、不记日志。
    """
    if not items:
        raise bad_request("items 不能为空")
    if len(items) > _MAX_EXECUTE_ITEMS:
        raise bad_request(f"单次最多处理 {_MAX_EXECUTE_ITEMS} 条，请先小批量测试")

    stores = _load_supplier_dhgate_stores(db, supplier_id)
    store_ids = set(stores.keys())
    clients: dict[int, DhgateClient] = {}
    actor_id = _normalize_operator_id(operator_id)

    success_count = 0
    failed_items: list[DhgateUpdateProductFailedItem] = []

    for raw in items:
        code = str((raw or {}).get("itemCode") or "").strip()
        store_id: int | None = None
        site_id = _DEFAULT_SITE_ID
        product_dh_id: int | None = None

        try:
            target = _parse_package_item(raw if isinstance(raw, dict) else {})
            code = target["itemCode"]
            local = _find_product_for_item(
                db, item_code=code, store_ids=store_ids
            )
            if local is None:
                message = _not_seed_error_message(code)
                log_store_id = _fallback_store_id(store_ids)
                store_id = log_store_id
                log_id = None
                if not dry_run and log_store_id is not None:
                    try:
                        log_id = _write_log(
                            db,
                            store_id=log_store_id,
                            item_code=code,
                            site_id=site_id,
                            operator_id=actor_id,
                            status="failed",
                            summary="非种子商品",
                            changes=[],
                            error_message=message,
                            product_dh_id=None,
                        )
                    except Exception:
                        db.rollback()
                        logger.exception(
                            "写非种子商品失败日志异常 itemCode=%s", code
                        )
                failed_items.append(
                    DhgateUpdateProductFailedItem(
                        itemCode=code,
                        store_id=log_store_id,
                        error_message=message,
                        log_id=log_id,
                    )
                )
                continue

            store_id = int(local.store_id)
            site_id = (str(local.site_id or _DEFAULT_SITE_ID).strip().upper()
                       or _DEFAULT_SITE_ID)
            product_dh_id = local.id
            client = _get_client_for_store(clients, stores, db, store_id)

            detail = get_item(client, item_code=code, site_id=site_id)
            before = _read_package_fields(detail)
            changes = _build_changes(before, target)
            summary = _summary_from_changes(changes)

            if not changes:
                # 无差异：不算失败，也不记成功写库
                success_count += 1
                continue

            if dry_run:
                success_count += 1
                continue

            # get 偶发缺长描时补齐，仍保持「详情底稿」语义，不做 add 裁剪
            detail = _ensure_html_content(
                client, detail, item_code=code, site_id=site_id
            )
            patched = apply_package_weight_to_detail(
                detail,
                grossWeight=target["grossWeight"],
                baseQt=target["baseQt"],
                stepQt=target["stepQt"],
                stepWeight=target["stepWeight"],
            )
            payload = build_item_update_payload(
                patched, item_code=code, site_id=site_id
            )
            _update_item_with_special_handling(
                client,
                payload=payload,
                item_code=code,
                site_id=site_id,
            )

            fresh = get_item(client, item_code=code, site_id=site_id)
            saved = persist_item_detail(
                db,
                store_id=store_id,
                item_code=code,
                site_id=site_id,
                detail=fresh,
                is_seed=local.is_seed or "1",
            )
            product_dh_id = saved.get("product_id") or product_dh_id

            _write_log(
                db,
                store_id=store_id,
                item_code=code,
                site_id=site_id,
                operator_id=actor_id,
                status="success",
                summary=summary,
                changes=changes,
                error_message=None,
                product_dh_id=product_dh_id,
            )
            success_count += 1
        except AppError as exc:
            db.rollback()
            message = format_dhgate_error_message(exc, fallback="更新商品失败")
            logger.warning(
                "敦煌商品更新失败 supplier_id=%s itemCode=%s: %s",
                supplier_id,
                code,
                message,
            )
            if not dry_run and store_id is not None:
                try:
                    _write_log(
                        db,
                        store_id=store_id,
                        item_code=code or "",
                        site_id=site_id,
                        operator_id=actor_id,
                        status="failed",
                        summary="更新商品失败",
                        changes=[],
                        error_message=message,
                        product_dh_id=product_dh_id,
                    )
                except Exception:
                    db.rollback()
                    logger.exception("写更新失败日志异常 itemCode=%s", code)
            raise
        except Exception:
            db.rollback()
            logger.exception(
                "敦煌商品更新异常 supplier_id=%s itemCode=%s",
                supplier_id,
                code,
            )
            raise

    return DhgateUpdateProductPublic(
        supplier_id=supplier_id,
        dry_run=dry_run,
        success_count=success_count,
        failed_count=len(failed_items),
        failed_items=failed_items,
    )
