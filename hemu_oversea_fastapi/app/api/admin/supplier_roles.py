from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Pagination, require_admin_user, require_perm
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.permission import (
    PermissionTreeNode,
    RoleCreate,
    RoleDelete,
    RoleDetail,
    RoleList,
    RolePublic,
    RoleUpdate,
)
from app.services import biz_roles as role_service
from app.services import permissions as perm_service

router = APIRouter(
    prefix="/supplier-roles",
    tags=["admin:supplier-roles"],
    dependencies=[Depends(require_admin_user)],
)


@router.post("/list", response_model=ApiResponse[PageData[RolePublic]])
def list_roles(
    payload: RoleList,
    current_user: User = Depends(require_perm("personnel.role")),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[RolePublic]]:
    supplier_id = role_service.assert_supplier_admin_actor(current_user)
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        role_service.list_roles(
            db,
            supplier_id=supplier_id,
            keyword=payload.keyword,
            pagination=pagination,
        )
    )


@router.post("/detail", response_model=ApiResponse[RolePublic])
def detail_role(
    payload: RoleDetail,
    current_user: User = Depends(require_perm("personnel.role")),
    db: Session = Depends(get_db),
) -> ApiResponse[RolePublic]:
    supplier_id = role_service.assert_supplier_admin_actor(current_user)
    return success(
        role_service.get_role(db, payload.id, supplier_id=supplier_id)
    )


@router.post("/create", status_code=201, response_model=ApiResponse[RolePublic])
def create_role(
    payload: RoleCreate,
    current_user: User = Depends(require_perm("personnel.role.create")),
    db: Session = Depends(get_db),
) -> ApiResponse[RolePublic]:
    supplier_id = role_service.assert_supplier_admin_actor(current_user)
    return success(
        role_service.create_role(
            db,
            actor=current_user,
            supplier_id=supplier_id,
            name=payload.name,
            remark=payload.remark,
            permission_codes=payload.permission_codes,
        )
    )


@router.post("/update", response_model=ApiResponse[RolePublic])
def update_role(
    payload: RoleUpdate,
    current_user: User = Depends(require_perm("personnel.role.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[RolePublic]:
    supplier_id = role_service.assert_supplier_admin_actor(current_user)
    return success(
        role_service.update_role(
            db,
            actor=current_user,
            supplier_id=supplier_id,
            role_id=payload.id,
            name=payload.name,
            remark=payload.remark,
            is_active=payload.is_active,
            permission_codes=payload.permission_codes,
        )
    )


@router.post("/delete", response_model=ApiResponse[dict])
def delete_role(
    payload: RoleDelete,
    current_user: User = Depends(require_perm("personnel.role.delete")),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    supplier_id = role_service.assert_supplier_admin_actor(current_user)
    role_service.delete_role(db, supplier_id=supplier_id, role_id=payload.id)
    return success({})


@router.post("/options", response_model=ApiResponse[list[dict]])
def role_options(
    current_user: User = Depends(require_perm("personnel.staff")),
    db: Session = Depends(get_db),
) -> ApiResponse[list[dict]]:
    supplier_id = role_service.assert_supplier_admin_actor(current_user)
    return success(role_service.list_role_options(db, supplier_id=supplier_id))


@router.post("/permission-tree", response_model=ApiResponse[list[PermissionTreeNode]])
def permission_tree(
    current_user: User = Depends(require_perm("personnel.role")),
    db: Session = Depends(get_db),
) -> ApiResponse[list[PermissionTreeNode]]:
    supplier_id = role_service.assert_supplier_admin_actor(current_user)
    return success(perm_service.supplier_pool_permission_tree(db, supplier_id))
