"""敦煌官方 API 联调（单店铺，仅调试）。

路径：/api/v1/common/testAPI/dhgate
多店编排见：/api/v1/common/testAPI/dhgate/commerce

所有接口统一通过 success_with_dhgate_raw 返回：
- result: 业务结果
- raw: 最近一次敦煌原始响应
- raw_calls: 本次请求内全部调用明细
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
# from app.core.deps import get_current_account
from app.schemas.common import ApiResponse, success
from app.schemas.test_api.dhgate import (
    CategoryGetTestRequest,
    CategoryListTestRequest,
    CategoryPathGetTestRequest,
    ItemGetTestRequest,
    PunishBrandListTestRequest,
    PunishListTestRequest,
)
from app.services.dhgate import (
    DhgateClient,
    get_category,
    get_category_path,
    get_dhgate_client,
    get_item,
    list_punish,
    list_punish_brand,
)
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
