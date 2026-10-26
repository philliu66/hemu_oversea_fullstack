"""管理端商品模块。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Pagination, require_admin_user, require_perm
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.product import (
    DhProductDetailPublic,
    DhProductDetailRequest,
    DhProductListRequest,
    DhProductPublic,
    DhProductPublishPublic,
    DhProductPublishRequest,
    DhProductSyncPublic,
    DhProductSyncRequest,
    DhSkuListPricePublic,
    DhSkuListPriceRequest,
)
from app.services import product_publish as product_publish_service
from app.services import products as product_service
from app.services import products_dh as products_dh_service
from app.services.sku_list_prices import calc_sku_list_price
from app.services.supplier_scope import (
    assert_supplier_data_writable,
    resolve_supplier_id,
)

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
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[DhProductPublic]]:
    """
    分页查询 product_dh 敦煌商品。

    - type：0=全部，1=仅种子商品（默认）
    - state：可选，按状态编码筛选（如 100100）
    - 支持 item_code / item_name / store_id / cate_pub_id 筛选
    - cate_pub_id：按种子商品分类树筛选，包含选中类目及其下级
    - sort：0=同步时间倒序（默认），1=同步时间正序
    - 仅返回作用域内供应商的商品（平台需传 supplier_id）
    """
    supplier_id = resolve_supplier_id(db, current_user, payload.supplier_id)
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        product_service.list_dh_products(
            db,
            supplier_id=supplier_id,
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


@router.post(
    "/dh/skulistprice/get",
    response_model=ApiResponse[DhSkuListPricePublic],
    summary="计算指定 SKU 的标价",
)
def get_dh_sku_list_price(
    payload: DhSkuListPriceRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[DhSkuListPricePublic]:
    """
    按供应商 + SKU 编码查询 sku_base_info_dh，并结合店铺折扣与类目佣金计算标价。

    标价 = 基础价格 × 打包数 ×（1 − 佣金率）/ 店铺折扣

    - sku_code 可原样传入，服务端统一清洗后再查表
    - store_id：取该店铺 base_discount
    - cate_id：定价参考类目，默认 000000；按订单金额（基础价×打包数×起订量）匹配佣金区间
    """
    return success(
        calc_sku_list_price(
            db,
            supplier_id=payload.supplier_id,
            sku_code=payload.sku_code,
            store_id=payload.store_id,
            cate_id=payload.cate_id,
        )
    )


@router.post(
    "/dh/sync",
    response_model=ApiResponse[DhProductSyncPublic],
    summary="同步敦煌单个商品",
)
def sync_dh_product(
    payload: DhProductSyncRequest,
    current_user: User = Depends(require_perm("product.list.sync")),
    db: Session = Depends(get_db),
) -> ApiResponse[DhProductSyncPublic]:
    """
    按店铺 ID + 商品编码拉取 dh.item.get 并写入 product_dh。

    - 底层复用 testAPI `/dhgate/commerce/product/sync` 同一套 sync_products_dh
    - 同店铺 + 编码 + 站点已存在则更新，否则新建
    - 敦煌接口失败时按错误返回，message 为敦煌原文
    - 需要按钮权限 `product.list.sync`
    """
    assert_supplier_data_writable(current_user)
    result = products_dh_service.sync_single_product_dh(
        db,
        actor=current_user,
        store_id=payload.store_id,
        item_code=payload.item_code,
        site_id=payload.site_id,
    )
    return success(DhProductSyncPublic.model_validate(result))


@router.post(
    "/dh/publish",
    response_model=ApiResponse[DhProductPublishPublic],
    summary="发布商品",
)
def publish_dh_product(
    payload: DhProductPublishRequest,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[DhProductPublishPublic]:
    """
    发布商品到敦煌（dh.item.add）。

    - type=addfission（默认）：按 mission_data_fission_id 读取任务数据 raw_json 发布，
      成功后写回 item_code / 裂变状态
    - type=addnew：按 info 完整商品数据发布
    """
    assert_supplier_data_writable(current_user)
    result = product_publish_service.publish_product(
        db,
        actor=current_user,
        publish_type=payload.type,
        mission_data_fission_id=payload.mission_data_fission_id,
        info=payload.info,
        supplier_id=payload.supplier_id,
    )
    return success(DhProductPublishPublic.model_validate(result))
