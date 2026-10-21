"""敦煌多店铺编排联调（仅调试）。

路径：/api/v1/common/testAPI/dhgate/commerce
OpenAPI 标签：common:testAPI:dhgate:commerce
用于验证敦煌店铺多店汇总 / 同步逻辑，非正式业务接口。
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
# from app.core.deps import get_current_account
from app.core.errors import bad_request
from app.schemas.common import ApiResponse, success
from app.schemas.test_api.commerce import (
    AftersaleTemplateSyncTestRequest,
    DisputeOpenSummaryTestRequest,
    DisputeProcessingSummaryTestRequest,
    ProductGroupSyncTestRequest,
    ProductSyncTestRequest,
    PunishSummaryTestRequest,
    ShippingTemplateSyncTestRequest,
)
from app.services import utils_file as utils_file_service
from app.services.aftersale_templates_dh import sync_supplier_aftersale_templates_dh
from app.services.commerce import (
    summarize_supplier_dispute_open,
    summarize_supplier_dispute_processing,
    summarize_supplier_punish,
)
from app.services.product_groups_dh import sync_supplier_product_groups_dh
from app.services.products_dh import (
    find_missing_product_sync_items,
    summarize_file_sync_result,
    sync_products_dh,
    sync_products_from_file,
)
from app.services.shipping_templates_dh import sync_supplier_shipping_templates_dh

router = APIRouter(
    prefix="/dhgate/commerce",
    tags=["common:testAPI:dhgate:commerce"],
    # dependencies=[Depends(get_current_account)],
)


def _success_with_multi_store_raw(summary: Any) -> ApiResponse[dict[str, Any]]:
    """多店联调统一出口：业务汇总 + 全部敦煌原始调用。"""
    payload = asdict(summary)
    raw_calls = payload.pop("raw_calls", []) or []
    last = raw_calls[-1] if raw_calls else None
    raw = last.get("response") if isinstance(last, dict) else None
    return success(
        {
            "result": payload,
            "raw": raw,
            "raw_calls": raw_calls,
        }
    )


@router.post(
    "/punish/summary",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] 敦煌多店铺处罚信息汇总",
)
def test_punish_summary(
    payload: PunishSummaryTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按供应商汇总已授权敦煌店铺的处罚信息（单店 / 多店；不含纠纷订单）。

    ## 店铺范围
    - `supplier_id` 必传
    - 传 `store_id`：仅查该店（须属于该供应商且已授权）
    - 不传 `store_id`：查该供应商下全部已授权敦煌店铺

    ## 每店拉取的数据（page_no / page_size 三类共用，默认 1 / 100）
    1. `punish` ← `dh.punish.list.get`（起止日期由 query_days 推算）
    2. `punish_brand` ← `dh.punish.brand.list.get` thirdType=brand
    3. `punish_other` ← `dh.punish.brand.list.get` thirdType=other

    ## 返回结构（与单店联调一致）
    - `result`：业务汇总
      - `stores[]`：各店 `punish` / `punish_brand` / `punish_other` 及 `call_errors`
      - `stores_summary.punish_list`：三类处罚合并（附 store_id）
      - `errors`：整店级失败
    - `raw`：最近一次敦煌原始响应（含 status）
    - `raw_calls`：本次全部调用明细（含 store_id / store_identifier）

    纠纷订单请使用同模块：
    - 【v1】`/dispute/processing/summary`
    - 【v2】`/order/disputeopen/summary`
    """
    summary = summarize_supplier_punish(
        db,
        supplier_id=payload.supplier_id,
        store_id=payload.store_id,
        query_days=payload.query_days,
        page_no=payload.page_no,
        page_size=payload.page_size,
    )
    return _success_with_multi_store_raw(summary)


