"""管理端发布商品：新增 / 裂变任务数据上传敦煌 dh.item.add。"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError, bad_request, forbidden, not_found
from app.models.mission import (
    FISSION_STATUS_FAILED,
    FISSION_STATUS_SUCCESS,
    MissionDataDhFission,
)
from app.models.product_dh import ProductDh
from app.models.user import User
from app.services.dhgate import add_item, get_dhgate_client, get_item_html
from app.services.dhgate.categories import get_category
from app.services.dhgate.client import DhgateClient
from app.services.dhgate.items import (
    _public_add_payload,
    _replace_main_image_with_tweaked,
    build_item_add_payload,
)
from app.services.dhgate.response import format_dhgate_error_message
from app.services.missions import _get_visible_mission, _require_supplier_actor


PUBLISH_TYPE_ADDNEW = "addnew"
PUBLISH_TYPE_ADDFISSION = "addfission"
# 自定义属性 / 品牌属性：类目列表外仍允许上送
_ALWAYS_ALLOWED_ATTR_IDS = frozenset({"11", "99"})


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _omit_none(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


def _looks_like_dhgate_get_detail(detail: dict[str, Any]) -> bool:
    return isinstance(detail.get("itemBase"), dict) or isinstance(
        detail.get("itemSkuList"), list
    )


def admin_detail_to_dhgate_detail(info: dict[str, Any]) -> dict[str, Any]:
    """把管理端 DhProductDetailPublic 形态（snake_case）转为接近 dh.item.get 的结构。"""
    if _looks_like_dhgate_get_detail(info):
        return deepcopy(info)

    weight_range = info.get("item_weight_range")
    package_weight: dict[str, Any] | None = None
    if isinstance(weight_range, dict):
        package_weight = _omit_none(
            {
                "baseQt": weight_range.get("base_qt"),
                "stepQt": weight_range.get("step_qt"),
                "stepWeight": weight_range.get("step_weight"),
            }
        )
        if not package_weight:
            package_weight = None

    item_base = _omit_none(
        {
            "itemName": info.get("item_name"),
            "shortDesc": info.get("short_desc"),
            "shortDesc1": info.get("short_desc1"),
            "shortDesc2": info.get("short_desc2"),
            "shortDesc3": info.get("short_desc3"),
            "shortDesc4": info.get("short_desc4"),
            "shortDesc5": info.get("short_desc5"),
            "htmlContent": info.get("html_content"),
            "keyWord1": info.get("key_word1"),
            "keyWord2": info.get("key_word2"),
            "keyWord3": info.get("key_word3"),
            "videoUrl": info.get("video_url") if info.get("video_url") is not None else "",
        }
    )

    item_package = _omit_none(
        {
            "grossWeight": info.get("gross_weight"),
            "length": info.get("length"),
            "width": info.get("width"),
            "height": info.get("height"),
            "measureId": info.get("measure_id"),
            "packingQuantity": info.get("packing_quantity"),
            "itemWeigthRange": package_weight,
        }
    )

    item_sale = _omit_none(
        {
            "minWholesaleQty": info.get("min_wholesale_qty"),
            "maxSaleQty": info.get("max_sale_qty"),
            "leadingTime": info.get("leading_time"),
            "priceConfigType": info.get("price_config_type"),
        }
    )

    images: list[dict[str, Any]] = []
    for img in info.get("item_img_list") or []:
        if not isinstance(img, dict):
            continue
        mapped = _omit_none(
            {
                "imgUrl": img.get("img_url"),
                "imgMd5": img.get("img_md5"),
                "type": img.get("type"),
            }
        )
        if mapped:
            images.append(mapped)

    attrs: list[dict[str, Any]] = []
    for attr in info.get("attr_list") or []:
        if not isinstance(attr, dict):
            continue
        attr_id = _as_str(attr.get("attr_id"))
        if not attr_id:
            continue
        values: list[dict[str, Any]] = []
        for val in attr.get("values") or []:
            if not isinstance(val, dict):
                continue
            mapped_val = _omit_none(
                {
                    "attrId": attr_id,
                    "attrValId": val.get("attr_val_id"),
                    "attrName": val.get("attr_name") or attr.get("attr_name"),
                    "lineAttrvalName": val.get("line_attrval_name"),
                    "lineAttrvalNameCn": val.get("line_attrval_name_cn"),
                    "picUrl": val.get("pic_url"),
                    "brandId": val.get("brand_id"),
                }
            )
            if mapped_val:
                values.append(mapped_val)
        is_price = _as_str(attr.get("is_price_attr"))
        mapped_attr = _omit_none(
            {
                "attrId": attr_id,
                "attrName": attr.get("attr_name"),
                "attrNameCn": attr.get("attr_name_cn"),
                "isbrand": attr.get("is_brand"),
                "isPriceAttr": is_price,
                "saleAttr": "1" if is_price == "1" else None,
                "itemAttrValList": values or None,
            }
        )
        attrs.append(mapped_attr)

    skus: list[dict[str, Any]] = []
    for sku in info.get("sku_list") or []:
        if not isinstance(sku, dict):
            continue
        attr_vals: list[dict[str, Any]] = []
        for val in sku.get("item_sku_attr_value_list") or []:
            if not isinstance(val, dict):
                continue
            mapped_val = _omit_none(
                {
                    "attrId": val.get("attr_id"),
                    "attrValId": val.get("attr_val_id"),
                    "attrValCode": val.get("attr_val_code"),
                    "sizeSpecType": val.get("size_spec_type"),
                }
            )
            if mapped_val:
                attr_vals.append(mapped_val)
        invent_list: list[dict[str, Any]] = []
        for inv in sku.get("item_sku_inventory_list") or []:
            if not isinstance(inv, dict):
                continue
            mapped_inv = _omit_none(
                {
                    "skuMD5": inv.get("sku_md5"),
                    "inventoryLocation": inv.get("inventory_location"),
                    "skuInventoryQty": inv.get("sku_inventory_qty"),
                }
            )
            if mapped_inv:
                invent_list.append(mapped_inv)
        shipto_prices: list[dict[str, Any]] = []
        for price in sku.get("shipto_country_price_list") or []:
            if not isinstance(price, dict):
                continue
            mapped_price = _omit_none(
                {
                    "regionCode": price.get("region_code"),
                    "retailPrice": price.get("retail_price"),
                }
            )
            if mapped_price:
                shipto_prices.append(mapped_price)
        mapped_sku = _omit_none(
            {
                "skuId": sku.get("sku_id"),
                "skuCode": sku.get("sku_code"),
                "skuMD5": sku.get("sku_md5"),
                "retailPrice": sku.get("retail_price"),
                "inventory": sku.get("inventory"),
                "saleStatus": sku.get("sale_status"),
                "picUrl": sku.get("pic_url"),
                "itemSkuAttrvalList": attr_vals or None,
                "itemSkuInvenList": invent_list or None,
                "shiptoCountryPriceList": shipto_prices or None,
            }
        )
        skus.append(mapped_sku)

    specs: list[dict[str, Any]] = []
    for spec in info.get("item_spec_self_def_list") or []:
        if not isinstance(spec, dict):
            continue
        mapped_spec = _omit_none(
            {
                "attrValId": spec.get("attr_val_id"),
                "specAttrName": spec.get("spec_attr_name"),
                "attrValName": spec.get("attr_val_name"),
                "picUrl": spec.get("pic_url"),
            }
        )
        if mapped_spec:
            specs.append(mapped_spec)

    wholesale: list[dict[str, Any]] = []
    for row in info.get("item_wholesale_range_list") or []:
        if not isinstance(row, dict):
            continue
        mapped_row = _omit_none(
            {
                "discount": row.get("discount"),
                "startQty": row.get("start_qty"),
            }
        )
        if mapped_row:
            wholesale.append(mapped_row)

    inventory = info.get("item_inventory")
    item_inventory: dict[str, Any] | None = None
    if isinstance(inventory, dict):
        locations: list[dict[str, Any]] = []
        for loc in inventory.get("inventory_location_list") or []:
            if not isinstance(loc, dict):
                continue
            mapped_loc = _omit_none(
                {
                    "sortVal": loc.get("sort_val"),
                    "leadingTime": loc.get("leading_time"),
                    "inventoryLocation": loc.get("inventory_location"),
                    "ifInTransit": loc.get("if_in_transit"),
                }
            )
            if mapped_loc:
                locations.append(mapped_loc)
        item_inventory = _omit_none(
            {
                "inventoryLocation": inventory.get("inventory_location"),
                "inventoryStatus": inventory.get("inventory_status"),
                "subtractStockType": inventory.get("subtract_stock_type"),
                "inventoryOriQty": inventory.get("inventory_ori_qty"),
                "inventoryQty": inventory.get("inventory_qty"),
                "inventoryLocationList": locations or None,
            }
        )

    shipto_settings: list[dict[str, Any]] = []
    for row in info.get("item_shipto_setting_list") or []:
        if not isinstance(row, dict):
            continue
        region_wholesale: list[dict[str, Any]] = []
        for wr in row.get("item_wholesale_range_list") or []:
            if not isinstance(wr, dict):
                continue
            mapped_wr = _omit_none(
                {
                    "discount": wr.get("discount"),
                    "startQty": wr.get("start_qty"),
                }
            )
            if mapped_wr:
                region_wholesale.append(mapped_wr)
        mapped_shipto = _omit_none(
            {
                "regionCode": row.get("region_code"),
                "shiptoCountryList": row.get("shipto_country_list"),
                "itemWholesaleRangeList": region_wholesale or None,
            }
        )
        if mapped_shipto:
            shipto_settings.append(mapped_shipto)

    attr_groups: list[dict[str, Any]] = []
    for group in info.get("item_attr_group_list") or []:
        if not isinstance(group, dict):
            continue
        details: list[dict[str, Any]] = []
        for detail_row in group.get("item_attrgroup_detail_list") or []:
            if not isinstance(detail_row, dict):
                continue
            mapped_detail = _omit_none(
                {
                    "attrId": detail_row.get("attr_id"),
                    "attrValId": detail_row.get("attr_val_id"),
                    "attrName": detail_row.get("attr_name"),
                    "attrNameCn": detail_row.get("attr_name_cn"),
                    "lineAttrvalName": detail_row.get("line_attrval_name"),
                    "lineAttrvalNameCn": detail_row.get("line_attrval_name_cn"),
                }
            )
            if mapped_detail:
                details.append(mapped_detail)
        if details:
            attr_groups.append({"itemAttrgroupDetailList": details})

    custom_info = info.get("item_custom_type_info")
    item_custom: dict[str, Any] | None = None
    if isinstance(custom_info, dict):
        custom_prices: list[dict[str, Any]] = []
        for price in custom_info.get("shipto_country_price_list") or []:
            if not isinstance(price, dict):
                continue
            mapped_price = _omit_none(
                {
                    "regionCode": price.get("region_code"),
                    "retailPrice": price.get("retail_price"),
                }
            )
            if mapped_price:
                custom_prices.append(mapped_price)
        item_custom = _omit_none(
            {
                "customType": custom_info.get("custom_type"),
                "retailPrice": custom_info.get("retail_price"),
                "minWholesaleQty": custom_info.get("min_wholesale_qty"),
                "maxSaleQty": custom_info.get("max_sale_qty"),
                "leadingTime": custom_info.get("leading_time"),
                "skuCode": custom_info.get("sku_code"),
                "saleStatus": custom_info.get("sale_status"),
                "shiptoCountryPriceList": custom_prices or None,
            }
        )

    detail: dict[str, Any] = _omit_none(
        {
            "itemCode": info.get("item_code"),
            "siteId": info.get("site_id") or "EN",
            "supplierId": info.get("supplier_id"),
            "catePubId": info.get("cate_pub_id"),
            "state": info.get("state"),
            "issample": info.get("issample"),
            "isDhOptimized": info.get("is_dh_optimized"),
            "vaildDay": info.get("vaild_day"),
            "shippingModelId": info.get("shipping_model_id"),
            "afterSaleTemplateId": info.get("after_sale_template_id"),
            "sizeTemplateId": info.get("size_template_id"),
            "itemGroupId": info.get("item_group_id"),
            "itemBase": item_base,
            "itemPackage": item_package,
            "itemSaleSetting": item_sale,
            "itemImgList": images,
            "itemAttrList": attrs,
            "itemSkuList": skus,
            "itemSpecSelfDefList": specs or None,
            "itemWholesaleRangeList": wholesale,
            "itemInventory": item_inventory,
            "itemAttrGroupList": attr_groups or None,
            "itemShiptoSettingList": shipto_settings or None,
            "itemCustomTypeInfo": item_custom,
        }
    )
    return detail


def _extract_item_code(added: Any) -> str | None:
    if not isinstance(added, dict):
        return None
    for key in ("itemCode", "item_code", "productId", "product_id"):
        code = _as_str(added.get(key))
        if code:
            return code
    nested = added.get("data")
    if isinstance(nested, dict):
        return _extract_item_code(nested)
    return None


def _main_image_already_tweaked(detail: dict[str, Any]) -> bool:
    """裂变编辑时主图微调会写入 original；有原图+现图则视为已微调。"""
    images = detail.get("item_img_list")
    if not isinstance(images, list):
        images = detail.get("itemImgList")
    if not isinstance(images, list) or not images:
        return False
    first = images[0]
    if not isinstance(first, dict):
        return False
    current_url = _as_str(first.get("img_url") or first.get("imgUrl"))
    if not current_url:
        return False
    original = first.get("original")
    if not isinstance(original, dict):
        return False
    return bool(_as_str(original.get("img_url") or original.get("imgUrl")))


def _read_html_content(detail: dict[str, Any]) -> str | None:
    """从管理端详情或 dh.item.get 形态中读取已有长描。"""
    direct = _as_str(detail.get("html_content"))
    if direct:
        return direct
    item_base = detail.get("itemBase")
    if isinstance(item_base, dict):
        return _as_str(item_base.get("htmlContent"))
    return None


def _fill_html_content_if_missing(
    db: Session,
    get_shape: dict[str, Any],
    *,
    source_store_id: int,
    source_item_code: str | None,
    site_id: str,
) -> dict[str, Any]:
    """
    与联调 fission/add 一致：本地详情常无完整长描时，
    用源店 token 调 dh.product.html.get 补齐 itemBase.htmlContent。
    """
    item_base = (
        get_shape.get("itemBase")
        if isinstance(get_shape.get("itemBase"), dict)
        else {}
    )
    if _as_str(item_base.get("htmlContent")):
        return get_shape

    item_code = _as_str(source_item_code) or _as_str(get_shape.get("itemCode"))
    if not item_code:
        return get_shape

    source_client = get_dhgate_client(db, source_store_id)
    html_data = get_item_html(
        source_client,
        item_code=item_code,
        site_id=site_id or "EN",
    )
    html_content = None
    if isinstance(html_data, dict):
        html_content = html_data.get("htmlContent")
    if html_content in (None, ""):
        return get_shape

    patched = dict(get_shape)
    base = dict(item_base)
    base["htmlContent"] = html_content
    patched["itemBase"] = base
    return patched


def _upload_dh_product_info(add_payload: dict[str, Any]) -> dict[str, Any] | None:
    """最终上送敦煌 dh.item.add 的参数（去掉 htmlContent，便于接口回传排查）。"""
    return _public_add_payload(add_payload)


def _attach_upload_dh_product_info(
    exc: AppError, add_payload: dict[str, Any]
) -> AppError:
    """发布失败时附带最终上送敦煌的商品参数。"""
    data = dict(exc.data) if isinstance(exc.data, dict) else {}
    data["upload_dh_product_info"] = _upload_dh_product_info(add_payload)
    return AppError(exc.status_code, exc.code, exc.message, data)


def _item_attr_id(item: dict[str, Any]) -> str | None:
    attr_id = item.get("attrId")
    if attr_id is not None and str(attr_id).strip():
        return str(attr_id).strip()
    values = item.get("itemAttrValList")
    if isinstance(values, list):
        for val in values:
            if not isinstance(val, dict):
                continue
            vid = val.get("attrId")
            if vid is not None and str(vid).strip():
                return str(vid).strip()
    return None


def _filter_item_attrs_by_category(
    client: DhgateClient,
    detail: dict[str, Any],
) -> dict[str, Any]:
    """只保留当前发布类目下的类目属性 + 自定义/品牌属性，去掉换类目后的残留。"""
    cate_pub_id = _as_str(detail.get("catePubId"))
    attrs = detail.get("itemAttrList")
    if not cate_pub_id or not isinstance(attrs, list) or not attrs:
        return detail
    try:
        cate = get_category(client, cate_pub_id=cate_pub_id)
    except AppError:
        return detail
    allowed = set(_ALWAYS_ALLOWED_ATTR_IDS)
    for row in cate.get("categoryPubAttrList") or []:
        if not isinstance(row, dict):
            continue
        attr_id = row.get("attrId")
        if attr_id is not None and str(attr_id).strip():
            allowed.add(str(attr_id).strip())
    filtered = [
        item
        for item in attrs
        if isinstance(item, dict)
        and (
            (aid := _item_attr_id(item)) is None or aid in allowed
        )
    ]
    out = dict(detail)
    out["itemAttrList"] = filtered
    return out


def _publish_detail_to_store(
    db: Session,
    *,
    store_id: int,
    detail: dict[str, Any],
    tweak_filename_code: str,
    html_source_store_id: int | None = None,
    html_source_item_code: str | None = None,
    site_id: str | None = None,
) -> dict[str, Any]:
    """组装 dh.item.add 入参并发布；缺长描时先补齐，主图未微调过时再微调上传。"""
    get_shape = admin_detail_to_dhgate_detail(detail)
    # 若详情已有长描（编辑器写入）则沿用；否则用源店 dh.product.html.get 补齐
    if not _read_html_content(detail):
        get_shape = _fill_html_content_if_missing(
            db,
            get_shape,
            source_store_id=html_source_store_id or store_id,
            source_item_code=html_source_item_code or tweak_filename_code,
            site_id=(
                _as_str(site_id)
                or _as_str(get_shape.get("siteId"))
                or _as_str(detail.get("site_id"))
                or "EN"
            ),
        )
    client = get_dhgate_client(db, store_id)
    get_shape = _filter_item_attrs_by_category(client, get_shape)
    add_payload = build_item_add_payload(get_shape)
    try:
        # 裂变编辑已微调主图（带 original）时跳过，直接用现图发布
        tweaked: dict[str, Any] | None = None
        if not _main_image_already_tweaked(detail):
            tweaked = _replace_main_image_with_tweaked(
                client,
                add_payload,
                item_code=tweak_filename_code or "new",
            )
        # 主图微调后即为实际上送体
        upload_info = _upload_dh_product_info(add_payload)
        added = add_item(client, add_payload)
        item_code = _extract_item_code(added)
        return {
            "added": added,
            "item_code": item_code,
            "tweaked_main_image": tweaked,
            "store_id": store_id,
            "skipped_main_image_tweak": tweaked is None,
            "upload_dh_product_info": upload_info,
        }
    except AppError as exc:
        raise _attach_upload_dh_product_info(exc, add_payload) from exc


def publish_product(
    db: Session,
    *,
    actor: User,
    publish_type: str,
    mission_data_fission_id: int | None,
    info: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    发布商品。

    - addfission：按任务数据 raw_json 发布，成功后写回 item_code / 裂变状态
    - addnew：按 info 发布（暂不落本地任务表）
    """
    ptype = (publish_type or PUBLISH_TYPE_ADDFISSION).strip().lower()
    if ptype not in {PUBLISH_TYPE_ADDNEW, PUBLISH_TYPE_ADDFISSION}:
        raise bad_request("type 仅支持 addnew / addfission")

    if ptype == PUBLISH_TYPE_ADDNEW:
        if not isinstance(info, dict) or not info:
            raise bad_request("type=addnew 时 info 必传")
        store_id = info.get("store_id")
        try:
            store_id_int = int(store_id)
        except (TypeError, ValueError):
            raise bad_request("info.store_id 无效") from None
        if actor.supplier_id is None:
            raise bad_request("当前账号未绑定供应商，无法发布商品")
        result = _publish_detail_to_store(
            db,
            store_id=store_id_int,
            detail=info,
            tweak_filename_code=_as_str(info.get("item_code")) or "addnew",
            html_source_store_id=store_id_int,
            html_source_item_code=_as_str(info.get("item_code")),
            site_id=_as_str(info.get("site_id")),
        )
        return {
            "type": ptype,
            "item_code": result.get("item_code"),
            "mission_data_fission_id": None,
            "fission_status": None,
            "upload_dh_product_info": result.get("upload_dh_product_info"),
        }

    # addfission
    if mission_data_fission_id is None or int(mission_data_fission_id) < 1:
        raise bad_request("type=addfission 时 mission_data_fission_id 必传")
    supplier_id = _require_supplier_actor(actor)
    row = db.get(MissionDataDhFission, int(mission_data_fission_id))
    if row is None or row.is_deleted:
        raise not_found("裂变任务数据不存在")
    if row.supplier_id != supplier_id:
        raise forbidden("只能操作本供应商的任务数据")
    _get_visible_mission(
        db,
        mission_id=row.mission_id,
        actor=actor,
        supplier_id=supplier_id,
    )
    if row.fission_status == FISSION_STATUS_SUCCESS:
        raise bad_request("该任务数据已裂变成功，请勿重复发布")

    raw_json = row.raw_json if isinstance(row.raw_json, dict) else None
    if not raw_json:
        raise bad_request("任务数据缺少 raw_json，无法发布")

    seed = db.get(ProductDh, row.seed_product_id)
    tweak_code = (seed.item_code if seed is not None else None) or "fission"
    # 长描必须从种子源店拉取（与联调 fission/add 一致），目标店可能跨店
    html_source_store_id = seed.store_id if seed is not None else row.store_id
    html_source_item_code = seed.item_code if seed is not None else None
    site_id = (
        _as_str(raw_json.get("site_id"))
        or (seed.site_id if seed is not None else None)
        or row.site_id
        or "EN"
    )

    try:
        result = _publish_detail_to_store(
            db,
            store_id=row.store_id,
            detail=raw_json,
            tweak_filename_code=str(tweak_code),
            html_source_store_id=html_source_store_id,
            html_source_item_code=html_source_item_code,
            site_id=site_id,
        )
        item_code = result.get("item_code")
        if not item_code:
            raise bad_request("敦煌发布成功但未返回 itemCode")
        row.item_code = item_code
        row.fission_status = FISSION_STATUS_SUCCESS
        row.fission_msg = None
        row.fission_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
        return {
            "type": ptype,
            "mission_data_fission_id": row.id,
            "item_code": item_code,
            "fission_status": row.fission_status,
            "upload_dh_product_info": result.get("upload_dh_product_info"),
        }
    except AppError as exc:
        row.fission_status = FISSION_STATUS_FAILED
        row.fission_msg = format_dhgate_error_message(exc, fallback="裂变发布失败")
        row.fission_at = datetime.now(timezone.utc)
        db.commit()
        data = dict(exc.data) if isinstance(exc.data, dict) else {}
        raise bad_request(row.fission_msg, data=data or None) from exc
    except Exception as exc:  # noqa: BLE001 — 写回失败状态后继续抛出
        row.fission_status = FISSION_STATUS_FAILED
        row.fission_msg = str(exc) or "裂变发布失败"
        row.fission_at = datetime.now(timezone.utc)
        db.commit()
        raise bad_request(row.fission_msg) from exc
