from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Pagination, require_admin_user, require_perm
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.supplier_staff import (
    SupplierStaffCreate,
    SupplierStaffDelete,
    SupplierStaffList,
    SupplierStaffStatusUpdate,
    SupplierStaffUpdate,
)
from app.schemas.user import UserPublic
from app.services import supplier_staff as staff_service

router = APIRouter(
    prefix="/supplier-staff",
    tags=["admin:staff"],
    dependencies=[Depends(require_admin_user)],
)


@router.post(
    "/list",
    response_model=ApiResponse[PageData[UserPublic]],
    summary="[供应商] 员工列表",
)
def list_staff(
    payload: SupplierStaffList,
    current_user: User = Depends(require_perm("personnel.staff")),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[UserPublic]]:
    """
    分页查询当前供应商的员工（身份 `supplier_staff`）。

    - 调用者：已绑定供应商的账号，权限码 `personnel.staff`
    - 只返回该账号 `supplier_id` 下的员工，可按账号、昵称、邮箱、手机号筛选
    - 不含平台员工；返回里带已挂的本供应商角色
    """
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        staff_service.list_staff(
            db,
            actor=current_user,
            keyword=payload.keyword,
            pagination=pagination,
        )
    )


@router.post(
    "/create",
    status_code=201,
    response_model=ApiResponse[UserPublic],
    summary="[供应商] 新建员工",
)
def create_staff(
    payload: SupplierStaffCreate,
    current_user: User = Depends(require_perm("personnel.staff.create")),
    db: Session = Depends(get_db),
) -> ApiResponse[UserPublic]:
    """
    为当前供应商新建员工，身份固定为 `supplier_staff`。

    - 调用者：已绑定供应商的账号，权限码 `personnel.staff.create`
    - 新账号挂在调用者的 `supplier_id` 上
    - `role_ids` 只能挂本供应商的角色；账号、邮箱、手机号全局不可重复
    """
    return success(
        staff_service.create_staff(
            db,
            actor=current_user,
            username=payload.username,
            password=payload.password,
            email=payload.email,
            nickname=payload.nickname,
            phone=payload.phone,
            role_ids=payload.role_ids,
        )
    )


@router.post(
    "/update",
    response_model=ApiResponse[UserPublic],
    summary="[供应商] 修改员工",
)
def update_staff(
    payload: SupplierStaffUpdate,
    current_user: User = Depends(require_perm("personnel.staff.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[UserPublic]:
    """
    修改本供应商员工的昵称、邮箱、手机号、密码或角色。

    - 调用者：已绑定供应商的账号，权限码 `personnel.staff.update`
    - 只能改本供应商、身份为 `supplier_staff` 的账号
    - 传入 `role_ids` 时整份替换，且只能是本供应商角色；改密码会踢掉该账号已有登录
    """
    return success(
        staff_service.update_staff(
            db,
            actor=current_user,
            staff_id=payload.id,
            nickname=payload.nickname,
            email=payload.email,
            phone=payload.phone,
            password=payload.password,
            role_ids=payload.role_ids,
        )
    )


@router.post(
    "/status",
    response_model=ApiResponse[UserPublic],
    summary="[供应商] 启用或停用员工",
)
def update_staff_status(
    payload: SupplierStaffStatusUpdate,
    current_user: User = Depends(require_perm("personnel.staff.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[UserPublic]:
    """
    启用或停用本供应商员工。

    - 调用者：已绑定供应商的账号，权限码 `personnel.staff.update`
    - 只能改本供应商、身份为 `supplier_staff` 的账号
    - 停用时踢掉该账号已有登录
    """
    return success(
        staff_service.set_staff_active(
            db,
            actor=current_user,
            staff_id=payload.id,
            is_active=payload.is_active,
        )
    )


@router.post(
    "/delete",
    response_model=ApiResponse[dict],
    summary="[供应商] 删除员工",
)
def delete_staff(
    payload: SupplierStaffDelete,
    current_user: User = Depends(require_perm("personnel.staff.delete")),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    """
    软删除本供应商员工并停用。

    - 调用者：已绑定供应商的账号，权限码 `personnel.staff.delete`
    - 只能删本供应商、身份为 `supplier_staff` 的账号，同时踢掉已有登录
    """
    staff_service.soft_delete_staff(
        db,
        actor=current_user,
        staff_id=payload.id,
    )
    return success({})
