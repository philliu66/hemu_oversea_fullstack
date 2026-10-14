from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Pagination, require_admin_user, require_perm
from app.core.errors import bad_request
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.sku_attr_template import DhSkuBaseInfoList
from app.schemas.utils import DhSkuBaseInfoPublic
from app.services import sku_base_infos_dh as sku_base_info_service

router = APIRouter(
    prefix="/sku/dh",
    tags=["admin:sku"],
    dependencies=[Depends(require_admin_user)],
)


@router.post(
    "/base-info/list",
    response_model=ApiResponse[PageData[DhSkuBaseInfoPublic]],
)
def list_sku_base_info(
    payload: DhSkuBaseInfoList,
    current_user: User = Depends(require_perm("template.skuAttr")),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[DhSkuBaseInfoPublic]]:
    if current_user.supplier_id is None:
        raise bad_request("当前账号未绑定供应商，无法查询 SKU")
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        sku_base_info_service.list_sku_base_infos(
            db,
            supplier_id=current_user.supplier_id,
            keyword=payload.keyword,
            pagination=pagination,
        )
    )
