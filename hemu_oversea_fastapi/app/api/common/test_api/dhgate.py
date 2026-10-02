"""敦煌官方 API 联调（单店铺，仅调试）。

路径：/api/v1/common/testAPI/dhgate
多店编排见：/api/v1/common/testAPI/dhgate/commerce

所有接口统一通过 success_with_dhgate_raw 返回：
- result: 业务结果
- raw: 最近一次敦煌原始响应
- raw_calls: 本次请求内全部调用明细
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
# from app.core.deps import get_current_account
from app.core.errors import AppError, bad_request, not_found
from app.models.product_dh import ProductDh
from app.schemas.common import ApiResponse, success
from app.schemas.test_api.dhgate import (
    CategoryGetTestRequest,
    CategoryListTestRequest,
    CategoryPathGetTestRequest,
    CommissionRateListTestRequest,
    ItemAftersaleListTestRequest,
    ItemFissionAddTestRequest,
    ItemGetTestRequest,
    ItemGroupListTestRequest,
    ItemShelfTestRequest,
    MeasuresListTestRequest,
    PunishBrandListTestRequest,
    PunishListTestRequest,
    ShippingTemplateListTestRequest,
)
from app.services.commission_rates_dh import sync_commission_rates_dh
from app.services.dhgate import (
    DhgateClient,
    downshelf_items,
    fission_add_item,
    get_category,
    get_category_path,
    get_dhgate_client,
    get_item,
    get_item_html,
    list_item_aftersale,
    list_item_groups,
    list_punish,
    list_punish_brand,
    list_shipping_templates,
    tweak_and_upload_main_image,
    upshelf_items,
)
from app.services.measures_units_dh import sync_measures_units_dh
from app.services.product_categories_dh import sync_product_categories_dh

router = APIRouter(
    prefix="/dhgate",
    tags=["common:testAPI:dhgate"],
    # dependencies=[Depends(get_current_account)],
)


def _test_client(db: Session, store_id: int) -> DhgateClient:
    client = get_dhgate_client(db, store_id)
    client.clear_call_history()
    return client


def success_with_dhgate_raw(
    client: DhgateClient,
    result: Any,
) -> ApiResponse[dict[str, Any]]:
    """联调统一出口：业务结果 + 原始调用记录。"""
    return success(
        {
            "result": result,
            "raw": client.last_raw,
            "raw_calls": client.call_history,
        }
    )


@router.post(
    "/punish-brand/list",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] dh.punish.brand.list.get",
)
def test_list_punish_brand(
    payload: PunishBrandListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    client = _test_client(db, payload.store_id)
    data = list_punish_brand(
        client,
        third_type=payload.third_type,
        page_no=payload.page_no,
        page_size=payload.page_size,
    )
    return success_with_dhgate_raw(client, data)


@router.post(
    "/punish/list",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] dh.punish.list.get",
)
def test_list_punish(
    payload: PunishListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    client = _test_client(db, payload.store_id)
    data = list_punish(
        client,
        start_date=payload.start_date,
        end_date=payload.end_date,
        page_no=payload.page_no,
        page_size=payload.page_size,
        punish_id=payload.punish_id,
    )
    return success_with_dhgate_raw(client, data)


@router.post(
    "/category/list",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] dh.category.list$2.0（边拉边入库，已存在跳过）",
)
def test_list_categories(
    payload: CategoryListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    递归拉取敦煌发布类目并写入 product_category_dh。

    - 每入库一条立即 commit
    - 库中已有的 cate_pub_id 直接跳过（不再下钻）
    - 中断后可重跑续传；list 仅返回本次新入库的类目
    """
    client = _test_client(db, payload.store_id)
    categories, sync_stats = sync_product_categories_dh(
        db,
        store_id=payload.store_id,
        client=client,
    )
    return success_with_dhgate_raw(
        client,
        {
            "list": categories,
            "count": len(categories),
            "synced": sync_stats,
        },
    )


