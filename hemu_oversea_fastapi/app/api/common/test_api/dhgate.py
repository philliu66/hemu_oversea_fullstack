"""敦煌官方 API 联调（单店铺，仅调试）。

路径：/api/v1/common/testAPI/dhgate
OpenAPI 标签：common:testAPI:dhgate。/docs 中单店接口在前，多店编排整体在最后。

所有接口统一通过 success_with_dhgate_raw 返回：
- result: 业务结果
- raw: 最近一次敦煌原始响应
- raw_calls: 本次请求内全部调用明细

敦煌调用失败时，错误响应 data 里同样带上 raw 与 raw_calls。
"""

from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from contextvars import ContextVar
from functools import wraps
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
    DisputeProcessingListTestRequest,
    MeasuresListTestRequest,
    OrderDisputeOpenListTestRequest,
    PunishBrandListTestRequest,
    PunishListTestRequest,
    SellerAdReportTestRequest,
    ShippingTemplateListTestRequest,
    WisCoreInfoTestRequest,
    WisDetailPageTestRequest,
    WisKeywordTop10TestRequest,
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
    get_wis_core_info,
    get_wis_detail_page,
    get_wis_keywordtop10_info,
    list_dispute_processing,
    list_item_aftersale,
    list_item_groups,
    list_order_dispute_open,
    list_punish,
    list_punish_brand,
    list_seller_ad_order_report,
    list_seller_ad_prod_report,
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


_tracked_clients: ContextVar[list[DhgateClient] | None] = ContextVar(
    "dhgate_single_test_clients",
    default=None,
)


def _remember_client(client: DhgateClient) -> DhgateClient:
    bucket = _tracked_clients.get()
    if bucket is not None:
        bucket.append(client)
    return client


def _test_client(db: Session, store_id: int) -> DhgateClient:
    client = get_dhgate_client(db, store_id)
    client.clear_call_history()
    return _remember_client(client)


def _raw_bundle(clients: list[DhgateClient]) -> dict[str, Any]:
    raw_calls: list[dict[str, Any]] = []
    last_raw: dict[str, Any] | None = None
    for client in clients:
        raw_calls.extend(client.call_history)
        if client.last_raw is not None:
            last_raw = client.last_raw
    return {"raw": last_raw, "raw_calls": raw_calls}


def _error_with_raw_calls(exc: AppError, clients: list[DhgateClient]) -> AppError:
    """失败响应补上本次已发生的敦煌原始调用；调用方已自行放入时不覆盖。"""
    if not clients:
        return exc
    data = dict(exc.data) if isinstance(exc.data, dict) else {}
    if "raw_calls" in data:
        return exc
    data.update(_raw_bundle(clients))
    return AppError(exc.status_code, exc.code, exc.message, data)


