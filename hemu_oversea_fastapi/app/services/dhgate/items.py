"""敦煌 Product API（卖家产品）封装。

文档：
- dh.item.get$2.0（卖家获取产品详情）
  https://open.dhgate.com/docs/api/detail/7ef9fd6dd5374492babbe5a74894b343
- dh.item.group.list$2.0（获取产品组列表）
  https://open.dhgate.com/docs/api/detail/79ddc34ed44347058fda6f7742db63b9
- dh.product.html.get$1.0（获取产品长描内容）
  https://open.dhgate.com/docs/api/detail/0c7a6c7045f44a5c97cc44bc0e822fce
- dh.item.add$2.0（卖家发布产品信息）
  https://open.dhgate.com/docs/api/detail/7547475966da4fbdaca30aa956f8e218
- dh.item.aftersale.list$2.0（获取售后模板列表）
  https://open.dhgate.com/docs/api/detail/d1ce0879df0a4564a75cbf0e1af7c4b2
- dh.shipping.template.list$2.0（卖家获取运费模版列表）
  https://open.dhgate.com/docs/api/detail/f0327a8a79684b138d324b30f39b6777
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from app.core.errors import AppError, bad_request
from app.services.dhgate.client import DhgateClient
from app.services.dhgate.logistics import list_shipping_templates

_DEFAULT_SITE_ID = "EN"
_ALLOWED_SITE_IDS = frozenset({"EN", "RU", "ES", "ID"})
# 敦煌自定义属性 attrId 固定为 11
_CUSTOM_ATTR_ID = "11"

# dh.item.add 顶层标量（vaildDay 文档写暂不使用，发布不传）
_ADD_SCALAR_KEYS = (
    "catePubId",
    "shippingModelId",
    "afterSaleTemplateId",
    "sizeTemplateId",
    "itemGroupId",
    "siteId",
    "privateProd",
    "issample",
    "customType",
)

_ITEM_BASE_KEYS = (
    "itemName",
    "shortDesc1",
    "shortDesc2",
    "shortDesc3",
    "shortDesc4",
    "shortDesc5",
    "htmlContent",
    "keyWord1",
    "keyWord2",
    "keyWord3",
    "videoUrl",
)

_ITEM_PACKAGE_KEYS = (
    "height",
    "length",
    "width",
    "grossWeight",
    "measureId",
    "packingQuantity",
    "itemWeigthRange",
)

_ITEM_SALE_SETTING_KEYS = (
    "leadingTime",
    "maxSaleQty",
    "minWholesaleQty",
    "priceConfigType",
)

_ITEM_IMG_KEYS = ("imgMd5", "imgUrl", "type")

_ITEM_ATTR_KEYS = ("isbrand", "saleAttr", "buyAttr", "itemAttrValList")
_ITEM_ATTR_VAL_KEYS = (
    "brandId",
    "attrId",
    "attrName",
    "attrValId",
    "picUrl",
    "lineAttrvalName",
    "lineAttrvalNameCn",
)

_ITEM_SKU_KEYS = (
    "retailPrice",
    "saleStatus",
    "inventory",
    "skuCode",
    "itemSkuAttrvalList",
    "shiptoCountryPriceList",
    "itemSkuInvenList",
    "inventoryLocationPriceList",
)
_ITEM_SKU_ATTRVAL_KEYS = ("attrId", "attrValId", "sizeSpecType")
_ITEM_SPEC_SELF_DEF_KEYS = ("attrValName", "picUrl", "attrValId")

_REQUIRED_ADD_KEYS = (
    "catePubId",
    "itemBase",
    "itemPackage",
    "itemSaleSetting",
    "itemImgList",
    "itemAttrList",
    "itemSkuList",
    "itemWholesaleRangeList",
    "shippingModelId",
)

# 文档标「必须」但官方示例/说明可按有无传：空则不发
# issample 按详情原样复制（含 0），不因文档取值说明而改写或丢弃
_OPTIONAL_IF_EMPTY_KEYS = (
    "itemAttrGroupList",
    "itemSpecSelfDefList",
    "itemShiptoSettingList",
    "itemCustomTypeInfo",
    "itemInventory",
    "afterSaleTemplateId",
    "sizeTemplateId",
    "itemGroupId",
    "privateProd",
    "customType",
)


def get_item(
    client: DhgateClient,
    *,
    item_code: str,
    site_id: str = _DEFAULT_SITE_ID,
) -> dict[str, Any]:
    """
    获取卖家产品详情。

    method: dh.item.get
    version: 2.0

    item_code 通常来自 dh.item.list；site_id 默认 EN（英语站）。
    """
    code = str(item_code or "").strip()
    if not code:
        raise bad_request("item_code 不能为空（商品编码 itemCode）")

    site = _normalize_site_id(site_id)
    return client.call(
        "dh.item.get",
        version="2.0",
        params={
            "itemCode": code,
            "siteId": site,
        },
        http_method="GET",
    )


def list_item_groups(
    client: DhgateClient,
    *,
    page_no: int = 1,
    page_size: int = 20,
    contain_child_group: bool | None = None,
    parent_group_id: str | None = None,
    group_cn_name: str | None = None,
    group_en_name: str | None = None,
) -> dict[str, Any]:
    """
    获取卖家产品组列表。

    method: dh.item.group.list
    version: 2.0
    官方必填 pageNo、pageSize；Java 示例为 POST。
    返回 itemGroupList、count、pageTotal；列表项 groupId 对应发布入参 itemGroupId。
    containChildGroup=true 时列表项带 itemChildGroupList 子分组。
    """
    if page_no < 1:
        raise bad_request("page_no 不能小于 1")
    if page_size < 1 or page_size > 200:
        raise bad_request("page_size 须在 1～200 之间")

    include_children = True if contain_child_group is None else contain_child_group
    params: dict[str, Any] = {
        "pageNo": page_no,
        "pageSize": page_size,
        "containChildGroup": "true" if include_children else "false",
    }
    parent_id = str(parent_group_id or "").strip()
    if parent_id:
        params["parentGroupId"] = parent_id
    cn_name = str(group_cn_name or "").strip()
    if cn_name:
        params["groupCnName"] = cn_name
    en_name = str(group_en_name or "").strip()
    if en_name:
        params["groupEnName"] = en_name

    return client.call(
        "dh.item.group.list",
        version="2.0",
        params=params,
        http_method="POST",
    )


def get_item_html(
    client: DhgateClient,
    *,
    item_code: str,
    site_id: str = _DEFAULT_SITE_ID,
) -> dict[str, Any]:
    """
    获取产品长描内容。

    method: dh.product.html.get
    version: 1.0
    官方入参为 itemcode；site_id 与详情接口对齐，平台侧不使用。
    """
    code = str(item_code or "").strip()
    if not code:
        raise bad_request("item_code 不能为空（商品编码 itemCode）")
    _normalize_site_id(site_id)
    return client.call(
        "dh.product.html.get",
        version="1.0",
        params={"itemcode": code},
        http_method="POST",
    )


def list_item_aftersale(client: DhgateClient) -> dict[str, Any]:
    """
    获取售后模板列表。

    method: dh.item.aftersale.list
    version: 2.0
    官方无业务入参，仅公共参数；Java 示例为 POST。
    """
    return client.call(
        "dh.item.aftersale.list",
        version="2.0",
        params={},
        http_method="POST",
    )


def add_item(client: DhgateClient, payload: dict[str, Any]) -> dict[str, Any]:
    """
    发布产品。

    method: dh.item.add
    version: 2.0
    仅支持 POST；复杂对象由客户端 JSON 序列化后提交。
    """
    if not payload:
        raise bad_request("dh.item.add 入参不能为空")
    return client.call(
        "dh.item.add",
        version="2.0",
        params=payload,
        http_method="POST",
    )


def apply_fission_update_info(
    detail: dict[str, Any],
    update_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """用 update_info 覆盖种子详情中的对应字段，返回副本（不改原详情）。"""
    updated = deepcopy(detail) if isinstance(detail, dict) else {}
    item_base = updated.get("itemBase")
    if not isinstance(item_base, dict):
        item_base = {}
        updated["itemBase"] = item_base
    _apply_fission_update_info(updated, item_base, update_info or {})
    return updated


def fission_add_item(
    source_client: DhgateClient,
    *,
    item_code: str,
    target_client_factory: Callable[[], DhgateClient],
    update_info: dict[str, Any] | None = None,
    site_id: str = _DEFAULT_SITE_ID,
) -> dict[str, Any]:
    """
    源店 dh.item.get + dh.product.html.get → update_info 覆盖 → 目标店微调主图后 dh.item.add。

    第一张主图会调用相册微调上传替换 imgUrl/imgMd5，避免原样上送被判重复。
    update_info.afterSaleTemplateId / shippingTempId 有值时直接写入发布体，不再拉模板列表；
    未传时：同店沿用原 ID，跨店取目标店默认售后模板、新手运费模板（modelType=10）。
    target_client_factory 在详情组装完成后再调用，避免目标店校验失败时拿不到原详情。
    不抛业务异常：失败时 error 为原因，同时尽量带回 original_detail / add_payload。
    """
    original_detail: dict[str, Any] | None = None
    add_payload: dict[str, Any] | None = None
    aftersale_list: Any = None
    shipping_template_list: Any = None
    tweaked_main_image: dict[str, Any] | None = None
    added: dict[str, Any] | None = None
    try:
        original_detail = get_item(
            source_client,
            item_code=item_code,
            site_id=site_id,
        )
        html_data = get_item_html(
            source_client,
            item_code=item_code,
            site_id=site_id,
        )
        html_content = None
        if isinstance(html_data, dict) and "htmlContent" in html_data:
            html_content = html_data.get("htmlContent")
        updated = apply_fission_update_info(original_detail, update_info)
        item_base = updated.get("itemBase")
        if not isinstance(item_base, dict):
            item_base = {}
            updated["itemBase"] = item_base
        if html_content is not None:
            item_base["htmlContent"] = html_content
        add_payload = build_item_add_payload(updated)
        target_client = target_client_factory()
        aftersale_list = _apply_aftersale_template_for_target(
            source_client,
            target_client,
            add_payload,
            override_id=(update_info or {}).get("afterSaleTemplateId"),
        )
        shipping_template_list = _apply_shipping_template_for_target(
            source_client,
            target_client,
            add_payload,
            override_id=(update_info or {}).get("shippingTempId"),
        )
        tweaked_main_image = _replace_main_image_with_tweaked(
            target_client,
            add_payload,
            item_code=item_code,
        )
        added = add_item(target_client, add_payload)
        return {
            "original_detail": original_detail,
            "aftersale_list": aftersale_list,
            "shipping_template_list": shipping_template_list,
            "tweaked_main_image": tweaked_main_image,
            "add_payload": _public_add_payload(add_payload),
            "added": added,
            "error": None,
            "error_detail": None,
        }
    except AppError as exc:
        return {
            "original_detail": original_detail,
            "aftersale_list": aftersale_list,
            "shipping_template_list": shipping_template_list,
            "tweaked_main_image": tweaked_main_image,
            "add_payload": _public_add_payload(add_payload),
            "added": added,
            "error": _fission_error_message(exc),
            "error_detail": _fission_error_detail(exc),
        }


def _public_add_payload(add_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """接口回传发布体时去掉长描，避免把 htmlContent 打印出来。"""
    if not isinstance(add_payload, dict):
        return add_payload
    public = deepcopy(add_payload)
    item_base = public.get("itemBase")
    if isinstance(item_base, dict):
        item_base.pop("htmlContent", None)
    return public


def _apply_aftersale_template_for_target(
    source_client: DhgateClient,
    target_client: DhgateClient,
    payload: dict[str, Any],
    *,
    override_id: str | None = None,
) -> list[dict[str, Any]] | None:
    """指定 ID 直接使用；否则同店沿用原值，跨店取目标店默认售后模板。"""
    specified = _normalize_optional_id(override_id)
    if specified:
        payload["afterSaleTemplateId"] = specified
        return None
    if _is_same_fission_store(source_client, target_client):
        return None

    data = list_item_aftersale(target_client)
    templates = data.get("afterSaleList") if isinstance(data, dict) else None
    if not isinstance(templates, list):
        templates = []
    payload["afterSaleTemplateId"] = _pick_default_aftersale_template_id(templates)
    return templates


def _apply_shipping_template_for_target(
    source_client: DhgateClient,
    target_client: DhgateClient,
    payload: dict[str, Any],
    *,
    override_id: str | None = None,
) -> list[dict[str, Any]] | None:
    """指定 ID 直接使用；否则同店沿用原值，跨店取目标店新手运费模板。"""
    specified = _normalize_optional_id(override_id)
    if specified:
        payload["shippingModelId"] = specified
        return None
    if _is_same_fission_store(source_client, target_client):
        return None

    data = list_shipping_templates(target_client)
    templates = data.get("shippingModelList") if isinstance(data, dict) else None
    if not isinstance(templates, list):
        templates = []
    payload["shippingModelId"] = _pick_default_shipping_template_id(templates)
    return templates


def _normalize_optional_id(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _is_same_fission_store(
    source_client: DhgateClient,
    target_client: DhgateClient,
) -> bool:
    source_store_id = getattr(getattr(source_client, "store", None), "id", None)
    target_store_id = getattr(getattr(target_client, "store", None), "id", None)
    return source_store_id is not None and source_store_id == target_store_id


def _pick_default_aftersale_template_id(templates: list[Any]) -> str:
    if not templates:
        raise bad_request("目标店铺没有售后模板，无法裂变发布")
    for item in templates:
        if not isinstance(item, dict):
            continue
        if _is_aftersale_deleted(item):
            continue
        if not _is_flag_on(item.get("ifTemplateDefault")):
            continue
        template_id = str(item.get("afterSaleTemplateId") or "").strip()
        if template_id:
            return template_id
    raise bad_request("目标店铺没有默认售后模板，无法裂变发布")


_DEFAULT_SHIPPING_MODEL_TYPE = "10"


def _pick_default_shipping_template_id(templates: list[Any]) -> str:
    if not templates:
        raise bad_request("目标店铺没有运费模板，无法裂变发布")
    for item in templates:
        if not isinstance(item, dict):
            continue
        if str(item.get("modelType") or "").strip() != _DEFAULT_SHIPPING_MODEL_TYPE:
            continue
        template_id = str(item.get("shippingTempId") or "").strip()
        if template_id:
            return template_id
    raise bad_request("目标店铺没有默认运费模板（新手运费模板），无法裂变发布")


def _is_aftersale_deleted(item: dict[str, Any]) -> bool:
    status = item.get("status")
    if status is None:
        return False
    return str(status).strip() in {"0", "false", "False"}


def _is_flag_on(value: Any) -> bool:
    if value is True or value == 1:
        return True
    return str(value).strip() == "1"


def _replace_main_image_with_tweaked(
    client: DhgateClient,
    payload: dict[str, Any],
    *,
    item_code: str,
) -> dict[str, Any]:
    """用目标店微调上传后的 imgUrl/imgMd5 替换发布体第一张主图。"""
    from app.services.dhgate.album import tweak_and_upload_from_url

    images = payload.get("itemImgList")
    if not isinstance(images, list) or not images:
        raise bad_request("发布体缺少主图 itemImgList，无法微调替换")
    first = images[0]
    if not isinstance(first, dict) or not first.get("imgUrl"):
        raise bad_request("发布体第一张主图 imgUrl 为空，无法微调替换")

    tweaked = tweak_and_upload_from_url(
        client,
        image_url=str(first.get("imgUrl")),
        image_filename=f"tweak_{item_code}.jpg",
    )
    uploaded = tweaked.get("upload") if isinstance(tweaked.get("upload"), dict) else {}
    new_url = uploaded.get("imgUrl")
    new_md5 = uploaded.get("imgMd5")
    if not new_url or not new_md5:
        raise bad_request("微调主图已上传，但未返回 imgUrl/imgMd5")

    replaced = dict(first)
    replaced["imgUrl"] = new_url
    replaced["imgMd5"] = new_md5
    payload["itemImgList"] = [replaced, *images[1:]]
    return tweaked


def build_item_add_payload(
    detail: dict[str, Any],
    *,
    update_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """把 dh.item.get 详情裁剪/映射为 dh.item.add 入参。"""
    if not isinstance(detail, dict) or not detail:
        raise bad_request("种子商品详情为空，无法裂变发布")

    working = apply_fission_update_info(detail, update_info) if update_info else detail

    payload: dict[str, Any] = {}
    for key in _ADD_SCALAR_KEYS:
        value = working.get(key)
        if value not in (None, ""):
            payload[key] = value

    item_base = _copy_keys(
        working.get("itemBase") if isinstance(working.get("itemBase"), dict) else {},
        _ITEM_BASE_KEYS,
        keep_empty_keys=("videoUrl", "htmlContent"),
    )
    item_base.setdefault("videoUrl", "")
    payload["itemBase"] = item_base

    payload["itemPackage"] = _copy_keys(
        working.get("itemPackage") if isinstance(working.get("itemPackage"), dict) else {},
        _ITEM_PACKAGE_KEYS,
    )
    payload["itemSaleSetting"] = _copy_keys(
        working.get("itemSaleSetting")
        if isinstance(working.get("itemSaleSetting"), dict)
        else {},
        _ITEM_SALE_SETTING_KEYS,
    )

    images = _map_item_images(working.get("itemImgList"))
    payload["itemImgList"] = _ensure_promo_image(images)
    payload["itemAttrList"] = _map_item_attrs(working.get("itemAttrList"))
    payload["itemSkuList"] = _map_item_skus(working.get("itemSkuList"))
    spec_list = _map_item_spec_self_defs(working.get("itemSpecSelfDefList"))
    if spec_list:
        payload["itemSpecSelfDefList"] = spec_list

    wholesale = working.get("itemWholesaleRangeList")
    if isinstance(wholesale, list):
        payload["itemWholesaleRangeList"] = wholesale

    for key in (
        "itemAttrGroupList",
        "itemShiptoSettingList",
        "itemCustomTypeInfo",
        "itemInventory",
    ):
        value = working.get(key)
        if not _is_empty_value(value):
            payload[key] = value

    site = working.get("siteId") or payload.get("siteId")
    if site:
        payload["siteId"] = _normalize_site_id(str(site))

    _validate_add_payload(payload)
    return {key: value for key, value in payload.items() if not _should_omit(key, value)}


def _normalize_site_id(site_id: str | None) -> str:
    site = str(site_id or _DEFAULT_SITE_ID).strip().upper() or _DEFAULT_SITE_ID
    if site not in _ALLOWED_SITE_IDS:
        raise bad_request("site_id 仅支持 EN / RU / ES / ID")
    return site


def _copy_keys(
    source: dict[str, Any],
    keys: tuple[str, ...],
    *,
    keep_empty_keys: tuple[str, ...] = (),
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in keys:
        if key not in source:
            continue
        value = source[key]
        if value is None:
            continue
        if value == "" and key not in keep_empty_keys:
            continue
        out[key] = value
    return out


def _apply_fission_update_info(
    detail: dict[str, Any],
    item_base: dict[str, Any],
    update_info: dict[str, Any],
) -> None:
    item_name = update_info.get("item_name")
    if item_name is not None:
        name = str(item_name).strip()
        if not name:
            raise bad_request("update_info.item_name 不能为空")
        if len(name) > 140:
            raise bad_request("update_info.item_name 最多 140 个字符")
        item_base["itemName"] = name

    after_sale_id = _normalize_optional_id(update_info.get("afterSaleTemplateId"))
    if after_sale_id:
        detail["afterSaleTemplateId"] = after_sale_id

    shipping_id = _normalize_optional_id(update_info.get("shippingTempId"))
    if shipping_id:
        detail["shippingModelId"] = shipping_id


def _fission_error_message(exc: AppError) -> str:
    parts: list[str] = []
    if exc.message:
        parts.append(exc.message)
    data = exc.data if isinstance(exc.data, dict) else {}
    response = data.get("dhgate_response")
    status = response.get("status") if isinstance(response, dict) else None
    sub_errors = status.get("subErrors") if isinstance(status, dict) else None
    if isinstance(sub_errors, list):
        for item in sub_errors:
            if not isinstance(item, dict):
                continue
            message = item.get("message")
            if message:
                text = str(message)
                if text not in parts:
                    parts.append(text)
    return "；".join(parts) or "裂变发布失败"


def _fission_error_detail(exc: AppError) -> dict[str, Any]:
    data = exc.data if isinstance(exc.data, dict) else {}
    return {
        "code": exc.code,
        "dhgate_error_code": data.get("dhgate_error_code"),
        "dhgate_response": data.get("dhgate_response"),
        "oauth_reauth_required": data.get("oauth_reauth_required"),
    }


def _map_list(raw: Any, mapper) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    items: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        mapped = mapper(item)
        if mapped:
            items.append(mapped)
    return items


def _map_item_images(raw: Any) -> list[dict[str, Any]]:
    return _map_list(raw, lambda item: _copy_keys(item, _ITEM_IMG_KEYS))


def _ensure_promo_image(images: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """发布必须有一张 type=3 的站外推广图；种子没有时用第一张顶上。"""
    if not images:
        return images
    if any(str(item.get("type")) == "3" for item in images):
        return images
    patched = [dict(item) for item in images]
    patched[0]["type"] = 3
    return patched


def _map_item_attrs(raw: Any) -> list[dict[str, Any]]:
    def map_attr(item: dict[str, Any]) -> dict[str, Any]:
        mapped = _copy_keys(item, _ITEM_ATTR_KEYS)
        is_custom = _is_custom_attr(item)
        val_keys = (
            tuple(key for key in _ITEM_ATTR_VAL_KEYS if key != "attrValId")
            if is_custom
            else _ITEM_ATTR_VAL_KEYS
        )
        values = _map_list(
            item.get("itemAttrValList"),
            lambda val: _copy_keys(val, val_keys, keep_empty_keys=("picUrl",)),
        )
        if values:
            mapped["itemAttrValList"] = values
        return mapped

    return _map_list(raw, map_attr)


def _is_custom_attr(item: dict[str, Any]) -> bool:
    attr_id = item.get("attrId")
    if attr_id is None:
        return False
    return str(attr_id).strip() == _CUSTOM_ATTR_ID


def _map_item_skus(raw: Any) -> list[dict[str, Any]]:
    def map_sku(item: dict[str, Any]) -> dict[str, Any]:
        mapped = _copy_keys(item, _ITEM_SKU_KEYS)
        attr_raw = item.get("itemSkuAttrvalList")
        if not isinstance(attr_raw, list):
            attr_raw = item.get("itemSkuAttrValueList")
        attr_vals = _map_list(
            attr_raw,
            lambda val: _copy_keys(val, _ITEM_SKU_ATTRVAL_KEYS),
        )
        if attr_vals:
            mapped["itemSkuAttrvalList"] = attr_vals

        inven_raw = item.get("itemSkuInvenList")
        if not isinstance(inven_raw, list):
            inven_raw = item.get("itemSkuInventoryList")
        if isinstance(inven_raw, list) and inven_raw:
            mapped["itemSkuInvenList"] = inven_raw
        return mapped

    return _map_list(raw, map_sku)


def _map_item_spec_self_defs(raw: Any) -> list[dict[str, Any]]:
    """自定义规格：按发布接口字段拷贝，不传 specAttrName。"""
    return _map_list(
        raw,
        lambda item: _copy_keys(item, _ITEM_SPEC_SELF_DEF_KEYS, keep_empty_keys=("picUrl",)),
    )


def _is_empty_value(value: Any) -> bool:
    if value in (None, "", [], {}):
        return True
    if isinstance(value, dict) and all(item is None for item in value.values()):
        return True
    return False


def _should_omit(key: str, value: Any) -> bool:
    if key not in _OPTIONAL_IF_EMPTY_KEYS:
        return False
    return _is_empty_value(value)


def _validate_add_payload(payload: dict[str, Any]) -> None:
    missing = [key for key in _REQUIRED_ADD_KEYS if not payload.get(key)]
    if missing:
        raise bad_request(f"种子商品缺少发布必填字段: {', '.join(missing)}")

    item_base = payload.get("itemBase") or {}
    if not item_base.get("itemName"):
        raise bad_request("商品标题 itemName 不能为空（可在 update_info.item_name 中指定）")
    if not item_base.get("htmlContent"):
        raise bad_request("种子商品缺少详情 htmlContent，无法裂变发布")
    if not any(
        item_base.get(key) for key in ("shortDesc1", "shortDesc2", "shortDesc3", "shortDesc4", "shortDesc5")
    ):
        raise bad_request("种子商品缺少卖点 shortDesc1-5，无法裂变发布")
    for key in ("keyWord1", "keyWord2", "keyWord3"):
        if not item_base.get(key):
            raise bad_request(f"种子商品缺少搜索关键字 {key}，无法裂变发布")

    package = payload.get("itemPackage") or {}
    for key in ("height", "length", "width", "grossWeight", "measureId", "packingQuantity"):
        if package.get(key) in (None, ""):
            raise bad_request(f"种子商品包装信息缺少 {key}，无法裂变发布")
