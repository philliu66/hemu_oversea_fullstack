from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_admin_user, require_perm
from app.core.roles import normalize_portal_role, Role
from app.core.errors import forbidden
from app.models.user import User
from app.schemas.common import ApiResponse, success
from app.schemas.permission import PermissionTreeNode
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
    role = normalize_portal_role(current_user.role) or current_user.role
    if role not in {
        Role.PLATFORM_ADMIN.value,
        Role.PLATFORM_STAFF.value,
        Role.SUPER_ADMIN.value,
    }:
        raise forbidden()
    return success(perm_service.supplier_assignable_permission_tree(db))