def _expose_raw_on_error(fn: Callable[..., Any]) -> Callable[..., Any]:
    """单店联调：敦煌报错时把 raw / raw_calls 放进错误 data。"""

    if inspect.iscoroutinefunction(fn):
        @wraps(fn)
        async def async_wrapped(*args: Any, **kwargs: Any) -> Any:
            bucket: list[DhgateClient] = []
            token = _tracked_clients.set(bucket)
            try:
                return await fn(*args, **kwargs)
            except AppError as exc:
                raise _error_with_raw_calls(exc, bucket) from exc
            finally:
                _tracked_clients.reset(token)

        return async_wrapped

    @wraps(fn)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        bucket: list[DhgateClient] = []
        token = _tracked_clients.set(bucket)
        try:
            return fn(*args, **kwargs)
        except AppError as exc:
            raise _error_with_raw_calls(exc, bucket) from exc
        finally:
            _tracked_clients.reset(token)

    return wrapped


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
    summary="[联调][单店][处罚] 第三方投诉处罚列表（dh.punish.brand.list.get$1.0）",
)
@_expose_raw_on_error
def test_list_punish_brand(
    payload: PunishBrandListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按第三方投诉类型查询卖家处罚信息。

    ## 官方
    - method：`dh.punish.brand.list.get`，version=`1.0`，级别 A，超时约 15 秒

    ## 业务入参（对应请求体字段）
    | 官方字段 | 本接口字段 | 必填 | 可选值 / 说明 |
    | --- | --- | --- | --- |
    | thirdType | third_type | 是 | `brand` 品牌商投诉；`other` 其他第三方投诉 |
    | pageNo | page_no | 是 | 页码，从 1 开始 |
    | pageSize | page_size | 是 | 1～200 |

    ## 返回（result）
    - `punishInfoList`、`pages`、`count`
    """
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
    summary="[联调][单店][处罚] 卖家处罚记录（dh.punish.list.get$1.0）",
)
@_expose_raw_on_error
def test_list_punish(
    payload: PunishListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按时间范围查询卖家处罚记录。

    ## 官方
    - method：`dh.punish.list.get`，version=`1.0`，级别 A，超时约 15 秒

    ## 业务入参
    | 官方字段 | 本接口字段 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | startDate | start_date | 是 | yyyy-MM-dd |
    | endDate | end_date | 是 | yyyy-MM-dd |
    | pageNo | page_no | 是 | 从 1 开始 |
    | pageSize | page_size | 是 | 1～200 |
    | punishId | punish_id | 否 | 处罚编号 |

    ## 返回（result）
    - `punishInfoList`、`pages`、`count`
    """
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
    "/dispute/processing/list",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调][单店][纠纷][v1] 进行中纠纷订单列表（dh.dispute.processing.list$1.0）",
)
@_expose_raw_on_error
def test_list_dispute_processing(
    payload: DisputeProcessingListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    【v1】查询当前卖家「进行中」的纠纷订单列表。

    ## 官方
    - method：`dh.dispute.processing.list`，version=`1.0`，超时约 30 秒

    ## 业务入参
    | 官方字段 | 本接口字段 | 必填 | 可选值 / 说明 |
    | --- | --- | --- | --- |
    | disputeStatus | dispute_status | 是 | 手册未单独列本接口枚举；联调可参考：`106001`/`106003`/`107001`/`107002`/`107003`/`109001`/`109002`（含义见下方 v2 接口注释） |
    | pageNum | page_num | 否 | 从 1 开始 |
    | pageSize | page_size | 否 | 1～200 |
    | startTime | start_time | 否 | 开始时间 |
    | endTime | end_time | 否 | 结束时间 |

    ## 返回（result）
    - `disputeList`、`total`、`pageNum`、`pageSize`

    【v2】同场景：`/order/disputeopen/list`（`dh.order.disputeopen.list$2.0`）。
    """
    client = _test_client(db, payload.store_id)
    data = list_dispute_processing(
        client,
        dispute_status=payload.dispute_status,
        page_num=payload.page_num,
        page_size=payload.page_size,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    return success_with_dhgate_raw(client, data)


@router.post(
    "/order/disputeopen/list",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调][单店][纠纷][v2] 纠纷开启订单列表（dh.order.disputeopen.list$2.0）",
)
@_expose_raw_on_error
def test_list_order_dispute_open(
    payload: OrderDisputeOpenListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    【v2】查询当前卖家「开启中」的纠纷订单列表。

    ## 官方
    - method：`dh.order.disputeopen.list`，version=`2.0`，仅支持 POST，超时约 20 秒
    - **无时间范围入参**，返回当前仍处于开启状态的纠纷

    ## 业务入参
    | 官方字段 | 本接口字段 | 必填 | 可选值 / 说明 |
    | --- | --- | --- | --- |
    | pageNo | page_no | 是 | 从 1 开始；超过总页数返回最后一页 |
    | pageSize | page_size | 是 | 1～200 |
    | disputeType | dispute_type | 否 | `1` 协议纠纷；`2` 平台纠纷；`3` 售后纠纷；不传=全部 |
    | buyerNickName | buyer_nick_name | 否 | 买家昵称 |
    | orderNo | order_no | 否 | 订单号 |

    ## 响应 disputeStatus 枚举（orderDisputeOpenInfos）
    | 编码 | 含义 |
    | --- | --- |
    | 106001 | 协议纠纷-等待协议达成 |
    | 106003 | 协议纠纷-协议已达成 |
    | 107001 | 平台纠纷开启 |
    | 107002 | 平台纠纷-dhgate审核中 |
    | 107003 | 平台纠纷-裁决方案执行中 |
    | 109001 | 售后纠纷开启 |
    | 109002 | 售后纠纷裁决中 |
    | （空） | 没有售后纠纷 |

    ## 返回（result）
    - `orderDisputeOpenInfos`、`count`、`pages`
    - 取到 `orderNo` 后可用 `dh.dispute.detail.get$1.0` 查详情
    """
    client = _test_client(db, payload.store_id)
    data = list_order_dispute_open(
        client,
        page_no=payload.page_no,
        page_size=payload.page_size,
        dispute_type=payload.dispute_type,
        buyer_nick_name=payload.buyer_nick_name,
        order_no=payload.order_no,
    )
    return success_with_dhgate_raw(client, data)


@router.post(
    "/wis/core-info",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调][单店][数据] 数据概览核心指标（dh.wis.core.info$1.0）",
)
@_expose_raw_on_error
def test_wis_core_info(
    payload: WisCoreInfoTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    下载「数据概览」页核心经营指标（数据 API 限免三件套之一）。

    ## 官方
    - method：`dh.wis.core.info`，version=`1.0`，级别 A，超时约 30 秒
    - 关联：下钻单品 → `dh.wis.detail.page`；关键词 → `dh.wis.keywordtop10.info`

    ## 业务入参（手册均标必填）
    | 官方字段 | 本接口字段 | 必填 | 可选值 / 说明 |
    | --- | --- | --- | --- |
    | periodType | period_type | 是 | `DAY` 1天；`L7` 7天；`L30` 30天；`WEEK` 周；`MON` 月 |
    | site | site | 是 | `TOTAL` / `app` / `unapp` |
    | endDate | end_date | 是 | 结束时间 yyyy-MM-dd |
    | countryId | country_id | 是 | 示例 `TOTAL`；其它见 `dh.base.countrys.get` |
    | statDate | stat_date | 是 | 开始时间 yyyy-MM-dd |

    ## 返回（result）
    - `list`：核心指标列表（WisCoreDTO[]）
    """
    client = _test_client(db, payload.store_id)
    data = get_wis_core_info(
        client,
        period_type=payload.period_type,
        site=payload.site,
        end_date=payload.end_date,
        country_id=payload.country_id,
        stat_date=payload.stat_date,
    )
    return success_with_dhgate_raw(client, data)


@router.post(
    "/wis/detail-page",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调][单店][数据] 商品分析-产品详情（dh.wis.detail.page$1.0）",
)
@_expose_raw_on_error
def test_wis_detail_page(
    payload: WisDetailPageTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    下载「商品分析-产品详情」页产品维度数据（数据 API 限免三件套之一）。

    ## 官方
    - method：`dh.wis.detail.page`，version=`1.0`，级别 A，超时约 **60** 秒
    - 关联：店铺看板 `dh.wis.core.info`；产品基础信息可对照 `dh.item.list` / `dh.item.get`

    ## 业务入参
    | 官方字段 | 本接口字段 | 必填 | 可选值 / 说明 |
    | --- | --- | --- | --- |
    | endDate | end_date | 是 | 结束时间 yyyy-MM-dd |
    | statDate | stat_date | 是 | 开始时间 yyyy-MM-dd |
    | site | site | 是 | `PC` / `APP` / `WAP` / `all` |
    | pageNo | page_no | 是 | 页号，从 1 开始 |
    | pageSize | page_size | 是 | 1～200 |
    | periodType | period_type | 否 | `DAY`/`L7`/`L30`/`WEEK`/`MON`；不传则不上送 |

    ## 返回（result）
    - `list`：产品维度分析数据（WisProdDetailDTO[]）
    - `count`：数据总量
    """
    client = _test_client(db, payload.store_id)
    data = get_wis_detail_page(
        client,
        end_date=payload.end_date,
        stat_date=payload.stat_date,
        site=payload.site,
        page_no=payload.page_no,
        page_size=payload.page_size,
        period_type=payload.period_type,
    )
    return success_with_dhgate_raw(client, data)


@router.post(
    "/wis/keywordtop10",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调][单店][数据] 关键词 TOP（dh.wis.keywordtop10.info$1.0）",
)
@_expose_raw_on_error
def test_wis_keywordtop10(
    payload: WisKeywordTop10TestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    下载「关键词 TOP」数据（数据 API 限免三件套之一）。

    ## 官方
    - method：`dh.wis.keywordtop10.info`，version=`1.0`，级别 A，超时约 30 秒
    - 关联：店铺 `dh.wis.core.info` / 单品 `dh.wis.detail.page`；`itemCode` 可来自 `dh.item.list`

    ## 业务入参（手册均标必填）
    | 官方字段 | 本接口字段 | 必填 | 可选值 / 说明 |
    | --- | --- | --- | --- |
    | platformId | platform_id | 是 | 手册示例 `ALL` |
    | searchDateType | search_date_type | 是 | 手册示例 `12`；其它以实返为准 |
    | itemCode | item_code | 是 | **产品编码**（数字）；官网说明列可能有笔误 |
    | siteId | site_id | 是 | 手册示例 `EN` |

    ## 返回（result）
    - `list`：关键词 TOP 列表（WisProdKwordsTop10DTO[]）
    """
    client = _test_client(db, payload.store_id)
    data = get_wis_keywordtop10_info(
        client,
        platform_id=payload.platform_id,
        search_date_type=payload.search_date_type,
        item_code=payload.item_code,
        site_id=payload.site_id,
    )
    return success_with_dhgate_raw(client, data)


@router.post(
    "/seller/ad/order-report",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调][单店][广告] 广告消耗-订单维度（dh.seller.ad.order.report.page$1.0）",
)
@_expose_raw_on_error
def test_seller_ad_order_report(
    payload: SellerAdReportTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按时间、广告类型、产品编码分页查询订单维度广告消耗（**增值 API**，非数据限免）。

    ## 官方
    - method：`dh.seller.ad.order.report.page`，version=`1.0`，级别 A，超时约 15 秒
    - 关联：产品维报表 `dh.seller.ad.prod.report.page`；`itemcode` ← `dh.item.list`

    ## 业务入参（官方均标必填字段）
    | 官方字段 | 本接口字段 | 必填 | 可选值 / 说明 |
    | --- | --- | --- | --- |
    | adType | ad_type | 是（可空） | `` 所有；`shopauto` 全店自动；`ppc` 手动；`prodauto` 商品自动 |
    | itemcode | itemcode | 是 | 商品 ID（小写字段名） |
    | datelineFrom | dateline_from | 是 | yyyy-MM-dd；与结束日期间隔建议 ≤1 个月 |
    | datelineTo | dateline_to | 是 | yyyy-MM-dd |
    | page | page | 是 | 当前页号 |
    | limit | limit | 是 | 每页条数 1～200 |

    ## 返回（result）
    - `sellerAdOrderReportList`、`count`、`pages`
    """
    client = _test_client(db, payload.store_id)
    data = list_seller_ad_order_report(
        client,
        ad_type=payload.ad_type,
        itemcode=payload.itemcode,
        dateline_from=payload.dateline_from,
        dateline_to=payload.dateline_to,
        page=payload.page,
        limit=payload.limit,
    )
    return success_with_dhgate_raw(client, data)


@router.post(
    "/seller/ad/prod-report",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调][单店][广告] 广告消耗-产品维度（dh.seller.ad.prod.report.page$1.0）",
)
@_expose_raw_on_error
def test_seller_ad_prod_report(
    payload: SellerAdReportTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按时间、广告类型、产品编码分页查询产品维度广告消耗（**增值 API**）。

    ## 官方
    - method：`dh.seller.ad.prod.report.page`，version=`1.0`，级别 A，超时约 15 秒
    - 入参与订单维度相同；返回字段为 `sellerAdProdReportList`

    ## 业务入参
    | 官方字段 | 本接口字段 | 必填 | 可选值 / 说明 |
    | --- | --- | --- | --- |
    | adType | ad_type | 是（可空） | `` / `shopauto` / `ppc` / `prodauto` |
    | itemcode | itemcode | 是 | 商品 ID |
    | datelineFrom | dateline_from | 是 | yyyy-MM-dd（建议跨度 ≤1 个月） |
    | datelineTo | dateline_to | 是 | yyyy-MM-dd |
    | page | page | 是 | 页码 |
    | limit | limit | 是 | 1～200 |

    ## 返回（result）
    - `sellerAdProdReportList`、`count`、`pages`
    """
    client = _test_client(db, payload.store_id)
    data = list_seller_ad_prod_report(
        client,
        ad_type=payload.ad_type,
        itemcode=payload.itemcode,
        dateline_from=payload.dateline_from,
        dateline_to=payload.dateline_to,
        page=payload.page,
        limit=payload.limit,
    )
    return success_with_dhgate_raw(client, data)


@router.post(
    "/category/list",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调][单店][类目] 发布类目递归入库（dh.category.list$2.0）",
)
@_expose_raw_on_error
def test_list_categories(
    payload: CategoryListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    递归拉取敦煌发布类目并写入 product_category_dh。

    ## 官方
    - method：`dh.category.list`，version=`2.0`
    - 官方业务入参：`parentId`（可选；不传返回一级类目）
    - 本联调：从根递归全量拉取并入库，**无 parentId 请求体字段**；`store_id` 仅取 token

    ## 入库行为（本地）
    - 每入库一条立即 commit；已有 `cate_pub_id` 跳过不再下钻
    - 中断后可重跑续传；`result.list` 仅含本次新入库类目
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
    summary="[联调][单店][公共] 计件单位全量入库（dh.base.measures.get$1.0）",
)
@_expose_raw_on_error
def test_sync_measures_units(
    payload: MeasuresListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    拉取敦煌计件单位列表并覆盖本地 measures_unit_dh。

    ## 官方
    - method：`dh.base.measures.get`，version=`1.0`（公共 API · 基础）
    - **无业务入参**；`store_id` 仅取 access_token
    - 返回关键字段：`meauserList`（拼写以文档为准）

    ## 入库行为（本地）
    - 每次先清空再全量写入
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
    summary="[联调][单店][类目] 类目佣金率全量入库（dh.categorys.commissions$1.0）",
)
@_expose_raw_on_error
def test_sync_commission_rates(
    payload: CommissionRateListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    拉取全部类目佣金率并覆盖本地 commissions_rate_dh。

    ## 官方
    - method：`dh.categorys.commissions`，version=`1.0`
    - **无业务入参**；返回关键字段：`list`
    - `store_id` 仅取 token；佣金率按类目全局存储，不按店铺隔离

    ## 入库行为（本地）
    - 每次先清空再全量写入
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
    summary="[联调][单店][类目] 类目详情与属性（dh.category.get$2.0）",
)
@_expose_raw_on_error
def test_get_category(
    payload: CategoryGetTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按叶子发布类目 ID 获取类目详情：属性、属性值、关键词限制等。

    ## 官方
    - method：`dh.category.get`，version=`2.0`，超时约 15 秒

    ## 业务入参
    | 官方字段 | 本接口字段 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | catePubId | cate_pub_id | 是 | 必须是有效**叶子**类目 ID（来自 list / 本地表） |

    ## 返回关键字段（result）
    - `catePubId`、`pubName`、`pubNameCn`、`leaf`、`pareCatePubId`
    - `categoryPubAttrList`、`categoryPubAttrgroupList`
    - `excludeKeyWords`、`inlucdeKeyWords`、`remark`（拼写以文档为准）
    """
    client = _test_client(db, payload.store_id)
    data = get_category(client, cate_pub_id=payload.cate_pub_id)
    return success_with_dhgate_raw(client, data)


@router.post(
    "/category/path/get",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调][单店][类目] 类目路径（dh.category.path.get$2.0）",
)
@_expose_raw_on_error
def test_get_category_path(
    payload: CategoryPathGetTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按类目 ID 获取从根到当前类目的主线路径。

    ## 官方
    - method：`dh.category.path.get`，version=`2.0`

    ## 业务入参
    | 官方字段 | 本接口字段 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | catePubId | cate_pub_id | 是 | 发布类目 ID |

    ## 返回（result）
    - `categoryPublishList`：由上至下，含当前类目
    """
    client = _test_client(db, payload.store_id)
    data = get_category_path(client, cate_pub_id=payload.cate_pub_id)
    return success_with_dhgate_raw(client, data)


@router.post(
    "/item/get",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调][单店][商品] 产品详情（dh.item.get$2.0）",
)
@_expose_raw_on_error
def test_get_item(
    payload: ItemGetTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按商品编码获取卖家产品详情（SKU、属性、图片、包装、销售设置等）。

    ## 官方
    - method：`dh.item.get`，version=`2.0`，超时约 30 秒

    ## 业务入参
    | 官方字段 | 本接口字段 | 必填 | 可选值 / 说明 |
    | --- | --- | --- | --- |
    | itemCode | item_code | 是 | 来自 dh.item.list |
    | siteId | site_id | 否 | `EN`(默认) / `RU` / `ES` / `ID` |

    ## 返回关键字段（result）
    - `itemBase`、`itemSkuList`、`itemImgList`、`itemAttrList`
    - `itemInventory`、`itemPackage`、`itemWholesaleRangeList`
    - `shippingModelId`、`sizeTemplateId`、`afterSaleTemplateId`、`state`、`catePubId`、`siteId` 等
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
    summary="[联调][单店][商品] 上架/下架（dh.item.upshelf.list / downshelf.list$2.0）",
)
@_expose_raw_on_error
def test_item_shelf(
    payload: ItemShelfTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按 action 调用敦煌批量上架或下架（仅支持 POST）。

    ## 官方 method（由 action 选择）
    - `action=0` → `dh.item.downshelf.list$2.0` 下架
    - `action=1` → `dh.item.upshelf.list$2.0` 上架

    ## 业务入参
    | 官方字段 | 本接口字段 | 必填 | 可选值 / 说明 |
    | --- | --- | --- | --- |
    | itemCodes | item_codes | 是 | 逗号分隔字符串，最多 200 个 |
    | siteId | site_id | 否 | EN / RU / ES / ID；不传则不上送 |
    | （本地） | action | 是 | `0` 下架；`1` 上架 |

    ## 返回关键字段（敦煌侧）
    - `isSuccess`、`resultList`
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
    summary="[联调][单店][产品组] 产品组列表（dh.item.group.list$2.0）",
)
@_expose_raw_on_error
def test_list_item_groups(
    payload: ItemGroupListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    获取当前店铺产品组列表（itemGroupList）。

    ## 官方
    - method：`dh.item.group.list`，version=`2.0`，超时约 15 秒

    ## 业务入参
    | 官方字段 | 本接口字段 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | pageNo | page_no | 是 | 从 1 开始 |
    | pageSize | page_size | 是 | 1～200 |
    | containChildGroup | contain_child_group | 否 | true/false；不传默认 false |
    | parentGroupId | parent_group_id | 否 | 父组 ID |
    | groupCnName | group_cn_name | 否 | 中文名筛选 |
    | groupEnName | group_en_name | 否 | 英文名筛选 |

    ## 返回（result）
    - `itemGroupList`、`count`、`pageTotal`；列表项 `groupId` → 发布入参 `itemGroupId`
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
    summary="[联调][单店][商品] 产品长描（dh.item.html.get / dh.product.html.get）",
)
@_expose_raw_on_error
def test_get_item_html(
    payload: ItemGetTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按商品编码获取产品长描 htmlContent。

    ## 官方
    - method：`dh.item.html.get` / 旧名 `dh.product.html.get`，本联调走现有封装
    - 手册 2.0：`dh.item.html.get$2.0`；关键入参 `itemCode`（必填）、`siteId`（可选）

    ## 业务入参
    | 官方字段 | 本接口字段 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | itemCode / itemcode | item_code | 是 | 商品编码 |
    | siteId | site_id | 否 | EN/RU/ES/ID；封装侧可能仅本地对齐 |

    ## 返回（result）
    - `htmlContent`
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
    summary="[联调][单店][相册] 微调产品主图并上传（dh.album.img.upload$2.1）",
)
@_expose_raw_on_error
async def test_tweak_main_image(
    db: Session = Depends(get_db),
    store_id: int = Form(
        ...,
        description="【联调必填·本地】店铺 ID，取 access_token",
    ),
    item_code: str | None = Form(
        default=None,
        description=(
            "【联调可选·本地】产品编码；有值则 dh.item.get 取第一张主图，"
            "忽略上传文件"
        ),
    ),
    imgBase64: UploadFile | None = File(
        default=None,
        description=(
            "【联调可选·本地】参考主图文件（转 base64 后上送）；"
            "仅当未传 item_code 时使用"
        ),
    ),
) -> ApiResponse[dict[str, Any]]:
    """
    获取参考主图 → Pillow 微调防重复 → 调用相册上传。

    ## 官方（实际上送）
    - method：`dh.album.img.upload`，version=`2.1`，仅支持 POST，超时约 60 秒
    - 官方必填：`funType`、`imgName`、`imgBase64`（由服务封装填充）
    - 官方可选：`imgBannerName`、`markPosition`

    ## 本联调入参（二选一提供参考图）
    | 字段 | 必填 | 说明 |
    | --- | --- | --- |
    | store_id | 是 | 目标店 token |
    | item_code | 条件 | 有值：拉详情第一张主图（image.dhgate.com） |
    | imgBase64 | 条件 | 文件上传；仅无 item_code 时使用 |

    ## 返回关键字段（上传结果）
    - `imgName`、`imgMd5`、`imgUrl`、`result`、`imgSize` 等
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
    summary="[联调][单店][售后] 售后模板列表（dh.item.aftersale.list$2.0）",
)
@_expose_raw_on_error
def test_list_item_aftersale(
    payload: ItemAftersaleListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    获取当前店铺售后模板列表（afterSaleList）。

    ## 官方
    - method：`dh.item.aftersale.list`，version=`2.0`，超时约 30 秒
    - **无业务入参**；`store_id` 仅取 token
    - 返回 `afterSaleList`（含 afterSaleTemplateId 等），供 `dh.item.add` 填 afterSaleTemplateId
    - 常与 `dh.category.is3Ccategory` 配合判断是否需要售后模板
    """
    client = _test_client(db, payload.store_id)
    data = list_item_aftersale(client)
    return success_with_dhgate_raw(client, data)


@router.post(
    "/shipping/template/list",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调][单店][物流] 运费模板列表（dh.shipping.template.list$2.0）",
)
@_expose_raw_on_error
def test_list_shipping_templates(
    payload: ShippingTemplateListTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    获取当前店铺运费模板列表（shippingModelList）。

    ## 官方
    - method：`dh.shipping.template.list`，version=`2.0`，超时约 15 秒
    - **无业务入参**；`store_id` 仅取 token
    - 返回 `shippingModelList`；模板 ID 对应发布入参 `shippingModelId`
    - 详情可再调 `dh.shipping.template.get`（入参 shippingTempId）
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
    summary="[联调][单店][商品] 裂变发布（源店 dh.item.get + 目标店 dh.item.add$2.0）",
)
@_expose_raw_on_error
def test_fission_add_item(
    payload: ItemFissionAddTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按本地种子商品 pid 查出源店与 item_code，拉最新详情后裂变发布到目标店。

    ## 官方链路
    - 源店：`dh.item.get$2.0` + 长描（`dh.item.html.get` / `dh.product.html.get`）
    - 目标店：`dh.album.img.upload$2.1`（微调主图）+ `dh.item.add$2.0` 发布
    - 可选辅助：`dh.item.aftersale.list`、`dh.shipping.template.list`

    ## 本联调入参
    | 字段 | 必填 | 说明 |
    | --- | --- | --- |
    | target_store_id | 是 | 目标店 ID（发布 token） |
    | pid | 是 | 本地 `product_dh.id` → 源店 store_id / item_code / site_id |
    | site_id | 否 | EN/RU/ES/ID；不传用种子再默认 EN |
    | update_info.item_name | 否 | → itemBase.itemName，最多 140 字 |
    | update_info.afterSaleTemplateId | 否 | 有值则直接作 afterSaleTemplateId |
    | update_info.shippingTempId | 否 | 有值则映射 shippingModelId |

    ## 行为摘要
    - 长描写入发布体 `itemBase.htmlContent`（响应不回传长描正文）
    - 发布前微调上传第一张主图，替换 `itemImgList[0]` 的 imgUrl/imgMd5
    - 未传模板 ID：同店沿用原值；跨店取目标店默认售后及新手运费模板（modelType=10）
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
        _remember_client(client)
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
