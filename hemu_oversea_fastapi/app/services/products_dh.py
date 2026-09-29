"""敦煌商品详情落库（product_dh）。

由 dh.item.get 结果 upsert 到 product_dh：
列表列、sku_json（itemSkuList）、raw_json（完整响应）。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, bad_request
from app.models.product_dh import ProductDh
from app.models.store import Store
from app.services.dhgate.client import DhgateClient
from app.services.dhgate.items import get_item
from app.services.dhgate.store_context import (
    get_dhgate_client_by_identifier,
    get_dhgate_store_by_identifier,
)

logger = logging.getLogger("app")

_BJ = ZoneInfo("Asia/Shanghai")
_DEFAULT_SITE_ID = "EN"
_SYNC_OK = "1"
_SYNC_FAIL = "0"
_SYNC_OK_DESC = "同步成功"
_SYNC_DESC_MAX_LEN = 512


def _clip_sync_desc(message: str | None) -> str:
    text = (message or "").strip() or "未知错误"
    if len(text) <= _SYNC_DESC_MAX_LEN:
        return text
    return text[: _SYNC_DESC_MAX_LEN - 3] + "..."


def _get_product_row(
    db: Session,
    *,
    store_id: int,
    item_code: str,
    site_id: str,
) -> ProductDh | None:
    return db.scalar(
        select(ProductDh).where(
            ProductDh.store_id == store_id,
            ProductDh.item_code == item_code,
            ProductDh.site_id == site_id,
        )
    )


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text != "" else None


def _spec_self_def_lookup(detail: dict[str, Any]) -> dict[str, tuple[str, str]]:
    """自定义规格 attrValId → (specAttrName, attrValName)，用于 SKU 规格文案。"""
    mapping: dict[str, tuple[str, str]] = {}
    spec_list = detail.get("itemSpecSelfDefList")
    if not isinstance(spec_list, list):
        return mapping
    for item in spec_list:
        if not isinstance(item, dict):
            continue
        attr_val_id = _as_str(item.get("attrValId"))
        if not attr_val_id:
            continue
        spec_name = _as_str(item.get("specAttrName")) or "Options"
        val_name = _as_str(item.get("attrValName")) or attr_val_id
        mapping[attr_val_id] = (spec_name, val_name)
    return mapping


def _attr_combo_text(
    combo: list[dict[str, Any]],
    spec_lookup: dict[str, tuple[str, str]],
) -> str | None:
    parts: list[str] = []
    for item in combo:
        if not isinstance(item, dict):
            continue
        attr_id = _as_str(item.get("attrId")) or ""
        attr_val_id = _as_str(item.get("attrValId")) or ""
        spec_name, spec_val = spec_lookup.get(attr_val_id, ("", ""))
        attr_name = (
            _as_str(item.get("attrName"))
            or spec_name
            or attr_id
            or "attr"
        )
        val_name = (
            _as_str(item.get("attrValName"))
            or _as_str(item.get("lineAttrvalName"))
            or spec_val
            or attr_val_id
        )
        if attr_name or val_name:
            parts.append(f"{attr_name}:{val_name}")
    return ";".join(parts) if parts else None


def _item_sku_list(detail: dict[str, Any]) -> list | None:
    sku_list = detail.get("itemSkuList")
    if isinstance(sku_list, list):
        return sku_list
    return None


def _main_image_url(detail: dict[str, Any]) -> str | None:
    images = detail.get("itemImgList")
    if not isinstance(images, list):
        return None
    for img in images:
        if not isinstance(img, dict):
            continue
        img_url = _as_str(img.get("imgUrl"))
        img_md5 = _as_str(img.get("imgMd5"))
        if img_url and img_md5:
            return img_url
    return None


def _supplier_id_for_store(db: Session, store_id: int) -> int:
    store = db.get(Store, store_id)
    if store is None or store.is_deleted:
        raise bad_request("店铺不存在")
    if store.supplier_id is None:
        raise bad_request("店铺未绑定供应商")
    return store.supplier_id


def _upsert_product_row(
    db: Session,
    *,
    store_id: int,
    item_code: str,
    site_id: str,
    detail: dict[str, Any],
    is_seed: str = "1",
) -> ProductDh:
    item_base = detail.get("itemBase") if isinstance(detail.get("itemBase"), dict) else {}
    supplier_id = _supplier_id_for_store(db, store_id)
    values = {
        "supplier_id": supplier_id,
        "cate_pub_id": _as_str(detail.get("catePubId")),
        "state": _as_str(detail.get("state")),
        "item_name": _as_str(item_base.get("itemName")),
        "main_image_url": _main_image_url(detail),
        "sku_json": _item_sku_list(detail),
        "raw_json": detail,
        "is_seed": is_seed,
        "sync_state": _SYNC_OK,
        "last_synced_at": datetime.now(_BJ),
    }

    row = _get_product_row(
        db, store_id=store_id, item_code=item_code, site_id=site_id
    )
    if row is None:
        row = ProductDh(
            store_id=store_id,
            item_code=item_code,
            site_id=site_id,
            **values,
        )
        db.add(row)
        db.flush()
    else:
        # 同 store + item_code + site 重复同步时覆盖旧主表数据
        for key, value in values.items():
            setattr(row, key, value)
        db.flush()
    return row


def mark_product_sync_failed(
    db: Session,
    *,
    store_id: int,
    item_code: str,
    site_id: str,
    is_seed: str = "1",
) -> ProductDh:
    """同步失败时只更新主表同步状态，不覆盖已有详情。"""
    code = _as_str(item_code)
    site = (_as_str(site_id) or _DEFAULT_SITE_ID).upper()
    if not code:
        raise bad_request("item_code 不能为空")

    now = datetime.now(_BJ)
    supplier_id = _supplier_id_for_store(db, store_id)
    row = _get_product_row(db, store_id=store_id, item_code=code, site_id=site)
    if row is None:
        row = ProductDh(
            store_id=store_id,
            supplier_id=supplier_id,
            item_code=code,
            site_id=site,
            is_seed=is_seed,
            sync_state=_SYNC_FAIL,
            last_synced_at=now,
        )
        db.add(row)
    else:
        row.supplier_id = supplier_id
        row.sync_state = _SYNC_FAIL
        row.last_synced_at = now
        if is_seed == "1":
            row.is_seed = "1"
    db.commit()
    db.refresh(row)
    return row


def _try_mark_sync_failed(
    db: Session,
    *,
    store_identifier: str | None,
    item_code: str | None,
    site_id: str,
    clients: dict[str, DhgateClient],
) -> ProductDh | None:
    """尽量将失败状态写入主表；无法解析店铺时跳过。"""
    if not store_identifier or not item_code:
        return None
    try:
        store_id: int | None = None
        client = clients.get(store_identifier)
        if client is not None:
            store_id = client.store.id
        else:
            store = get_dhgate_store_by_identifier(db, store_identifier)
            store_id = store.id
        return mark_product_sync_failed(
            db,
            store_id=store_id,
            item_code=item_code,
            site_id=site_id,
            is_seed="1",
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning(
            "写入同步失败状态失败 store_identifier=%s item_code=%s: %s",
            store_identifier,
            item_code,
            exc,
        )
        return None


def persist_item_detail(
    db: Session,
    *,
    store_id: int,
    item_code: str,
    site_id: str,
    detail: dict[str, Any],
    is_seed: str = "1",
) -> dict[str, Any]:
    """将单条 dh.item.get 结果写入 product_dh（同键 upsert）。"""
    code = _as_str(item_code)
    site = (_as_str(site_id) or _DEFAULT_SITE_ID).upper()
    if not code:
        raise bad_request("item_code 不能为空")

    product = _upsert_product_row(
        db,
        store_id=store_id,
        item_code=code,
        site_id=site,
        detail=detail,
        is_seed=is_seed,
    )
    db.commit()
    db.refresh(product)

    return {
        "product_id": product.id,
        "store_id": product.store_id,
        "item_code": product.item_code,
        "site_id": product.site_id,
        "is_seed": product.is_seed,
        "item_name": product.item_name,
        "sync_state": product.sync_state,
        "sync_state_desc": _SYNC_OK_DESC,
    }


def sync_products_dh(
    db: Session,
    *,
    items: list[dict[str, Any]],
    site_id_default: str = _DEFAULT_SITE_ID,
) -> dict[str, Any]:
    """
    多店铺商品详情同步：逐条调用 dh.item.get 并落库。

    items 元素需含 store_identifier（stores.identifier）、item_code；
    可选 site_id（默认 EN）。
    同 store+item_code+site 重复时覆盖旧数据；
    单条失败不中断整批，并在 product_dh 写入 sync_state=0。失败原因只出现在返回结果里。
    """
    if not items:
        raise bad_request("items 不能为空")

    success_list: list[dict[str, Any]] = []
    failed_list: list[dict[str, Any]] = []
    raw_calls: list[dict[str, Any]] = []

    # 同 identifier 复用 client，减少重复取 token
    clients: dict[str, DhgateClient] = {}
    total = len(items)

    for index, item in enumerate(items):
        store_identifier = _as_str(item.get("store_identifier"))
        item_code = _as_str(item.get("item_code"))
        site_id = (_as_str(item.get("site_id")) or site_id_default).upper()
        try:
            if not store_identifier:
                raise bad_request("store_identifier 不能为空")
            if not item_code:
                raise bad_request("item_code 不能为空")

            client = clients.get(store_identifier)
            if client is None:
                client = get_dhgate_client_by_identifier(db, store_identifier)
                client.clear_call_history()
                clients[store_identifier] = client

            before_calls = len(client.call_history)
            detail = get_item(client, item_code=item_code, site_id=site_id)
            raw_calls.extend(client.call_history[before_calls:])

            saved = persist_item_detail(
                db,
                store_id=client.store.id,
                item_code=item_code,
                site_id=site_id,
                detail=detail,
                is_seed="1",
            )
            saved["store_identifier"] = store_identifier
            saved["sync_state"] = _SYNC_OK
            saved["sync_state_desc"] = _SYNC_OK_DESC
            success_list.append(saved)
        except AppError as exc:
            db.rollback()
            fail_row = _try_mark_sync_failed(
                db,
                store_identifier=store_identifier,
                item_code=item_code,
                site_id=site_id,
                clients=clients,
            )
            failed_list.append(
                {
                    "index": index,
                    "store_identifier": store_identifier,
                    "item_code": item_code,
                    "site_id": site_id,
                    "message": exc.message,
                    "code": exc.code,
                    "product_id": fail_row.id if fail_row else None,
                    "sync_state": _SYNC_FAIL,
                    "sync_state_desc": _clip_sync_desc(exc.message),
                }
            )
            logger.warning(
                "商品同步失败 store_identifier=%s item_code=%s: %s",
                store_identifier,
                item_code,
                exc.message,
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            fail_row = _try_mark_sync_failed(
                db,
                store_identifier=store_identifier,
                item_code=item_code,
                site_id=site_id,
                clients=clients,
            )
            failed_list.append(
                {
                    "index": index,
                    "store_identifier": store_identifier,
                    "item_code": item_code,
                    "site_id": site_id,
                    "message": str(exc),
                    "product_id": fail_row.id if fail_row else None,
                    "sync_state": _SYNC_FAIL,
                    "sync_state_desc": _clip_sync_desc(str(exc)),
                }
            )
            logger.exception(
                "商品同步异常 store_identifier=%s item_code=%s",
                store_identifier,
                item_code,
            )
        finally:
            logger.info("当前同步进度: %s/%s", index + 1, total)

    return {
        "success": success_list,
        "failed": failed_list,
        "success_count": len(success_list),
        "failed_count": len(failed_list),
        "raw_calls": raw_calls,
    }


def find_missing_product_sync_items(
    db: Session,
    *,
    items: list[dict[str, Any]],
    site_id_default: str = _DEFAULT_SITE_ID,
) -> list[dict[str, str]]:
    """
    对照 product_dh，找出本次 items 中尚未入库的 (store_identifier, item_code)。

    判定键：store_id + item_code + site_id（默认 EN）。
    店铺 identifier 在 stores 中不存在时，视为遗漏（后续同步会失败并记入 failed）。
    """
    if not items:
        return []

    identifiers = sorted(
        {
            key
            for item in items
            if (key := _as_str(item.get("store_identifier"))) is not None
        }
    )
    store_id_by_identifier: dict[str, int] = {}
    if identifiers:
        rows = db.scalars(
            select(Store).where(
                Store.identifier.in_(identifiers),
                Store.deleted_at.is_(None),
            )
        ).all()
        store_id_by_identifier = {row.identifier: row.id for row in rows}

    store_ids = list(store_id_by_identifier.values())
    existing: set[tuple[int, str, str]] = set()
    if store_ids:
        product_rows = db.execute(
            select(ProductDh.store_id, ProductDh.item_code, ProductDh.site_id).where(
                ProductDh.store_id.in_(store_ids)
            )
        ).all()
        existing = {
            (int(store_id), str(item_code), str(site_id).upper())
            for store_id, item_code, site_id in product_rows
        }

    missing: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in items:
        store_identifier = _as_str(item.get("store_identifier"))
        item_code = _as_str(item.get("item_code"))
        site_id = (_as_str(item.get("site_id")) or site_id_default).upper()
        if not store_identifier or not item_code:
            continue
        dedupe_key = (store_identifier, item_code, site_id)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        store_id = store_id_by_identifier.get(store_identifier)
        if store_id is not None and (store_id, item_code, site_id) in existing:
            continue
        missing.append(
            {
                "store_identifier": store_identifier,
                "item_code": item_code,
                "site_id": site_id,
            }
        )
    return missing


def summarize_sync_result(
    sync_result: dict[str, Any],
    *,
    missing_items: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """精简同步结果：仅返回成功/失败/遗漏补充数量与遗漏明细。"""
    missing = missing_items or []
    return {
        "success_count": int(sync_result.get("success_count") or 0),
        "failed_count": int(sync_result.get("failed_count") or 0),
        "missing_count": len(missing),
        "missing_items": missing,
    }