@router.post(
    "/measures/list",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] dh.base.measures.get$1.0（清空后全量入库 measures_unit_dh）",
)
def test_sync_measures_units(
    payload: MeasuresListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    拉取敦煌计件单位列表并覆盖本地 measures_unit_dh。

    - 每次调用先清空再写入，保证与平台最新数据一致
    - 官方响应字段名为 meauserList（拼写以文档为准）
    """
    client = _test_client(db, payload.store_id)
    synced = sync_measures_units_dh(
        db,
        store_id=payload.store_id,
        client=client,
    )
    return success_with_dhgate_raw(client, synced)


@router.post(
    "/categorys/commissions",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] dh.categorys.commissions$1.0（清空后全量入库 commissions_rate_dh）",
)
def test_sync_commission_rates(
    payload: CommissionRateListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    拉取全部类目佣金率并覆盖本地 commissions_rate_dh。

    - 佣金率按二级类目绑定，不按店铺隔离
    - store_id 仅用于取 access_token
    - 每次调用先清空再写入
    """
    client = _test_client(db, payload.store_id)
    synced = sync_commission_rates_dh(
        db,
        store_id=payload.store_id,
        client=client,
    )
    return success_with_dhgate_raw(client, synced)


@router.post(
    "/category/get",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] dh.category.get$2.0（类目详情/属性）",
)
def test_get_category(
    payload: CategoryGetTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按叶子发布类目 ID 获取类目详情：属性、属性值、关键词限制等。

    cate_pub_id 须为有效叶子类目（来自 category/list 或 product_category_dh）。
    """
    client = _test_client(db, payload.store_id)
    data = get_category(client, cate_pub_id=payload.cate_pub_id)
    return success_with_dhgate_raw(client, data)


@router.post(
    "/category/path/get",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] dh.category.path.get$2.0（获取类目路径）",
)
def test_get_category_path(
    payload: CategoryPathGetTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按叶子发布类目 ID 获取从根到当前类目的主线路径。

    返回 categoryPublishList（由上至下，含当前叶子类目）。
    """
    client = _test_client(db, payload.store_id)
    data = get_category_path(client, cate_pub_id=payload.cate_pub_id)
    return success_with_dhgate_raw(client, data)


@router.post(
    "/item/get",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] dh.item.get$2.0（产品详情）",
)
def test_get_item(
    payload: ItemGetTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按商品编码获取卖家产品详情（SKU、属性、图片、包装、销售设置等）。

    item_code 来自 dh.item.list；site_id 默认 EN。
    """
    client = _test_client(db, payload.store_id)
    data = get_item(
        client,
        item_code=payload.item_code,
        site_id=payload.site_id,
    )
    return success_with_dhgate_raw(client, data)


@router.post(
    "/item/shelf",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] 商品上架/下架（dh.item.upshelf.list / downshelf.list）",
)
def test_item_shelf(
    payload: ItemShelfTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按 action 调用敦煌批量上架或下架。

    - action=0：dh.item.downshelf.list$2.0 下架
    - action=1：dh.item.upshelf.list$2.0 上架
    - item_codes：多个产品编码用英文半角逗号分隔，最多 200 个
    """
    client = _test_client(db, payload.store_id)
    if payload.action == 0:
        data = downshelf_items(
            client,
            item_codes=payload.item_codes,
            site_id=payload.site_id,
        )
        action_name = "downshelf"
    else:
        data = upshelf_items(
            client,
            item_codes=payload.item_codes,
            site_id=payload.site_id,
        )
        action_name = "upshelf"
    return success_with_dhgate_raw(
        client,
        {
            "action": payload.action,
            "action_name": action_name,
            "item_codes": payload.item_codes,
            "site_id": payload.site_id,
            "dhgate": data,
        },
    )


@router.post(
    "/item/group/list",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] dh.item.group.list$2.0（获取产品组列表）",
)
def test_list_item_groups(
    payload: ItemGroupListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    获取当前店铺产品组列表（itemGroupList）。

    官方必填 pageNo、pageSize；其余筛选可选。
    列表项 groupId 对应发布入参 itemGroupId。
    """
    client = _test_client(db, payload.store_id)
    data = list_item_groups(
        client,
        page_no=payload.page_no,
        page_size=payload.page_size,
        contain_child_group=payload.contain_child_group,
        parent_group_id=payload.parent_group_id,
        group_cn_name=payload.group_cn_name,
        group_en_name=payload.group_en_name,
    )
    return success_with_dhgate_raw(client, data)


@router.post(
    "/item/html/get",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] dh.product.html.get$1.0（产品长描）",
)
def test_get_item_html(
    payload: ItemGetTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按商品编码获取产品长描 htmlContent。

    参数与 /item/get 一致：store_id、item_code、site_id。
    官方入参仅 itemcode；site_id 仅作对齐，不传给平台。
    """
    client = _test_client(db, payload.store_id)
    data = get_item_html(
        client,
        item_code=payload.item_code,
        site_id=payload.site_id,
    )
    return success_with_dhgate_raw(client, data)


@router.post(
    "/item/img/tweak",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] 微调产品主图并上传（dh.album.img.upload$2.1）",
)
async def test_tweak_main_image(
    db: Session = Depends(get_db),
    store_id: int = Form(..., description="店铺 ID，用于取该店 access_token"),
    item_code: str | None = Form(
        default=None,
        description="产品编码；有值则取详情第一张主图并忽略 imgBase64",
    ),
    imgBase64: UploadFile | None = File(
        default=None,
        description="参考主图文件（接口内转 base64）；item_code 有值时忽略",
    ),
) -> ApiResponse[dict[str, Any]]:
    """
    获取参考主图 → Pillow 微调防重复 → 调用 dh.album.img.upload。

    - store_id：目标店铺 token
    - item_code：有值时调用 dh.item.get，取 itemImgList 第一张，
      拼接 http://image.dhgate.com/ 下载后作为原主图
    - imgBase64：文件上传；仅在未传 item_code 时使用
    """
    started = time.perf_counter()
    code = str(item_code or "").strip() or None
    image_bytes: bytes | None = None
    image_filename: str | None = None
    if not code:
        if imgBase64 is None:
            raise bad_request("请上传 imgBase64 文件，或传入 item_code")
        image_bytes = await imgBase64.read()
        if not image_bytes:
            raise bad_request("上传文件为空")
        image_filename = imgBase64.filename

    client = _test_client(db, store_id)
    data = tweak_and_upload_main_image(
        client,
        item_code=code,
        image_bytes=image_bytes,
        image_filename=image_filename,
    )
    uploaded = data.get("upload") if isinstance(data.get("upload"), dict) else {}
    duration_ms = int((time.perf_counter() - started) * 1000)
    return success_with_dhgate_raw(
        client,
        {
            **uploaded,
            "original_image_url": data.get("original_image_url"),
            "new_image_url": data.get("new_image_url"),
            "duration_ms": duration_ms,
        },
    )


