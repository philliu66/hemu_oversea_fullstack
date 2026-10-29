from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Pagination, require_admin_user, require_perm
from app.core.errors import forbidden
from app.core.roles import Role
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.platform_staff import (
    PlatformStaffCreate,
    PlatformStaffDelete,
    PlatformStaffList,
    PlatformStaffStatusUpdate,
    PlatformStaffUpdate,
)
from app.schemas.user import UserPublic
from app.services import platform_staff as staff_service


def _assert_platform(actor: User) -> None:
    if actor.role not in {
        Role.PLATFORM_ADMIN.value,
        Role.PLATFORM_STAFF.value,
    }:
        raise forbidden()


router = APIRouter(
    prefix="/platform-staff",
    tags=["admin:staff"],
    dependencies=[Depends(require_admin_user)],
)


@router.post(
    "/list",
    response_model=ApiResponse[PageData[UserPublic]],
    summary="[平台] 员工列表",
)
def list_staff(
    payload: PlatformStaffList,
    current_user: User = Depends(require_perm("personnel.staff")),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[UserPublic]]:
    """
    分页查询平台员工（身份 `platform_staff`）。

    - 调用者：平台管理员或平台员工，权限码 `personnel.staff`
    - 可按账号、昵称、邮箱、手机号筛选
    - 不含供应商员工；返回里带已挂的平台角色
    """
    _assert_platform(current_user)
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        staff_service.list_staff(
            db, keyword=payload.keyword, pagination=pagination
        )
    )


@router.post(
    "/create",
    status_code=201,
    response_model=ApiResponse[UserPublic],
    summary="[平台] 新建员工",
)
def create_staff(
    payload: PlatformStaffCreate,
    current_user: User = Depends(require_perm("personnel.staff.create")),
    db: Session = Depends(get_db),
) -> ApiResponse[UserPublic]:
    """
    新建平台员工，身份固定为 `platform_staff`，不绑定供应商。

    - 调用者：平台管理员或平台员工，权限码 `personnel.staff.create`
    - `role_ids` 只能挂 `supplier_id` 为空的平台角色
    - 账号、邮箱、手机号全局不可重复
    """
    _assert_platform(current_user)
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
    summary="[平台] 修改员工",
)
def update_staff(
    payload: PlatformStaffUpdate,
    current_user: User = Depends(require_perm("personnel.staff.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[UserPublic]:
    """
    修改平台员工的昵称、邮箱、手机号、密码或角色。

    - 调用者：平台管理员或平台员工，权限码 `personnel.staff.update`
    - 只能改身份为 `platform_staff` 的账号
    - 传入 `role_ids` 时整份替换，且只能是平台角色；改密码会踢掉该账号已有登录
    """
    _assert_platform(current_user)
    return success(
        staff_service.update_staff(
            db,
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
    summary="[平台] 启用或停用员工",
)
def update_staff_status(
    payload: PlatformStaffStatusUpdate,
    current_user: User = Depends(require_perm("personnel.staff.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[UserPublic]:
    """
    启用或停用平台员工。

    - 调用者：平台管理员或平台员工，权限码 `personnel.staff.update`
    - 只能改身份为 `platform_staff` 的账号
    - 停用时踢掉该账号已有登录
    """
    _assert_platform(current_user)
    return success(
        staff_service.set_staff_active(
            db, staff_id=payload.id, is_active=payload.is_active
        )
    )


@router.post(
    "/delete",
    response_model=ApiResponse[dict],
    summary="[平台] 删除员工",
)
def delete_staff(
    payload: PlatformStaffDelete,
    current_user: User = Depends(require_perm("personnel.staff.delete")),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    """
    软删除平台员工并停用。

    - 调用者：平台管理员或平台员工，权限码 `personnel.staff.delete`
    - 只能删身份为 `platform_staff` 的账号，同时踢掉已有登录
    """
    _assert_platform(current_user)
    staff_service.soft_delete_staff(db, staff_id=payload.id)
    return success({})
