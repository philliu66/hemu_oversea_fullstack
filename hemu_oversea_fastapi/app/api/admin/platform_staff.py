from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Pagination, require_admin_user, require_perm
from app.core.errors import forbidden
from app.core.roles import Role, normalize_portal_role
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
    role = normalize_portal_role(actor.role) or actor.role
    if role not in {
        Role.PLATFORM_ADMIN.value,
        Role.PLATFORM_STAFF.value,
        Role.SUPER_ADMIN.value,
    }:
        raise forbidden()


router = APIRouter(
    prefix="/platform-staff",
    tags=["admin:platform-staff"],
    dependencies=[Depends(require_admin_user)],
)


@router.post("/list", response_model=ApiResponse[PageData[UserPublic]])
def list_staff(
    payload: PlatformStaffList,
    current_user: User = Depends(require_perm("personnel.staff")),
    db: Session = Depends(get_db),
) -> ApiResponse[PageData[UserPublic]]:
    _assert_platform(current_user)
    pagination = Pagination(page=payload.page, page_size=payload.page_size)
    return success(
        staff_service.list_staff(
            db, keyword=payload.keyword, pagination=pagination
        )
    )


@router.post("/create", status_code=201, response_model=ApiResponse[UserPublic])
def create_staff(
    payload: PlatformStaffCreate,
    current_user: User = Depends(require_perm("personnel.staff.create")),
    db: Session = Depends(get_db),
) -> ApiResponse[UserPublic]:
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


@router.post("/update", response_model=ApiResponse[UserPublic])
def update_staff(
    payload: PlatformStaffUpdate,
    current_user: User = Depends(require_perm("personnel.staff.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[UserPublic]:
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


@router.post("/status", response_model=ApiResponse[UserPublic])
def update_staff_status(
    payload: PlatformStaffStatusUpdate,
    current_user: User = Depends(require_perm("personnel.staff.update")),
    db: Session = Depends(get_db),
) -> ApiResponse[UserPublic]:
    _assert_platform(current_user)
    return success(
        staff_service.set_staff_active(
            db, staff_id=payload.id, is_active=payload.is_active
        )
    )


@router.post("/delete", response_model=ApiResponse[dict])
def delete_staff(
    payload: PlatformStaffDelete,
    current_user: User = Depends(require_perm("personnel.staff.delete")),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    _assert_platform(current_user)
    staff_service.soft_delete_staff(db, staff_id=payload.id)
    return success({})
