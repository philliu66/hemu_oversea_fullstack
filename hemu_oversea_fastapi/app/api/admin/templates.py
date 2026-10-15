from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Pagination, require_admin_user, require_perm
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.sku_attr_template import (
    SkuAttrTemplateCreate,
    SkuAttrTemplateDelete,
    SkuAttrTemplateDetail,
    SkuAttrTemplateList,
    SkuAttrTemplateListItemPublic,
    SkuAttrTemplateLookup,
    SkuAttrTemplateLookupPublic,
    SkuAttrTemplatePublic,
    SkuAttrTemplateUpdate,
)
from app.services import sku_attr_templates as template_service
from app.services.supplier_scope import resolve_supplier_id

router = APIRouter(
    prefix="/templates/dh",
    tags=["admin:templates"],
    dependencies=[Depends(require_admin_user)],
)


@router.post(
    "/sku-attr-templates/list",
    response_model=ApiResponse[PageData[SkuAttrTemplateListItemPublic]],
)
def list_sku_attr_templates(
    payload: SkuAttrTemplateList,
    current_user: User = Depends(require_perm("template.skuAttr")),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[SkuAttrTemplateListItemPublic]]:
    supplier_id = resolve_supplier_id(db, current_user, payload.supplier_id)
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        template_service.list_sku_attr_templates(
            db,
            supplier_id=supplier_id,
            sku_code=payload.sku_code,
            cate_pub_id=payload.cate_pub_id,
            pagination=pagination,
        )
    )


@router.post(
    "/sku-attr-templates/detail",
    response_model=ApiResponse[SkuAttrTemplatePublic],
)
def detail_sku_attr_template(
    payload: SkuAttrTemplateDetail,
    current_user: User = Depends(require_perm("template.skuAttr")),
    db: Session = Depends(get_db),
) -> ApiResponse[SkuAttrTemplatePublic]:
    supplier_id = resolve_supplier_id(db, current_user, payload.supplier_id)
    return success(
        template_service.get_sku_attr_template(
            db,
            supplier_id=supplier_id,
            template_id=payload.id,
        )
    )


@router.post(
    "/sku-attr-templates/create",
    status_code=201,
    response_model=ApiResponse[SkuAttrTemplatePublic],
)
def create_sku_attr_template(
    payload: SkuAttrTemplateCreate,
    current_user: User = Depends(require_perm("template.skuAttr")),
    db: Session = Depends(get_db),
) -> ApiResponse[SkuAttrTemplatePublic]:
    supplier_id = resolve_supplier_id(db, current_user, payload.supplier_id)
    return success(
        template_service.create_sku_attr_template(
            db,
            supplier_id=supplier_id,
            actor_id=current_user.id,
            sku_code=payload.sku_code,
            cate_pub_id=payload.cate_pub_id,
            raw_json=payload.raw_json,
        )
    )


@router.post(
    "/sku-attr-templates/update",
    response_model=ApiResponse[SkuAttrTemplatePublic],
)
def update_sku_attr_template(
    payload: SkuAttrTemplateUpdate,
    current_user: User = Depends(require_perm("template.skuAttr")),
    db: Session = Depends(get_db),
) -> ApiResponse[SkuAttrTemplatePublic]:
    supplier_id = resolve_supplier_id(db, current_user, payload.supplier_id)
    return success(
        template_service.update_sku_attr_template(
            db,
            supplier_id=supplier_id,
            actor_id=current_user.id,
            template_id=payload.id,
            sku_code=payload.sku_code,
            cate_pub_id=payload.cate_pub_id,
            raw_json=payload.raw_json,
        )
    )


@router.post(
    "/sku-attr-templates/delete",
    response_model=ApiResponse[dict],
)
def delete_sku_attr_template(
    payload: SkuAttrTemplateDelete,
    current_user: User = Depends(require_perm("template.skuAttr")),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    supplier_id = resolve_supplier_id(db, current_user, payload.supplier_id)
    template_service.delete_sku_attr_template(
        db,
        supplier_id=supplier_id,
        template_id=payload.id,
    )
    return success({})


@router.post(
    "/sku-attr-templates/lookup",
    response_model=ApiResponse[SkuAttrTemplateLookupPublic],
)
def lookup_sku_attr_templates(
    payload: SkuAttrTemplateLookup,
    current_user: User = Depends(
        require_perm("template.skuAttr", "mission.fission", require_all=False)
    ),
    db: Session = Depends(get_db),
) -> ApiResponse[SkuAttrTemplateLookupPublic]:
    """裂变编辑等场景：按基型号 + 分类批量查询属性模板。"""
    supplier_id = resolve_supplier_id(db, current_user, payload.supplier_id)
    return success(
        template_service.lookup_sku_attr_templates(
            db,
            supplier_id=supplier_id,
            cate_pub_id=payload.cate_pub_id,
            sku_codes=payload.sku_codes,
        )
    )
