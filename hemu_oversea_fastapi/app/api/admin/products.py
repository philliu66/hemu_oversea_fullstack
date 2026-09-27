"""管理端商品模块。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Pagination, require_admin_user
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.product import (
    DhProductDetailPublic,
    DhProductDetailRequest,
    DhProductListRequest,
    DhProductPublic,
)
from app.services import products as product_service

router = APIRouter(
    prefix="/product",
    tags=["admin:product"],
    dependencies=[Depends(require_admin_user)],
)


@router.post(
    "/dh/list",
    response_model=ApiResponse[PageData[DhProductPublic]],
    summary="查询敦煌商品列表（分页）",
)
def list_dh_products(
    payload: DhProductListRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[DhProductPublic]]:
    """
    分页查询 product_dh 敦煌商品。

    - type：0=全部，1=仅种子商品（默认）
    - state：可选，按状态编码筛选（如 100100）
    - 支持 item_code / item_name / store_id / cate_pub_id 筛选
    - cate_pub_id：按种子商品分类树筛选，包含选中类目及其下级
    - sort：0=同步时间倒序（默认），1=同步时间正序
    """
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        product_service.list_dh_products(
            db,
            list_type=payload.type,
            state=payload.state,
            item_code=payload.item_code,
            item_name=payload.item_name,
            store_id=payload.store_id,
            cate_pub_id=payload.cate_pub_id,
            sort=payload.sort,
            pagination=pagination,
        )
    )


@router.post(
    "/dh/detail",
    response_model=ApiResponse[DhProductDetailPublic],
    summary="查询敦煌商品详情",
)
def get_dh_product_detail(
    payload: DhProductDetailRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[DhProductDetailPublic]:
    """
    按本地商品 ID 读取 product_dh.raw_json，按官网 dh.item.get$2.0 对照解析。

    不请求敦煌接口。字段包括图片、SKU、产品属性、自定义规格、
    运费/售后/尺码模板、卖点、折扣区间、备货、兼容属性、销售国家定价、定制信息。
    类目全路径请另调 /api/v1/admin/categories/dh/path。
    """
    return success(product_service.get_dh_product_detail(db, payload.id))
