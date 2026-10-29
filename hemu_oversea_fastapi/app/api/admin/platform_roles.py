from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Pagination, require_admin_user, require_perm
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.permission import (
    RoleCreate,
    RoleDelete,
    RoleDetail,
    RoleList,
    RolePublic,
    RoleUpdate,
)
from app.schemas.permission import PermissionTreeNode
from app.services import biz_roles as role_service
from app.services import permissions as perm_service

router = APIRouter(
    prefix="/platform-roles",
    tags=["admin:roles"],
    dependencies=[Depends(require_admin_user)],
)


@router.post(
    "/list",
    response_model=ApiResponse[PageData[RolePublic]],
    summary="[平台] 角色列表",
)
def list_roles(
    payload: RoleList,
    current_user: User = Depends(require_perm("personnel.role")),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[RolePublic]]:
    """
    分页查询平台角色（`supplier_id` 为空）。

    - 调用者：平台管理员或平台员工，权限码 `personnel.role`
    - 可按角色名称关键词筛选
    - 返回含 `permission_codes`；可分配范围是权限目录，不走供应商开通池
    """
    role_service.assert_platform_actor(current_user)
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        role_service.list_roles(
            db,
            supplier_id=None,
            keyword=payload.keyword,
            pagination=pagination,
        )
    )


@router.post(
    "/detail",
    response_model=ApiResponse[RolePublic],
    summary="[平台] 角色详情",
)
def detail_role(
    payload: RoleDetail,
    current_user: User = Depends(require_perm("personnel.role")),
    db: Session = Depends(get_db),
) -> ApiResponse[RolePublic]:
    """
    按 ID 查询一个平台角色及其权限码。

    - 调用者：平台管理员或平台员工，权限码 `personnel.role`
    - 只返回 `supplier_id` 为空的角色；传入供应商角色 ID 按不存在处理
    """
    role_service.assert_platform_actor(current_user)
    return success(role_service.get_role(db, payload.id, supplier_id=None))


@router.post(
    "/create",
    status_code=201,
    response_model=ApiResponse[RolePublic],
    summary="[平台] 新建角色",
)
def create_role(
    payload: RoleCreate,
    current_user: User = Depends(require_perm("personnel.role.create")),
    db: Session = Depends(get_db),
) -> ApiResponse[RolePublic]:
    """
    新建平台角色，并写入权限码。

    - 调用者：平台管理员或平台员工，权限码 `personnel.role.create`
    - `supplier_id` 固定为空；未删除的平台角色名称不可重复
    - `permission_codes` 须落在当前账号可分配的权限目录内
    """
    role_service.assert_platform_actor(current_user)
    return success(
        role_service.create_role(
            db,
            actor=current_user,
            supplier_id=None,
            name=payload.name,
            remark=payload.remark,
            permission_codes=payload.permission_codes,
        )
    )


@router.post(
    "/update",
    response_model=ApiResponse[RolePublic],
    summary="[平台] 修改角色",
)
def update_role(
    payload: RoleUpdate,
    current_user: User = Depends(require_perm("personnel.role.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[RolePublic]:
    """
    修改平台角色的名称、备注、启用状态或权限码。

    - 调用者：平台管理员或平台员工，权限码 `personnel.role.update`
    - 只改 `supplier_id` 为空的角色
    - 传入 `permission_codes` 时整份替换，且须落在权限目录可分配范围内
    """
    role_service.assert_platform_actor(current_user)
    return success(
        role_service.update_role(
            db,
            actor=current_user,
            supplier_id=None,
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
    summary="[平台] 删除角色",
)
def delete_role(
    payload: RoleDelete,
    current_user: User = Depends(require_perm("personnel.role.delete")),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    """
    软删除平台角色，并解除员工、权限关联。

    - 调用者：平台管理员或平台员工，权限码 `personnel.role.delete`
    - 只删 `supplier_id` 为空的角色；删除后停用，并清掉该角色的用户绑定与权限
    """
    role_service.assert_platform_actor(current_user)
    role_service.delete_role(db, supplier_id=None, role_id=payload.id)
    return success({})


@router.post(
    "/options",
    response_model=ApiResponse[list[dict]],
    summary="[平台] 角色下拉",
)
def role_options(
    current_user: User = Depends(require_perm("personnel.staff")),
    db: Session = Depends(get_db),
) -> ApiResponse[list[dict]]:
    """
    返回启用中的平台角色，供员工表单选择。

    - 调用者：平台管理员或平台员工，权限码 `personnel.staff`
    - 只含 `supplier_id` 为空且未删除、已启用的角色
    """
    role_service.assert_platform_actor(current_user)
    return success(role_service.list_role_options(db, supplier_id=None))


@router.post(
    "/permission-tree",
    response_model=ApiResponse[list[PermissionTreeNode]],
    summary="[平台] 可分配权限树",
)
def permission_tree(
    current_user: User = Depends(require_perm("personnel.role")),
    db: Session = Depends(get_db),
) -> ApiResponse[list[PermissionTreeNode]]:
    """
    返回平台角色可勾选的权限树。

    - 调用者：平台管理员或平台员工，权限码 `personnel.role`
    - 数据来自权限目录，不按供应商开通池过滤
    """
    role_service.assert_platform_actor(current_user)
    return success(perm_service.platform_permission_tree(db))
