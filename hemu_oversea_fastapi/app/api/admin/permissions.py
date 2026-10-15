from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_admin_user, require_perm, require_platform_admin
from app.core.errors import forbidden
from app.core.roles import Role
from app.models.user import User
from app.schemas.common import ApiResponse, success
from app.schemas.permission import (
    PermissionCreate,
    PermissionDelete,
    PermissionDetail,
    PermissionPublic,
    PermissionTreeNode,
    PermissionTreeQuery,
    PermissionUpdate,
)
from app.services import permissions as perm_service

router = APIRouter(
    prefix="/permissions",
    tags=["admin:permissions"],
    dependencies=[Depends(require_admin_user)],
)


@router.post(
    "/supplier-assignable-tree",
    response_model=ApiResponse[list[PermissionTreeNode]],
)
def supplier_assignable_tree(
    current_user: User = Depends(require_perm("supplier.create")),
    db: Session = Depends(get_db),
) -> ApiResponse[list[PermissionTreeNode]]:
    """创建/编辑供应商时勾选权限池用的树。"""
    if current_user.role not in {
        Role.PLATFORM_ADMIN.value,
        Role.PLATFORM_STAFF.value,
    }:
        raise forbidden()
    return success(perm_service.supplier_assignable_permission_tree(db))


@router.post(
    "/tree",
    response_model=ApiResponse[list[PermissionTreeNode]],
    summary="权限目录树",
)
def permission_tree(
    payload: PermissionTreeQuery,
    _current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[list[PermissionTreeNode]]:
    """平台管理员维护权限目录时用的完整树。"""
    scopes = set(payload.scopes) if payload.scopes else None
    return success(
        perm_service.list_permission_tree(
            db,
            scopes=scopes,
            include_inactive=payload.include_inactive,
        )
    )


@router.post(
    "/detail",
    response_model=ApiResponse[PermissionPublic],
    summary="权限详情",
)
def permission_detail(
    payload: PermissionDetail,
    _current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[PermissionPublic]:
    return success(perm_service.get_permission(db, payload.id))


@router.post(
    "/create",
    status_code=201,
    response_model=ApiResponse[PermissionPublic],
    summary="新增权限",
)
def create_permission(
    payload: PermissionCreate,
    _current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[PermissionPublic]:
    return success(
        perm_service.create_permission(
            db,
            code=payload.code,
            parent_id=payload.parent_id,
            parent_code=payload.parent_code,
            perm_type=payload.type,
            title=payload.title,
            path=payload.path,
            scope=payload.scope,
            sort_order=payload.sort_order,
            is_active=payload.is_active,
            grant_to_all_suppliers=payload.grant_to_all_suppliers,
        )
    )


@router.post(
    "/update",
    response_model=ApiResponse[PermissionPublic],
    summary="更新权限",
)
def update_permission(
    payload: PermissionUpdate,
    _current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[PermissionPublic]:
    fields = payload.model_dump(exclude_unset=True)
    fields.pop("id", None)
    return success(
        perm_service.update_permission(
            db,
            permission_id=payload.id,
            fields=fields,
        )
    )


@router.post(
    "/delete",
    response_model=ApiResponse[dict],
    summary="删除权限",
)
def delete_permission(
    payload: PermissionDelete,
    _current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    perm_service.delete_permission(db, permission_id=payload.id)
    return success({})
