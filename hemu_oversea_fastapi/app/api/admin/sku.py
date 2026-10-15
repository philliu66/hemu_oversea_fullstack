from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Pagination, require_admin_user, require_perm
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.sku_attr_template import DhSkuBaseInfoList
from app.schemas.utils import DhSkuBaseInfoPublic
from app.services import sku_base_infos_dh as sku_base_info_service
from app.services.supplier_scope import resolve_supplier_id

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
    supplier_id = resolve_supplier_id(db, current_user, payload.supplier_id)
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        sku_base_info_service.list_sku_base_infos(
            db,
            supplier_id=supplier_id,
            keyword=payload.keyword,
            pagination=pagination,
        )
    )
