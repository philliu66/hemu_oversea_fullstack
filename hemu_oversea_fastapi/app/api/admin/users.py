from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import (
    Pagination,
    get_current_admin_user,
    get_pagination,
    require_admin_user,
    require_super_admin,
)
from app.core.roles import Role
from app.models.user import User
from app.schemas.common import ApiResponse, PageData, success
from app.schemas.user import (
    AdminPasswordReset,
    AdminUserCreate,
    SupplierUserOption,
    UserPublic,
    UserRoleUpdate,
    UserStatusUpdate,
)
from app.services import users as user_service

router = APIRouter(
    prefix="/users",
    tags=["admin:users"],
    dependencies=[Depends(require_admin_user)],
)


@router.get("/me", response_model=ApiResponse[UserPublic])
def read_me(
    current_user: User = Depends(get_current_admin_user),
) -> ApiResponse[UserPublic]:
    """获取当前登录的管理端用户信息（刷新页面后可据此恢复前端状态）。"""
    return success(UserPublic.model_validate(current_user))


@router.get(
    "/supplier-list",
    response_model=ApiResponse[list[SupplierUserOption]],
)
def list_supplier_users(
    keyword: str | None = Query(default=None, description="按用户名或昵称模糊搜索"),
    supplier_id: int | None = Query(
        default=None,
        description="供应商 ID。供应商身份忽略该字段；平台身份必填",
    ),
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[list[SupplierUserOption]]:
    """获取供应商下的在职管理员和员工，供任务人员下拉选择。"""
    return success(
        user_service.list_supplier_users(
            db,
            actor=current_user,
            keyword=keyword,
            supplier_id=supplier_id,
        )
    )


@router.get("", response_model=ApiResponse[PageData[UserPublic]])
def list_users(
    keyword: str | None = Query(default=None, description="按用户名或邮箱模糊搜索"),
    role: Role | None = Query(default=None, description="按角色筛选"),
    pagination: Pagination = Depends(get_pagination),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[UserPublic]]:
    return success(
        user_service.list_users(db, keyword=keyword, role=role, pagination=pagination)
    )


@router.post("", status_code=201, response_model=ApiResponse[UserPublic])
def create_user(
    payload: AdminUserCreate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[UserPublic]:
    user = user_service.create_user(
        db,
        username=payload.username,
        email=payload.email,
        password=payload.password,
        nickname=payload.nickname,
        phone=payload.phone,
        avatar_url=payload.avatar_url,
        role=payload.role.value,
        org_type=payload.org_type.value,
        supplier_id=payload.supplier_id,
        created_by=current_user.id,
        is_active=payload.is_active,
    )
    return success(UserPublic.model_validate(user))


@router.patch("/{user_id}/status", response_model=ApiResponse[UserPublic])
def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> ApiResponse[UserPublic]:
    user = user_service.set_user_active(
        db,
        user_id=user_id,
        is_active=payload.is_active,
        actor=current_user,
    )
    return success(UserPublic.model_validate(user))


@router.patch("/{user_id}/role", response_model=ApiResponse[UserPublic])
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[UserPublic]:
    user = user_service.set_user_role(
        db,
        user_id=user_id,
        role=payload.role,
        org_type=payload.org_type.value if payload.org_type is not None else None,
        supplier_id=payload.supplier_id,
        actor=current_user,
    )
    return success(UserPublic.model_validate(user))


@router.post("/{user_id}/password", response_model=ApiResponse[dict])
def reset_user_password(
    user_id: int,
    payload: AdminPasswordReset,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    user_service.reset_user_password(
        db,
        user_id=user_id,
        new_password=payload.new_password,
        actor=current_user,
    )
    return success({})


@router.delete("/{user_id}", response_model=ApiResponse[dict])
def delete_user(
    user_id: int,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    user_service.soft_delete_user(db, user_id=user_id, actor=current_user)
    return success({})
