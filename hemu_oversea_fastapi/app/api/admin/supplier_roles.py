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
    tags=["admin:roles"],
    dependencies=[Depends(require_admin_user)],
)


@router.post(
    "/list",
    response_model=ApiResponse[PageData[RolePublic]],
    summary="[供应商] 角色列表",
)
def list_roles(
    payload: RoleList,
    current_user: User = Depends(require_perm("personnel.role")),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[RolePublic]]:
    """
    分页查询当前供应商的角色。

    - 调用者：仅供应商管理员，权限码 `personnel.role`
    - 只返回该账号 `supplier_id` 下的角色
    - 返回含 `permission_codes`；可勾选范围不超过该供应商开通池
    """
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


@router.post(
    "/detail",
    response_model=ApiResponse[RolePublic],
    summary="[供应商] 角色详情",
)
def detail_role(
    payload: RoleDetail,
    current_user: User = Depends(require_perm("personnel.role")),
    db: Session = Depends(get_db),
) -> ApiResponse[RolePublic]:
    """
    按 ID 查询当前供应商的一个角色及其权限码。

    - 调用者：仅供应商管理员，权限码 `personnel.role`
    - 角色须属于当前账号的供应商；平台角色或其他供应商角色按不存在处理
    """
    supplier_id = role_service.assert_supplier_admin_actor(current_user)
    return success(
        role_service.get_role(db, payload.id, supplier_id=supplier_id)
    )


@router.post(
    "/create",
    status_code=201,
    response_model=ApiResponse[RolePublic],
    summary="[供应商] 新建角色",
)
def create_role(
    payload: RoleCreate,
    current_user: User = Depends(require_perm("personnel.role.create")),
    db: Session = Depends(get_db),
) -> ApiResponse[RolePublic]:
    """
    为当前供应商新建角色，并写入权限码。

    - 调用者：仅供应商管理员，权限码 `personnel.role.create`
    - 角色挂在当前账号的 `supplier_id` 上；同一供应商内未删除角色名称不可重复
    - `permission_codes` 不得超过该供应商开通池，也不得超过当前账号可分配范围
    """
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


@router.post(
    "/update",
    response_model=ApiResponse[RolePublic],
    summary="[供应商] 修改角色",
)
def update_role(
    payload: RoleUpdate,
    current_user: User = Depends(require_perm("personnel.role.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[RolePublic]:
    """
    修改当前供应商角色的名称、备注、启用状态或权限码。

    - 调用者：仅供应商管理员，权限码 `personnel.role.update`
    - 只改本供应商的角色
    - 传入 `permission_codes` 时整份替换，且不得超过开通池
    """
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


@router.post(
    "/delete",
    response_model=ApiResponse[dict],
    summary="[供应商] 删除角色",
)
def delete_role(
    payload: RoleDelete,
    current_user: User = Depends(require_perm("personnel.role.delete")),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    """
    软删除当前供应商的角色，并解除员工、权限关联。

    - 调用者：仅供应商管理员，权限码 `personnel.role.delete`
    - 只删本供应商的角色；删除后停用，并清掉该角色的用户绑定与权限
    """
    supplier_id = role_service.assert_supplier_admin_actor(current_user)
    role_service.delete_role(db, supplier_id=supplier_id, role_id=payload.id)
    return success({})


@router.post(
    "/options",
    response_model=ApiResponse[list[dict]],
    summary="[供应商] 角色下拉",
)
def role_options(
    current_user: User = Depends(require_perm("personnel.staff")),
    db: Session = Depends(get_db),
) -> ApiResponse[list[dict]]:
    """
    返回当前供应商启用中的角色，供员工表单选择。

    - 调用者：仅供应商管理员，权限码 `personnel.staff`
    - 只含本供应商未删除且已启用的角色
    """
    supplier_id = role_service.assert_supplier_admin_actor(current_user)
    return success(role_service.list_role_options(db, supplier_id=supplier_id))


@router.post(
    "/permission-tree",
    response_model=ApiResponse[list[PermissionTreeNode]],
    summary="[供应商] 可分配权限树",
)
def permission_tree(
    current_user: User = Depends(require_perm("personnel.role")),
    db: Session = Depends(get_db),
) -> ApiResponse[list[PermissionTreeNode]]:
    """
    返回当前供应商角色可勾选的权限树。

    - 调用者：仅供应商管理员，权限码 `personnel.role`
    - 只含该供应商开通池内的权限
    """
    supplier_id = role_service.assert_supplier_admin_actor(current_user)
    return success(perm_service.supplier_pool_permission_tree(db, supplier_id))