@router.post(
    "/item/aftersale/list",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] dh.item.aftersale.list$2.0（获取售后模板列表）",
)
def test_list_item_aftersale(
    payload: ItemAftersaleListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    获取当前店铺售后模板列表（afterSaleList）。

    官方无业务入参，仅需 store_id 取该店 token。
    返回 afterSaleTemplateId、name、是否默认模板等，供发布时填写 afterSaleTemplateId。
    """
    client = _test_client(db, payload.store_id)
    data = list_item_aftersale(client)
    return success_with_dhgate_raw(client, data)


@router.post(
    "/shipping/template/list",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] dh.shipping.template.list$2.0（获取运费模板列表）",
)
def test_list_shipping_templates(
    payload: ShippingTemplateListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    获取当前店铺运费模板列表（shippingModelList）。

    官方无业务入参，仅需 store_id 取该店 token。
    shippingTempId 对应发布入参 shippingModelId；modelType=10 为新手/默认运费模板。
    """
    client = _test_client(db, payload.store_id)
    data = list_shipping_templates(client)
    return success_with_dhgate_raw(client, data)


def _fission_raw_bundle(
    source_client: DhgateClient,
    target_client: DhgateClient | None,
) -> dict[str, Any]:
    raw_calls = list(source_client.call_history)
    last_raw = source_client.last_raw
    if target_client is not None:
        raw_calls.extend(target_client.call_history)
        if target_client.last_raw is not None:
            last_raw = target_client.last_raw
    return {"raw": last_raw, "raw_calls": raw_calls}


@router.post(
    "/item/fission/add",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] 裂变发布商品（源店 dh.item.get + 目标店 dh.item.add$2.0）",
)
def test_fission_add_item(
    payload: ItemFissionAddTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按本地种子商品 pid 查出源店与 item_code，拉最新详情后裂变发布到目标店。

    - target_store_id：目标店铺，发布用该店 token
    - pid：product_dh.id，用于取源店 store_id / item_code / site_id
    - update_info：覆盖种子详情后再组装 dh.item.add 入参（含标题、售后模板、运费模板）
    - 额外调用 dh.product.html.get 取长描，写入发布体 itemBase.htmlContent，接口响应不回传长描
    - 发布前用目标店 token 微调上传第一张主图，替换 itemImgList[0] 的 imgUrl/imgMd5
    - update_info.afterSaleTemplateId / shippingTempId 有值则直接使用，不再拉对应模板列表
    - 未传模板 ID 时：同店沿用原值，跨店取目标店默认售后模板及新手运费模板（modelType=10）
    - 返回 original_detail、aftersale_list、shipping_template_list、tweaked_main_image、add_payload、duration_ms
    """
    started = time.perf_counter()
    row = db.get(ProductDh, payload.pid)
    if row is None:
        raise not_found("商品不存在")

    site_id = payload.site_id or row.site_id or "EN"
    update_info = payload.update_info.model_dump(exclude_none=True)
    source_meta = {
        "pid": row.id,
        "store_id": row.store_id,
        "item_code": row.item_code,
        "site_id": row.site_id,
    }
    try:
        source_client = _test_client(db, row.store_id)
    except AppError as exc:
        raise bad_request(
            exc.message,
            data={
                "source": source_meta,
                "target_store_id": payload.target_store_id,
                "update_info": update_info,
                "original_detail": None,
                "aftersale_list": None,
                "shipping_template_list": None,
                "tweaked_main_image": None,
                "add_payload": None,
                "added": None,
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "error": exc.message,
                "error_detail": exc.data,
            },
        ) from exc

    target_holder: dict[str, DhgateClient | None] = {"client": None}

    def _target_client() -> DhgateClient:
        client = get_dhgate_client(db, payload.target_store_id)
        client.clear_call_history()
        target_holder["client"] = client
        return client

    result = fission_add_item(
        source_client,
        item_code=row.item_code,
        target_client_factory=_target_client,
        update_info=update_info,
        site_id=site_id,
    )
    body: dict[str, Any] = {
        "source": source_meta,
        "target_store_id": payload.target_store_id,
        "update_info": update_info,
        "original_detail": result.get("original_detail"),
        "aftersale_list": result.get("aftersale_list"),
        "shipping_template_list": result.get("shipping_template_list"),
        "tweaked_main_image": result.get("tweaked_main_image"),
        "add_payload": result.get("add_payload"),
        "added": result.get("added"),
        "duration_ms": int((time.perf_counter() - started) * 1000),
        **_fission_raw_bundle(source_client, target_holder["client"]),
    }
    error = result.get("error")
    if error:
        raise bad_request(
            str(error),
            data={
                **body,
                "error": error,
                "error_detail": result.get("error_detail"),
            },
        ) from None
    return success(body)