@router.post(
    "/dispute/processing/summary",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调][v1] 敦煌多店铺进行中纠纷订单汇总",
)
def test_dispute_processing_summary(
    payload: DisputeProcessingSummaryTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    【v1】按供应商汇总已授权敦煌店铺「进行中」的纠纷订单（单店 / 多店）。

    ## 店铺范围
    - `supplier_id` 必传
    - 传 `store_id`：仅查该店（须属于该供应商且已授权）
    - 不传 `store_id`：查该供应商下全部已授权敦煌店铺

    ## 每店拉取的数据
    - `dispute_processing` ← `dh.dispute.processing.list$1.0`
    - 官方必填 `disputeStatus`；可选 `startTime` / `endTime` / `pageNum` / `pageSize`
    - 分页默认 `page_num=1`、`page_size=100`
    - `disputeStatus` 联调可参考：`106001`/`106003`/`107001`/`107002`/`107003`/`109001`/`109002`
      （含义见单店 `/order/disputeopen/list` 注释）

    ## 返回结构（与单店联调一致）
    - `result`：业务汇总（stores / stores_summary / errors）
    - `raw` / `raw_calls`：敦煌原始响应与调用明细

    单店【v1】：`/testAPI/dhgate/dispute/processing/list`。
    【v2】：`/order/disputeopen/summary`。
    """
    summary = summarize_supplier_dispute_processing(
        db,
        supplier_id=payload.supplier_id,
        store_id=payload.store_id,
        dispute_status=payload.dispute_status,
        page_num=payload.page_num,
        page_size=payload.page_size,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    return _success_with_multi_store_raw(summary)


@router.post(
    "/order/disputeopen/summary",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调][v2] 敦煌多店铺纠纷开启订单汇总",
)
def test_dispute_open_summary(
    payload: DisputeOpenSummaryTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    【v2】按供应商汇总已授权敦煌店铺当前「开启中」的纠纷订单（单店 / 多店）。

    ## 店铺范围
    - `supplier_id` 必传
    - 传 `store_id`：仅查该店（须属于该供应商且已授权）
    - 不传 `store_id`：查该供应商下全部已授权敦煌店铺

    ## 每店拉取的数据（page_no / page_size 默认 1 / 100）
    - `dispute_open` ← `dh.order.disputeopen.list$2.0`
    - 官方必填：`pageNo`、`pageSize`；可选 `disputeType`/`buyerNickName`/`orderNo`
      （本汇总当前只传分页；筛选请用单店联调）
    - 官方无时间范围入参；`disputeType` 可选值：`1` 协议 / `2` 平台 / `3` 售后

    ## 返回结构（与单店联调一致）
    - `result`：业务汇总
      - `stores[]`：各店 `dispute_open` 与 `call_errors`
      - `stores_summary.dispute_open_list`：合并 `orderDisputeOpenInfos`（附 store_id）
      - `errors`：整店级失败
    - `raw`：最近一次敦煌原始响应（含 status；可对照 payDate 等官方原文字段）
    - `raw_calls`：本次全部调用明细（含 store_id / store_identifier）

    单店【v2】联调见 `/testAPI/dhgate/order/disputeopen/list`；
    取到 `orderNo` 后可用 `dh.dispute.detail.get$1.0` 查详情。

    【v1】同场景见上方接口：`/dispute/processing/summary`
    （`dh.dispute.processing.list$1.0`）。
    """
    summary = summarize_supplier_dispute_open(
        db,
        supplier_id=payload.supplier_id,
        store_id=payload.store_id,
        page_no=payload.page_no,
        page_size=payload.page_size,
    )
    return _success_with_multi_store_raw(summary)


@router.post(
    "/item/group/sync",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] dh.item.group.list$2.0 多店铺产品分组同步入库",
)
def test_sync_product_groups(
    payload: ProductGroupSyncTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按供应商查询所属已授权敦煌店铺，逐店调用 `dh.item.group.list$2.0` 并写入 product_group_dh。

    ## 官方（每店）
    - method：`dh.item.group.list`，version=`2.0`
    - 本编排固定：`containChildGroup=true`，分页拉全量；结果扁平化写入

    ## 入库行为（本地）
    - 每入库一条立即 commit；同店已存在的 `group_id` 跳过
    - 子分组扁平化，`parent_group_id` 记录层级；每条带 `supplier_id`、`store_id`
    - 单店失败不中断其余店铺

    单店联调：`/testAPI/dhgate/item/group/list`。
    """
    result = sync_supplier_product_groups_dh(
        db,
        supplier_id=payload.supplier_id,
    )
    return success(result)


@router.post(
    "/shipping/template/sync",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] dh.shipping.template.list$2.0 多店铺运费模板同步入库",
)
def test_sync_shipping_templates(
    payload: ShippingTemplateSyncTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按供应商查询所属已授权敦煌店铺，逐店调用 `dh.shipping.template.list$2.0` 并写入 shipping_template_dh。

    ## 官方（每店）
    - method：`dh.shipping.template.list`，version=`2.0`，**无业务入参**
    - 返回 `shippingModelList`；模板 ID → 发布入参 `shippingModelId`

    ## 入库行为（本地）
    - 每入库一条立即 commit；同店已存在的 `shipping_temp_id` 跳过
    - 每条带 `supplier_id`、`store_id`；单店失败不中断其余店铺

    单店联调：`/testAPI/dhgate/shipping/template/list`。
    """
    result = sync_supplier_shipping_templates_dh(
        db,
        supplier_id=payload.supplier_id,
    )
    return success(result)


@router.post(
    "/item/aftersale/sync",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] dh.item.aftersale.list$2.0 多店铺售后模板同步入库",
)
def test_sync_aftersale_templates(
    payload: AftersaleTemplateSyncTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按供应商查询所属已授权敦煌店铺，逐店调用 `dh.item.aftersale.list$2.0` 并写入 aftersale_template_dh。

    ## 官方（每店）
    - method：`dh.item.aftersale.list`，version=`2.0`，**无业务入参**
    - 返回售后模板列表；模板 ID → 发布入参 `afterSaleTemplateId`（3C 类目常需）

    ## 入库行为（本地）
    - 每入库一条立即 commit；同店已存在的 `after_sale_template_id` 跳过
    - 每条带 `supplier_id`、`store_id`；单店失败不中断其余店铺

    单店联调：`/testAPI/dhgate/item/aftersale/list`。
    """
    result = sync_supplier_aftersale_templates_dh(
        db,
        supplier_id=payload.supplier_id,
    )
    return success(result)


@router.post(
    "/product/sync",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] 敦煌多店铺商品详情同步入库",
)
def test_product_sync(
    payload: ProductSyncTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按 store_identifier + item_code 批量拉取 dh.item.get 并写入 product_dh 及相关子表。

    - store_identifier 对应 stores.identifier，内部解析店铺与 access_token
    - 可跨店铺一次传入多个商品
    - site_id 默认 EN
    - 同步成功的商品 is_seed=1
    - 单条失败不中断整批
    """
    result = sync_products_dh(
        db,
        items=[item.model_dump() for item in payload.items],
    )
    return success(result)


@router.post(
    "/product/syncfromfile",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] 从 Excel 提取后多店铺商品详情同步入库",
)
async def test_product_sync_from_file(
    db: Session = Depends(get_db),
    file: UploadFile = File(..., description="Excel 文件（.xlsx / .xlsm）"),
    extract_field_info: str = Form(
        default='{"store_identifier":"A","item_code":"B"}',
        description=(
            "提取字段映射（JSON）。须含 store_identifier / item_code。"
            '默认：{"store_identifier":"A","item_code":"B"}'
        ),
        examples=['{"store_identifier":"A","item_code":"B"}'],
    ),
    start_row: int = Form(
        default=2,
        ge=1,
        description="开始提取的行号（1 起）。默认 2=跳过表头；无表头时设为 1",
    ),
    row_count: int = Form(
        default=0,
        ge=0,
        description="计划提取行数。默认 0=全部；超出实际数据不报错",
    ),
    sheet_index: int = Form(
        default=1,
        ge=0,
        description="工作表索引：0=读取全部 sheet；1 起为指定 sheet（1=第一个）",
    ),
    is_autocheck: int = Form(
        default=0,
        ge=0,
        le=1,
        description="是否自动检查遗漏：0=否（处理全部提取行），1=是（仅处理库中不存在的商品）",
    ),
) -> ApiResponse[dict[str, Any]]:
    """
    从 Excel 提取店铺标识与商品编码后同步入库：

    1. 按 extract_field_info 提取行（须含 store_identifier / item_code）
    2. 行内缺少店铺或商品编码：仅在响应 failed 中体现，不写库
    3. 调 dh.item.get 成功：写入完整详情，sync_state=1
    4. 敦煌 API 报错/数据异常：仍写入店铺+商品编码，sync_state=0，便于事后排查
    5. is_autocheck=1 时仅处理库中尚不存在的商品

    响应：elapsed_ms、success_count、failed_count；
    failed 含 item_code / store_identifier / message（及可选 product_id）。
    """
    field_map = utils_file_service.parse_extract_field_info(extract_field_info)
    if "store_identifier" not in field_map or "item_code" not in field_map:
        raise bad_request(
            "extract_field_info 须包含 store_identifier 与 item_code 两列映射"
        )

    content = await file.read()
    extract = utils_file_service.extract_rows_from_file(
        file=file,
        content=content,
        extract_field_info=field_map,
        start_row=start_row,
        row_count=row_count,
        sheet_index=sheet_index,
    )
    if extract.valid_count <= 0:
        raise bad_request("Excel 中未解析到有效的店铺标识与商品编码")

    all_items = list(extract.items)
    missing_items: list[dict[str, str]] | None = None
    if is_autocheck == 1:
        missing_items = find_missing_product_sync_items(db, items=all_items)
        sync_items = missing_items
    else:
        sync_items = all_items

    if not sync_items:
        return success(
            {
                "elapsed_ms": 0,
                "success_count": 0,
                "failed_count": 0,
                "failed": [],
                **(
                    {
                        "missing_count": 0,
                        "missing_items": [],
                    }
                    if is_autocheck == 1
                    else {}
                ),
            }
        )

    sync_result = sync_products_from_file(db, items=sync_items)
    return success(
        summarize_file_sync_result(
            sync_result,
            missing_items=missing_items if is_autocheck == 1 else None,
        )
    )
