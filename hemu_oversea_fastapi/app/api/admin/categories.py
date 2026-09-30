"""管理端商品分类模块。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_admin_user
from app.core.errors import bad_request
from app.models.user import User
from app.schemas.common import ApiResponse, success
from app.schemas.product import (
    DhCategoryAttrsPublic,
    DhCategoryAttrsRequest,
    DhCategoryListRequest,
    DhCategoryPathPublic,
    DhCategoryPathRequest,
    DhCategoryPublic,
    DhCategorySearchRequest,
    DhCommissionRatePublic,
    DhCommissionRateRequest,
    DhSeedCategoryPublic,
)
from app.services import products as product_service
from app.services.commission_rates_dh import get_commission_rate_by_cate_id

router = APIRouter(
    prefix="/categories",
    tags=["admin:categories"],
    dependencies=[Depends(require_admin_user)],
)


@router.post(
    "/dh/list",
    response_model=ApiResponse[list[DhCategoryPublic]],
    summary="查询敦煌商品分类（按父级一层）",
)
def list_dh_categories(
    payload: DhCategoryListRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[list[DhCategoryPublic]]:
    """
    按父类目 ID 查询直接子分类，供前端逐层展开。

    - 不传 / 传空 parent_id：返回一级类目
    - 传入某 cate_pub_id：返回该类目下的直接子类
    """
    items = product_service.list_dh_categories_by_parent(
        db,
        parent_id=payload.parent_id,
    )
    return success(items)


@router.post(
    "/dh/seed-list",
    response_model=ApiResponse[list[DhSeedCategoryPublic]],
    summary="查询种子商品分类（按父级一层）",
)
def list_dh_seed_categories(
    payload: DhCategoryListRequest,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[list[DhSeedCategoryPublic]]:
    """
    按父类目 ID 查询种子商品（product_dh.is_seed=1）涉及的直接子分类。

    - 不传 / 传空 parent_id：返回一级类目
    - 传入某 cate_pub_id：返回该类目下仍包含种子商品的直接子类
    - product_count：根类目由 groupby 汇总向上累计，其余类目为下级商品数合计
    - 仅统计当前账号所属供应商的种子商品
    """
    if current_user.supplier_id is None:
        raise bad_request("当前账号未绑定供应商，无法查询种子分类")
    items = product_service.list_dh_seed_categories_by_parent(
        db,
        parent_id=payload.parent_id,
        supplier_id=current_user.supplier_id,
    )
    return success(items)


@router.post(
    "/dh/search",
    response_model=ApiResponse[list[DhCategoryPublic]],
    summary="搜索敦煌商品分类",
)
def search_dh_categories(
    payload: DhCategorySearchRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[list[DhCategoryPublic]]:
    """
    按中英文类目名称（或 cate_pub_id）模糊搜索。

    默认仅返回叶子类目，供商品详情下拉搜索选用。
    """
    items = product_service.search_dh_categories(
        db,
        keyword=payload.keyword,
        leaf_only=payload.leaf_only,
        limit=payload.limit,
    )
    return success(items)


@router.post(
    "/dh/path",
    response_model=ApiResponse[DhCategoryPathPublic],
    summary="查询敦煌商品分类全路径",
)
def get_dh_category_path(
    payload: DhCategoryPathRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[DhCategoryPathPublic]:
    """
    按类目主键 ID 获取从根到当前类目的全路径。

    数据来源本地 product_category_dh，按父子关系向上回溯。
    path_name 格式：中文(英文) > 中文(英文) > …
    """
    return success(product_service.get_dh_category_path(db, payload.id))


@router.post(
    "/dh/attrs",
    response_model=ApiResponse[DhCategoryAttrsPublic],
    summary="查询敦煌叶子类目属性",
)
def get_dh_category_attrs(
    payload: DhCategoryAttrsRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[DhCategoryAttrsPublic]:
    """
    按类目主键 ID 获取该叶子类目下的属性及可选/可填属性值。

    内部调用 dh.category.get$2.0。
    """
    return success(product_service.get_dh_category_attrs(db, category_id=payload.id))


@router.post(
    "/dh/commission-rate/get",
    response_model=ApiResponse[DhCommissionRatePublic],
    summary="查询类目佣金率",
)
def get_dh_commission_rate(
    payload: DhCommissionRateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[DhCommissionRatePublic]:
    """
    按类目 ID（cateId）查询本地 commissions_rate_dh 佣金率。

    数据由 testAPI dh.categorys.commissions 全量同步入库，本接口不请求敦煌。
    """
    return success(get_commission_rate_by_cate_id(db, cate_id=payload.cate_id))
