from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import (
    Pagination,
    require_admin_user,
    require_perm,
)
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.supplier import (
    SupplierCreate,
    SupplierDelete,
    SupplierDetail,
    SupplierDetailPublic,
    SupplierList,
    SupplierPublic,
    SupplierUpdate,
)
from app.services import permissions as perm_service
from app.services import suppliers as supplier_service

router = APIRouter(
    prefix="/suppliers",
    tags=["admin:suppliers"],
    dependencies=[Depends(require_admin_user)],
)


@router.post("/list", response_model=ApiResponse[PageData[SupplierPublic]])
def list_suppliers(
    payload: SupplierList,
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[SupplierPublic]]:
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        supplier_service.list_suppliers(
            db, keyword=payload.keyword, pagination=pagination
        )
    )


@router.post("/detail", response_model=ApiResponse[SupplierDetailPublic])
def detail_supplier(
    payload: SupplierDetail,
    db: Session = Depends(get_db),
) -> ApiResponse[SupplierDetailPublic]:
    supplier = supplier_service.get_supplier(db, payload.id)
    detail = SupplierDetailPublic.model_validate(supplier)
    detail.admin_username = supplier_service.get_supplier_admin_username(
        db, supplier.id
    )
    detail.permission_codes = perm_service.get_supplier_permission_codes(
        db, supplier.id
    )
    return success(detail)


@router.post("/create", status_code=201, response_model=ApiResponse[SupplierPublic])
def create_supplier(
    payload: SupplierCreate,
    current_user: User = Depends(require_perm("supplier.create")),
    db: Session = Depends(get_db),
) -> ApiResponse[SupplierPublic]:
    supplier = supplier_service.create_supplier(
        db,
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        admin_username=payload.admin_username,
        admin_password=payload.admin_password,
        permission_codes=payload.permission_codes,
        created_by=current_user.id,
    )
    return success(SupplierPublic.model_validate(supplier))


@router.post("/update", response_model=ApiResponse[SupplierPublic])
def update_supplier(
    payload: SupplierUpdate,
    _: User = Depends(require_perm("supplier.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[SupplierPublic]:
    supplier = supplier_service.update_supplier(
        db,
        supplier_id=payload.id,
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        permission_codes=payload.permission_codes,
    )
    return success(SupplierPublic.model_validate(supplier))


@router.post("/delete", response_model=ApiResponse[dict])
def delete_supplier(
    payload: SupplierDelete,
    _: User = Depends(require_perm("supplier.delete")),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    supplier_service.soft_delete_supplier(db, supplier_id=payload.id)
    return success({})
