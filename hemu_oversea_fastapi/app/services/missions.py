import copy
import logging
import re
import threading
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import unquote

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased, defer

from app.core.db import SessionLocal
from app.core.deps import Pagination
from app.core.errors import AppError, bad_request, forbidden, not_found
from app.core.roles import Role
from app.models.mission import (
    FISSION_STATUS_FAILED,
    FISSION_STATUS_MARKED_FINISHED,
    FISSION_STATUS_PENDING,
    FISSION_STATUS_SUCCESS,
    FISSION_STATUSES,
    HOTSALE_STATUS_FAILED,
    HOTSALE_STATUS_MARKED_FINISHED,
    HOTSALE_STATUS_PENDING,
    HOTSALE_STATUS_SUCCESS,
    HOTSALE_STATUSES,
    MISSION_TYPE_FISSION_DH,
    MISSION_TYPE_HOTSALE_DH,
    MISSION_TYPES,
    MISSION_STATUS_FINISHED,
    MISSION_STATUS_MARKED_FINISHED,
    MISSION_STATUS_PENDING,
    MISSION_STATUS_RUNNING,
    Mission,
    MissionDataDhFission,
    MissionDataDhHotsale,
    MissionLog,
)
from app.models.product_dh import ProductDh
from app.models.store import Store
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.common import PageData
from app.schemas.mission import (
    MissionFissionDataDetailPublic,
    MissionFissionDataPublic,
    MissionHotsaleDataExtractFailItem,
    MissionHotsaleDataExtractResult,
    MissionHotsaleDataImportResult,
    MissionHotsaleDataPublic,
    MissionLogPublic,
    MissionPublic,
)
from app.services import operation_logs
from app.services import permissions as perm_service
from app.services.dhgate.product_page import fetch_product_page
from app.services.products import _build_dh_main_image_url
from app.services.supplier_scope import (
    SUPPLIER_PORTAL_ROLES as _SUPPLIER_PORTAL_ROLES,
    resolve_supplier_id,
)

PLACEHOLDER_MESSAGE = "功能待补充"
logger = logging.getLogger(__name__)

_MARKABLE_STATUSES = {MISSION_STATUS_PENDING, MISSION_STATUS_RUNNING}

# 任务类型 → 菜单/按钮权限码前缀
_MISSION_TYPE_PERM = {
    MISSION_TYPE_FISSION_DH: "mission.fission",
    MISSION_TYPE_HOTSALE_DH: "mission.hotsale",
}


def normalize_mission_type(mission_type: str) -> str:
    cleaned = (mission_type or "").strip()
    if cleaned not in MISSION_TYPES:
        raise bad_request(
            f"无效的任务类型：{mission_type}，允许：{', '.join(sorted(MISSION_TYPES))}"
        )
    return cleaned


def assert_mission_type_perm(
    db: Session,
    actor: User,
    mission_type: str,
    *,
    suffix: str = "",
) -> str:
    """校验当前用户是否拥有该任务类型对应权限（platform_admin 放行）。"""
    normalized = normalize_mission_type(mission_type)
    prefix = _MISSION_TYPE_PERM[normalized]
    code = f"{prefix}.{suffix}" if suffix else prefix
    if not perm_service.user_has_permissions(db, actor, code):
        raise forbidden("无操作权限")
    return normalized
_EXECUTABLE_FISSION_STATUSES = {FISSION_STATUS_PENDING, FISSION_STATUS_FAILED}
_EXECUTABLE_HOTSALE_STATUSES = {HOTSALE_STATUS_PENDING, HOTSALE_STATUS_FAILED}
_MOCK_BATCH_SECONDS = 10


def _scope_supplier_id(
    db: Session,
    actor: User,
    supplier_id: int | None,
) -> int:
    return resolve_supplier_id(db, actor, supplier_id)


def _visible_filters(
    db: Session,
    actor: User,
    supplier_id: int | None,
) -> list:
    filters = [
        Mission.deleted_at.is_(None),
        Mission.supplier_id == _scope_supplier_id(db, actor, supplier_id),
    ]
    if actor.role == Role.SUPPLIER_STAFF.value:
        filters.append(Mission.worker_id == actor.id)
    return filters


def _get_visible_mission(
    db: Session,
    *,
    mission_id: int,
    actor: User,
    supplier_id: int | None = None,
) -> Mission:
    """按任务 ID 读取并校验可见性。

    已有 mission_id 时可不传 supplier_id：从任务记录解析供应商后再做作用域校验。
    若显式传入 supplier_id，须与任务归属一致。
    """
    mission = db.get(Mission, mission_id)
    if mission is None or mission.is_deleted:
        raise not_found("任务不存在")

    scoped_supplier_id = resolve_supplier_id(
        db,
        actor,
        supplier_id if supplier_id is not None else mission.supplier_id,
    )
    if mission.supplier_id != scoped_supplier_id:
        raise forbidden("无权查看该任务")
    if actor.role == Role.SUPPLIER_STAFF.value and mission.worker_id != actor.id:
        raise forbidden("无权查看该任务")
    return mission


def _require_supplier_actor(
    db: Session,
    actor: User,
    supplier_id: int | None = None,
) -> int:
    """供应商账号或平台账号（需传 supplier_id）均可操作。"""
    return resolve_supplier_id(db, actor, supplier_id)


def _require_supplier_admin(actor: User) -> int:
    if actor.role != Role.SUPPLIER_ADMIN.value:
        raise forbidden("只有供应商管理员可以操作")
    if actor.supplier_id is None:
        raise bad_request("当前账号未绑定供应商")
    return actor.supplier_id


def _get_assignable_worker(db: Session, *, supplier_id: int, worker_id: int) -> User:
    user = db.get(User, worker_id)
    if user is None or user.is_deleted or not user.is_active:
        raise bad_request("指定人员不存在或已停用")
    if user.supplier_id != supplier_id or user.role not in _SUPPLIER_PORTAL_ROLES:
        raise bad_request("只能指定本供应商下的用户")
    return user


def _to_public(
    mission: Mission,
    *,
    worker: User | None,
    creator: User | None,
    supplier_name: str | None = None,
) -> MissionPublic:
    return MissionPublic(
        id=mission.id,
        supplier_id=mission.supplier_id,
        supplier_name=supplier_name,
        type=mission.type,  # type: ignore[arg-type]
        title=mission.title,
        description=mission.description,
        status=mission.status,
        worker_id=mission.worker_id,
        worker_username=worker.username if worker is not None else "",
        worker_nickname=worker.nickname if worker is not None else "",
        created_by=mission.created_by,
        creator_username=creator.username if creator is not None else None,
        creator_nickname=creator.nickname if creator is not None else None,
        created_at=mission.created_at,
        updated_at=mission.updated_at,
    )


def _load_users(db: Session, user_ids: set[int]) -> dict[int, User]:
    if not user_ids:
        return {}
    rows = db.scalars(select(User).where(User.id.in_(user_ids))).all()
    return {user.id: user for user in rows}


def _load_supplier_names(
    db: Session, supplier_ids: set[int]
) -> dict[int, str]:
    if not supplier_ids:
        return {}
    rows = db.scalars(
        select(Supplier).where(Supplier.id.in_(supplier_ids))
    ).all()
    return {row.id: row.name for row in rows}


def create_mission(
    db: Session,
    *,
    actor: User,
    title: str,
    description: str | None,
    worker_id: int,
    mission_type: str,
    supplier_id: int | None = None,
) -> MissionPublic:
    normalized_type = assert_mission_type_perm(
        db, actor, mission_type, suffix="create"
    )
    scoped_supplier_id = _require_supplier_actor(db, actor, supplier_id)
    cleaned_title = title.strip()
    if not cleaned_title:
        raise bad_request("请填写任务标题")
    worker = _get_assignable_worker(
        db, supplier_id=scoped_supplier_id, worker_id=worker_id
    )
    cleaned_description = description.strip() if description else ""
    mission = Mission(
        supplier_id=scoped_supplier_id,
        type=normalized_type,
        title=cleaned_title,
        description=cleaned_description or None,
        status=MISSION_STATUS_PENDING,
        worker_id=worker.id,
        created_by=actor.id,
    )
    db.add(mission)
    db.flush()
    operation_logs.record_operation(
        db,
        actor=actor,
        action=operation_logs.ACTION_MISSION_CREATE,
        resource_type="mission",
        resource_id=str(mission.id),
        summary=f"新建任务：{cleaned_title}",
        detail={
            "title": cleaned_title,
            "type": normalized_type,
            "worker_id": worker.id,
            "supplier_id": scoped_supplier_id,
        },
    )
    db.commit()
    db.refresh(mission)
    return _to_public(mission, worker=worker, creator=actor)


def list_missions(
    db: Session,
    *,
    actor: User,
    supplier_id: int | None,
    keyword: str | None,
    mission_type: str,
    pagination: Pagination,
) -> PageData[MissionPublic]:
    normalized_type = assert_mission_type_perm(db, actor, mission_type)
    filters = _visible_filters(db, actor, supplier_id)
    filters.append(Mission.type == normalized_type)
    if keyword and keyword.strip():
        filters.append(Mission.title.ilike(f"%{keyword.strip()}%"))

    total = db.scalar(select(func.count()).select_from(Mission).where(*filters)) or 0
    missions = db.scalars(
        select(Mission)
        .where(*filters)
        .order_by(Mission.id.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()
    user_ids = {mission.worker_id for mission in missions}
    user_ids.update(
        mission.created_by for mission in missions if mission.created_by is not None
    )
    users = _load_users(db, user_ids)
    supplier_names = _load_supplier_names(
        db, {mission.supplier_id for mission in missions}
    )
    return PageData(
        items=[
            _to_public(
                mission,
                worker=users.get(mission.worker_id),
                creator=users.get(mission.created_by) if mission.created_by else None,
                supplier_name=supplier_names.get(mission.supplier_id),
            )
            for mission in missions
        ],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def get_mission(
    db: Session,
    *,
    mission_id: int,
    actor: User,
    supplier_id: int | None,
) -> MissionPublic:
    mission = _get_visible_mission(
        db,
        mission_id=mission_id,
        actor=actor,
        supplier_id=supplier_id,
    )
    assert_mission_type_perm(db, actor, mission.type)
    # 热卖：进入详情/设置数据页时按未闭环数据同步任务状态
    if mission.type == MISSION_TYPE_HOTSALE_DH:
        if _sync_hotsale_mission_status(db, mission=mission):
            db.commit()
            db.refresh(mission)
    users = _load_users(
        db,
        {mission.worker_id, *([mission.created_by] if mission.created_by else [])},
    )
    supplier_names = _load_supplier_names(db, {mission.supplier_id})
    return _to_public(
        mission,
        worker=users.get(mission.worker_id),
        creator=users.get(mission.created_by) if mission.created_by else None,
        supplier_name=supplier_names.get(mission.supplier_id),
    )


def update_mission(
    db: Session,
    *,
    actor: User,
    mission_id: int,
    title: str,
    description: str | None,
    worker_id: int,
    supplier_id: int | None = None,
) -> MissionPublic:
    peek = db.get(Mission, mission_id)
    if peek is None or peek.is_deleted:
        raise not_found("任务不存在")
    assert_mission_type_perm(db, actor, peek.type, suffix="create")
    scoped_supplier_id = _require_supplier_actor(
        db, actor, supplier_id if supplier_id is not None else peek.supplier_id
    )
    mission = _get_visible_mission(
        db,
        mission_id=mission_id,
        actor=actor,
        supplier_id=scoped_supplier_id,
    )
    if mission.status not in _MARKABLE_STATUSES:
        raise bad_request("仅未开始或进行中的任务可编辑")
    cleaned_title = title.strip()
    if not cleaned_title:
        raise bad_request("请填写任务标题")
    worker = _get_assignable_worker(
        db, supplier_id=scoped_supplier_id, worker_id=worker_id
    )
    cleaned_description = description.strip() if description else ""
    mission.title = cleaned_title
    mission.description = cleaned_description or None
    mission.worker_id = worker.id
    db.commit()
    db.refresh(mission)
    users = _load_users(
        db,
        {mission.worker_id, *([mission.created_by] if mission.created_by else [])},
    )
    return _to_public(
        mission,
        worker=worker,
        creator=users.get(mission.created_by) if mission.created_by else None,
    )


def mark_mission_finished(
    db: Session,
    *,
    mission_id: int,
    actor: User,
    supplier_id: int | None = None,
) -> MissionPublic:
    peek = db.get(Mission, mission_id)
    if peek is None or peek.is_deleted:
        raise not_found("任务不存在")
    assert_mission_type_perm(db, actor, peek.type, suffix="finish")
    scoped_supplier_id = _require_supplier_actor(
        db, actor, supplier_id if supplier_id is not None else peek.supplier_id
    )
    mission = _get_visible_mission(
        db,
        mission_id=mission_id,
        actor=actor,
        supplier_id=scoped_supplier_id,
    )
    if mission.status not in _MARKABLE_STATUSES:
        raise bad_request("当前状态不能标记结束")
    mission.status = MISSION_STATUS_MARKED_FINISHED
    db.commit()
    db.refresh(mission)
    users = _load_users(
        db,
        {mission.worker_id, *([mission.created_by] if mission.created_by else [])},
    )
    return _to_public(
        mission,
        worker=users.get(mission.worker_id),
        creator=users.get(mission.created_by) if mission.created_by else None,
    )


def _to_fission_list_public(
    row: MissionDataDhFission,
    *,
    store_name: str | None,
    seed_item_code: str | None = None,
) -> MissionFissionDataPublic:
    data = MissionFissionDataPublic.model_validate(row)
    return data.model_copy(
        update={
            "store_name": store_name,
            "seed_item_code": seed_item_code,
            "main_image_url": _build_dh_main_image_url(row.main_image_url),
        }
    )


def _snapshot_store_id(
    db: Session,
    *,
    product: ProductDh,
    update_json: dict,
    supplier_id: int,
) -> int:
    if "store_id" not in update_json or update_json.get("store_id") in (None, ""):
        return product.store_id
    try:
        store_id = int(update_json["store_id"])
    except (TypeError, ValueError):
        raise bad_request("店铺无效") from None
    if store_id == product.store_id:
        return store_id
    store = db.get(Store, store_id)
    if store is None or store.is_deleted or store.supplier_id != supplier_id:
        raise forbidden("只能选择本供应商的店铺")
    return store_id


def _body_text(body: dict, key: str) -> str | None:
    value = body.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _body_main_image(body: dict) -> str | None:
    images = body.get("item_img_list")
    if not isinstance(images, list):
        return None
    for image in images:
        if not isinstance(image, dict):
            continue
        url = _body_text(image, "img_url")
        if url:
            return url
    return None


def _overlay_text(update_json: dict, key: str, current: str | None) -> str | None:
    if key not in update_json:
        return current
    value = update_json.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def list_fission_data(
    db: Session,
    *,
    mission_id: int,
    actor: User,
    supplier_id: int | None,
    pagination: Pagination,
    keyword: str | None = None,
    fission_status: str | None = None,
) -> PageData[MissionFissionDataPublic]:
    _get_visible_mission(
        db,
        mission_id=mission_id,
        actor=actor,
        supplier_id=supplier_id,
    )
    filters = [
        MissionDataDhFission.deleted_at.is_(None),
        MissionDataDhFission.mission_id == mission_id,
    ]

    kw = (keyword or "").strip()
    if kw:
        pattern = f"%{kw}%"
        filters.append(
            or_(
                MissionDataDhFission.item_name.ilike(pattern),
                MissionDataDhFission.item_code.ilike(pattern),
                ProductDh.item_code.ilike(pattern),
            )
        )

    status = (fission_status or "").strip()
    if status and status != "all":
        if status not in FISSION_STATUSES:
            raise bad_request(
                f"无效的裂变状态：{status}，允许：{', '.join(sorted(FISSION_STATUSES))}"
            )
        filters.append(MissionDataDhFission.fission_status == status)

    count_stmt = select(func.count()).select_from(MissionDataDhFission)
    if kw:
        count_stmt = count_stmt.outerjoin(
            ProductDh, ProductDh.id == MissionDataDhFission.seed_product_id
        )
    total = db.scalar(count_stmt.where(*filters)) or 0

    rows = db.execute(
        select(MissionDataDhFission, Store.name, ProductDh.item_code)
        .options(
            defer(MissionDataDhFission.seed_json),
            defer(MissionDataDhFission.raw_json),
        )
        .outerjoin(Store, Store.id == MissionDataDhFission.store_id)
        .outerjoin(ProductDh, ProductDh.id == MissionDataDhFission.seed_product_id)
        .where(*filters)
        .order_by(
            MissionDataDhFission.created_at.desc(),
            MissionDataDhFission.id.desc(),
        )
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()
    return PageData(
        items=[
            _to_fission_list_public(
                fission,
                store_name=store_name,
                seed_item_code=seed_item_code,
            )
            for fission, store_name, seed_item_code in rows
        ],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def list_logs(
    db: Session,
    *,
    mission_id: int,
    actor: User,
    supplier_id: int | None,
    pagination: Pagination,
) -> PageData[MissionLogPublic]:
    _get_visible_mission(
        db,
        mission_id=mission_id,
        actor=actor,
        supplier_id=supplier_id,
    )
    filters = [MissionLog.mission_id == mission_id]
    total = db.scalar(select(func.count()).select_from(MissionLog).where(*filters)) or 0
    operator = aliased(User)
    rows = db.execute(
        select(MissionLog, operator)
        .join(operator, MissionLog.operator_id == operator.id)
        .where(*filters)
        .order_by(MissionLog.started_at.desc(), MissionLog.id.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()
    return PageData(
        items=[
            MissionLogPublic(
                id=log.id,
                mission_id=log.mission_id,
                operator_id=log.operator_id,
                operator_username=user.username,
                operator_nickname=user.nickname,
                started_at=log.started_at,
                ended_at=log.ended_at,
                success_count=log.success_count,
                fail_count=log.fail_count,
                remark=log.remark,
                created_at=log.created_at,
            )
            for log, user in rows
        ],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def get_fission_data_detail(
    db: Session,
    *,
    actor: User,
    mission_id: int,
    data_id: int,
    supplier_id: int | None,
) -> MissionFissionDataDetailPublic:
    """读取一条裂变数据的改后正文和相对种子的差异。"""
    _get_visible_mission(
        db,
        mission_id=mission_id,
        actor=actor,
        supplier_id=supplier_id,
    )
    row = db.get(MissionDataDhFission, data_id)
    if row is None or row.is_deleted or row.mission_id != mission_id:
        raise not_found("任务数据不存在")
    return MissionFissionDataDetailPublic(
        id=row.id,
        mission_id=row.mission_id,
        supplier_id=row.supplier_id,
        seed_product_id=row.seed_product_id,
        fission_status=row.fission_status,
        update_json=row.update_json or {},
        raw_json=row.raw_json if isinstance(row.raw_json, dict) else None,
        seed_json=row.seed_json if isinstance(row.seed_json, dict) else None,
    )


def add_fission_data(
    db: Session,
    *,
    actor: User,
    mission_id: int,
    seed_product_id: int,
    update_json: dict,
    raw_json: dict,
    seed_json: dict | None = None,
) -> MissionFissionDataPublic:
    """加入任务。seed_json 冻结种子原文，raw_json 为改完后的正文，update_json 为二者差异。"""
    peek = db.get(Mission, mission_id)
    if peek is None or peek.is_deleted:
        raise not_found("任务不存在")
    supplier_id = _require_supplier_actor(db, actor, peek.supplier_id)
    mission = _get_visible_mission(
        db,
        mission_id=mission_id,
        actor=actor,
        supplier_id=supplier_id,
    )
    if mission.status == MISSION_STATUS_RUNNING:
        raise bad_request("任务正在执行中，不能再添加数据")
    if mission.status in {MISSION_STATUS_MARKED_FINISHED, MISSION_STATUS_FINISHED}:
        raise bad_request("任务已结束，不能再添加数据")

    product = db.get(ProductDh, seed_product_id)
    if product is None:
        raise not_found("种子商品不存在")
    if product.is_seed != "1":
        raise bad_request("只能选择种子商品")
    if product.supplier_id != supplier_id:
        raise forbidden("只能选择本供应商的种子商品")
    store = db.get(Store, product.store_id)
    if store is None or store.is_deleted or store.supplier_id != supplier_id:
        raise forbidden("只能选择本供应商的种子商品")

    if not isinstance(raw_json, dict) or not raw_json:
        raise bad_request("缺少修改后的商品正文")
    frozen_seed = (
        copy.deepcopy(seed_json)
        if isinstance(seed_json, dict) and seed_json
        else (
            copy.deepcopy(product.raw_json)
            if isinstance(product.raw_json, dict)
            else None
        )
    )
    row = MissionDataDhFission(
        mission_id=mission.id,
        supplier_id=mission.supplier_id,
        seed_product_id=product.id,
        store_id=_snapshot_store_id(
            db,
            product=product,
            update_json=update_json,
            supplier_id=supplier_id,
        ),
        item_code=None,
        site_id=_body_text(raw_json, "site_id") or product.site_id or "EN",
        cate_pub_id=_overlay_text(
            update_json,
            "cate_pub_id",
            _body_text(raw_json, "cate_pub_id") or product.cate_pub_id,
        ),
        item_name=_overlay_text(
            update_json,
            "item_name",
            _body_text(raw_json, "item_name") or product.item_name,
        ),
        main_image_url=_body_main_image(raw_json) or product.main_image_url,
        seed_json=frozen_seed,
        raw_json=raw_json,
        update_json=update_json,
        fission_status=FISSION_STATUS_PENDING,
        created_by=actor.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return MissionFissionDataPublic.model_validate(row)


def update_fission_data(
    db: Session,
    *,
    actor: User,
    mission_id: int,
    data_id: int,
    update_json: dict,
    raw_json: dict,
) -> MissionFissionDataPublic:
    """编辑任务数据。seed_json 不变，raw_json / update_json 按最初种子重算覆盖。"""
    row = _get_mutable_fission_row(
        db,
        actor=actor,
        mission_id=mission_id,
        data_id=data_id,
    )
    if row.fission_status == FISSION_STATUS_SUCCESS:
        raise bad_request("裂变成功的数据不能编辑")
    if not isinstance(raw_json, dict) or not raw_json:
        raise bad_request("缺少修改后的商品正文")

    product = db.get(ProductDh, row.seed_product_id)
    if product is None:
        raise not_found("种子商品不存在")

    supplier_id = row.supplier_id
    row.store_id = _snapshot_store_id(
        db,
        product=product,
        update_json=update_json,
        supplier_id=supplier_id,
    )
    row.site_id = _body_text(raw_json, "site_id") or row.site_id or "EN"
    row.cate_pub_id = _overlay_text(
        update_json,
        "cate_pub_id",
        _body_text(raw_json, "cate_pub_id") or row.cate_pub_id,
    )
    row.item_name = _overlay_text(
        update_json,
        "item_name",
        _body_text(raw_json, "item_name") or row.item_name,
    )
    row.main_image_url = _body_main_image(raw_json) or row.main_image_url
    row.raw_json = raw_json
    row.update_json = update_json if isinstance(update_json, dict) else {}
    db.commit()
    db.refresh(row)
    return MissionFissionDataPublic.model_validate(row)


def _get_mutable_fission_row(
    db: Session,
    *,
    actor: User,
    mission_id: int,
    data_id: int,
) -> MissionDataDhFission:
    peek = db.get(Mission, mission_id)
    if peek is None or peek.is_deleted:
        raise not_found("任务不存在")
    supplier_id = _require_supplier_actor(db, actor, peek.supplier_id)
    mission = _get_visible_mission(
        db,
        mission_id=mission_id,
        actor=actor,
        supplier_id=supplier_id,
    )
    if mission.status == MISSION_STATUS_RUNNING:
        raise bad_request("任务正在执行中，不能修改数据")
    if mission.status in {MISSION_STATUS_MARKED_FINISHED, MISSION_STATUS_FINISHED}:
        raise bad_request("任务已结束，不能再修改数据")
    row = db.get(MissionDataDhFission, data_id)
    if row is None or row.is_deleted or row.mission_id != mission.id:
        raise not_found("任务数据不存在")
    return row


def delete_fission_data(
    db: Session,
    *,
    actor: User,
    mission_id: int,
    data_ids: list[int],
) -> dict:
    """软删除尚未裂变成功的任务数据（支持单条或多条）。"""
    now = datetime.now(timezone.utc)
    for data_id in data_ids:
        row = _get_mutable_fission_row(
            db,
            actor=actor,
            mission_id=mission_id,
            data_id=data_id,
        )
        if row.fission_status == FISSION_STATUS_SUCCESS:
            raise bad_request(f"裂变成功的数据不能删除（id={data_id}）")
        row.deleted_at = now
    db.commit()
    return {"count": len(data_ids)}


def mark_fission_data_finished(
    db: Session,
    *,
    actor: User,
    mission_id: int,
    data_ids: list[int],
) -> list[MissionFissionDataPublic]:
    """把尚未裂变成功的任务数据标记结束（支持单条或多条）。"""
    results: list[MissionFissionDataPublic] = []
    dirty = False
    for data_id in data_ids:
        row = _get_mutable_fission_row(
            db,
            actor=actor,
            mission_id=mission_id,
            data_id=data_id,
        )
        if row.fission_status == FISSION_STATUS_SUCCESS:
            raise bad_request(f"裂变成功的数据不能标记结束（id={data_id}）")
        if row.fission_status != FISSION_STATUS_MARKED_FINISHED:
            row.fission_status = FISSION_STATUS_MARKED_FINISHED
            dirty = True
        results.append(MissionFissionDataPublic.model_validate(row))
    if dirty:
        db.commit()
        for i, data_id in enumerate(data_ids):
            row = db.get(MissionDataDhFission, data_id)
            if row is not None:
                db.refresh(row)
                results[i] = MissionFissionDataPublic.model_validate(row)
    return results


def reject_placeholder(
    db: Session,
    *,
    mission_id: int,
    actor: User,
    supplier_id: int | None,
) -> None:
    """占位接口：确认任务可见后返回待补充，不写库、不调敦煌。"""
    _get_visible_mission(
        db,
        mission_id=mission_id,
        actor=actor,
        supplier_id=supplier_id,
    )
    raise bad_request(PLACEHOLDER_MESSAGE)


def execute_mission(
    db: Session,
    *,
    mission_id: int,
    actor: User,
    supplier_id: int | None,
) -> dict:
    """受理裂变任务执行：同步落库后后台模拟跑批（约 10s 后任务标 finished，数据状态不变）。

    真实循环调用单次裂变的逻辑后续再替换 `_mock_finish_mission_batch`。
    """
    peek = db.get(Mission, mission_id)
    if peek is None or peek.is_deleted:
        raise not_found("任务不存在")
    scoped_supplier_id = _require_supplier_actor(
        db, actor, supplier_id if supplier_id is not None else peek.supplier_id
    )
    mission = _get_visible_mission(
        db,
        mission_id=mission_id,
        actor=actor,
        supplier_id=scoped_supplier_id,
    )
    if mission.status == MISSION_STATUS_RUNNING:
        raise bad_request("任务正在执行中")
    if mission.status == MISSION_STATUS_MARKED_FINISHED:
        raise bad_request("任务已标记结束，不能执行")

    fission_ids = list(
        db.scalars(
            select(MissionDataDhFission.id)
            .where(
                MissionDataDhFission.mission_id == mission.id,
                MissionDataDhFission.deleted_at.is_(None),
                MissionDataDhFission.fission_status.in_(_EXECUTABLE_FISSION_STATUSES),
            )
            .order_by(MissionDataDhFission.id.asc())
        ).all()
    )
    if not fission_ids:
        raise bad_request("没有可执行的任务数据")

    now = datetime.now(timezone.utc)
    mission.status = MISSION_STATUS_RUNNING
    log = MissionLog(
        mission_id=mission.id,
        operator_id=actor.id,
        started_at=now,
        success_count=0,
        fail_count=0,
        remark="模拟执行中（真实跑批待补充）",
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    thread = threading.Thread(
        target=_mock_finish_mission_batch,
        kwargs={
            "mission_id": mission.id,
            "log_id": log.id,
        },
        name=f"mission-fission-mock-{mission.id}",
        daemon=True,
    )
    thread.start()

    return {
        "mission_id": mission.id,
        "log_id": log.id,
        "queued_count": len(fission_ids),
    }


def _mock_finish_mission_batch(
    *,
    mission_id: int,
    log_id: int,
) -> None:
    """临时占位：等待后只把任务标为 finished，不改裂变数据状态。后续替换为真实跑批。"""
    time.sleep(_MOCK_BATCH_SECONDS)
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        mission = db.get(Mission, mission_id)
        log = db.get(MissionLog, log_id)
        if mission is None or log is None:
            return
        if mission.status != MISSION_STATUS_RUNNING:
            return

        log.ended_at = now
        log.remark = "模拟执行完成（真实跑批待补充）"
        mission.status = MISSION_STATUS_FINISHED
        db.commit()
    except Exception:
        logger.exception(
            "mock mission batch failed mission_id=%s log_id=%s",
            mission_id,
            log_id,
        )
        db.rollback()
        try:
            mission = db.get(Mission, mission_id)
            log = db.get(MissionLog, log_id)
            now = datetime.now(timezone.utc)
            if mission is not None and mission.status == MISSION_STATUS_RUNNING:
                mission.status = MISSION_STATUS_PENDING
            if log is not None and log.ended_at is None:
                log.ended_at = now
                log.remark = "模拟执行异常"
            db.commit()
        except Exception:
            logger.exception(
                "mock mission batch recovery failed mission_id=%s log_id=%s",
                mission_id,
                log_id,
            )
            db.rollback()
    finally:
        db.close()


_ITEM_CODE_FROM_URL = re.compile(r"/(\d+)(?:\.html)+", re.IGNORECASE)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_dh_url(value: Any) -> str | None:
    text = _optional_str(value)
    if not text:
        return None
    if text.startswith("//"):
        return f"https:{text}"
    return text


def _extract_item_code_from_product_url(product_url: str | None) -> str | None:
    if not product_url:
        return None
    matched = _ITEM_CODE_FROM_URL.search(unquote(product_url))
    return matched.group(1) if matched else None


def list_hotsale_data(
    db: Session,
    *,
    mission_id: int,
    actor: User,
    supplier_id: int | None,
    pagination: Pagination,
    keyword: str | None = None,
    collect_status: str | None = None,
) -> PageData[MissionHotsaleDataPublic]:
    mission = _get_visible_mission(
        db,
        mission_id=mission_id,
        actor=actor,
        supplier_id=supplier_id,
    )
    if mission.type != MISSION_TYPE_HOTSALE_DH:
        raise bad_request("该任务不是热卖采集类型")

    filters = [
        MissionDataDhHotsale.deleted_at.is_(None),
        MissionDataDhHotsale.mission_id == mission_id,
    ]

    kw = (keyword or "").strip()
    if kw:
        pattern = f"%{kw}%"
        filters.append(
            or_(
                MissionDataDhHotsale.product_name.ilike(pattern),
                MissionDataDhHotsale.product_name_short.ilike(pattern),
                MissionDataDhHotsale.item_code.ilike(pattern),
                MissionDataDhHotsale.store_name.ilike(pattern),
            )
        )

    status = (collect_status or "").strip()
    if status and status != "all":
        if status not in HOTSALE_STATUSES:
            raise bad_request(
                f"无效的采集状态：{status}，允许：{', '.join(sorted(HOTSALE_STATUSES))}"
            )
        filters.append(MissionDataDhHotsale.collect_status == status)

    total = (
        db.scalar(
            select(func.count()).select_from(MissionDataDhHotsale).where(*filters)
        )
        or 0
    )
    rows = db.scalars(
        select(MissionDataDhHotsale)
        .options(defer(MissionDataDhHotsale.parse_raw_json))
        .where(*filters)
        .order_by(
            MissionDataDhHotsale.rank_no.asc().nullslast(),
            MissionDataDhHotsale.id.asc(),
        )
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()
    return PageData(
        items=[MissionHotsaleDataPublic.model_validate(row) for row in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def import_hotsale_capture(
    db: Session,
    *,
    actor: User,
    mission_id: int,
    payload: dict[str, Any],
    supplier_id: int | None = None,
) -> MissionHotsaleDataImportResult:
    """将扩展回传的热卖榜响应解析入库；新行默认 collect_status=pending。"""
    mission = _get_visible_mission(
        db,
        mission_id=mission_id,
        actor=actor,
        supplier_id=supplier_id,
    )
    if mission.type != MISSION_TYPE_HOTSALE_DH:
        raise bad_request("该任务不是热卖采集类型")
    assert_mission_type_perm(db, actor, MISSION_TYPE_HOTSALE_DH, suffix="data")

    if not isinstance(payload, dict):
        raise bad_request("采集数据格式无效")

    # currentCategory 仅作回传提示，不写入 cate_name（类目由详情提取填充）
    list_cate_tip = _optional_str(payload.get("currentCategory"))
    page_info = payload.get("pageInfoOfProductRank")
    if not isinstance(page_info, dict):
        raise bad_request("采集数据缺少 pageInfoOfProductRank")
    result_list = page_info.get("result")
    if not isinstance(result_list, list) or not result_list:
        raise bad_request("采集数据 result 为空")

    created = 0
    updated = 0
    for raw in result_list:
        if not isinstance(raw, dict):
            continue
        product_url = _normalize_dh_url(raw.get("productUrl"))
        item_code = _extract_item_code_from_product_url(product_url)
        product_name_short = _optional_str(raw.get("productName"))
        main_image_url = _normalize_dh_url(raw.get("imageUrl"))
        deal = _optional_str(raw.get("deal"))
        deal_amount = _optional_str(raw.get("dealAmount"))
        deal_persons = _optional_str(raw.get("dealPersons"))
        rank_raw = raw.get("rankNo")
        rank_no: int | None
        try:
            rank_no = int(rank_raw) if rank_raw is not None else None
        except (TypeError, ValueError):
            rank_no = None

        existing: MissionDataDhHotsale | None = None
        if item_code:
            existing = db.scalars(
                select(MissionDataDhHotsale).where(
                    MissionDataDhHotsale.deleted_at.is_(None),
                    MissionDataDhHotsale.mission_id == mission_id,
                    MissionDataDhHotsale.item_code == item_code,
                )
            ).first()

        if existing is not None:
            existing.product_url = product_url
            existing.product_name_short = product_name_short
            # product_name / cate_* / 店铺价格等留给详情提取，导入时不覆盖
            existing.main_image_url = main_image_url
            existing.deal = deal
            existing.deal_amount = deal_amount
            existing.deal_persons = deal_persons
            existing.rank_no = rank_no
            existing.updated_by = actor.id
            updated += 1
        else:
            db.add(
                MissionDataDhHotsale(
                    mission_id=mission.id,
                    supplier_id=mission.supplier_id,
                    item_code=item_code,
                    product_url=product_url,
                    product_name_short=product_name_short,
                    product_name=None,
                    main_image_url=main_image_url,
                    cate_name=None,
                    deal=deal,
                    deal_amount=deal_amount,
                    deal_persons=deal_persons,
                    collect_status=HOTSALE_STATUS_PENDING,
                    rank_no=rank_no,
                    created_by=actor.id,
                    updated_by=actor.id,
                )
            )
            created += 1

    # 按未闭环数据同步任务状态（有新增 pending 时通常会变为 running）
    _sync_hotsale_mission_status(db, mission=mission)

    db.commit()
    return MissionHotsaleDataImportResult(
        created=created,
        updated=updated,
        total=created + updated,
        cate_name=list_cate_tip,
        mission_status=mission.status,
    )


def _parse_sales_num_from_display(value: Any) -> int | None:
    """将销量展示文案（如 '142' / '1,234'）转为 int。"""
    text = _optional_str(value)
    if not text:
        return None
    cleaned = text.replace(",", "").replace(" ", "")
    matched = re.match(r"^(\d+)", cleaned)
    if matched:
        try:
            return int(matched.group(1))
        except ValueError:
            return None
    try:
        return int(Decimal(cleaned))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _parse_price_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _parse_store_id(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _apply_hotsale_parsed_fields(
    row: MissionDataDhHotsale,
    parsed: dict[str, Any],
) -> None:
    """把商品详情解析结果写入行内业务字段，并保存完整 parsed JSON。"""
    row.parse_raw_json = parsed

    title = _optional_str(parsed.get("title"))
    if title:
        row.product_name = title[:512]

    item_code = _optional_str(parsed.get("item_code"))
    if item_code and not row.item_code:
        row.item_code = item_code[:64]

    category = parsed.get("category")
    if isinstance(category, dict):
        cate_name = _optional_str(category.get("name"))
        if cate_name:
            row.cate_name = cate_name[:128]
        cate_id = _optional_str(category.get("id")) or _optional_str(
            category.get("pub_id")
        )
        if cate_id:
            row.cate_id = cate_id[:64]

    shop = parsed.get("shop")
    if isinstance(shop, dict):
        store_name = _optional_str(shop.get("name"))
        if store_name:
            row.store_name = store_name[:256]
        store_id = _parse_store_id(shop.get("seq"))
        if store_id is not None:
            row.store_id = store_id

    price_block = parsed.get("price")
    if isinstance(price_block, dict):
        price = _parse_price_decimal(price_block.get("single_price"))
        if price is not None:
            row.price = price

    sales = parsed.get("sales")
    if isinstance(sales, dict):
        sales_num = _parse_sales_num_from_display(sales.get("display"))
        if sales_num is not None:
            row.sales_num = sales_num

    last_modify = _optional_str(parsed.get("last_modify_date"))
    if last_modify:
        row.last_modify_date = last_modify[:64]


def _get_mutable_hotsale_row(
    db: Session,
    *,
    actor: User,
    mission_id: int,
    data_id: int,
) -> MissionDataDhHotsale:
    peek = db.get(Mission, mission_id)
    if peek is None or peek.is_deleted:
        raise not_found("任务不存在")
    supplier_id = _require_supplier_actor(db, actor, peek.supplier_id)
    mission = _get_visible_mission(
        db,
        mission_id=mission_id,
        actor=actor,
        supplier_id=supplier_id,
    )
    if mission.type != MISSION_TYPE_HOTSALE_DH:
        raise bad_request("该任务不是热卖采集类型")
    # 热卖 running=进行中（可继续采集/提取）；仅结束态不可改数据
    if mission.status in {MISSION_STATUS_MARKED_FINISHED, MISSION_STATUS_FINISHED}:
        raise bad_request("任务已结束，不能再修改数据")
    row = db.get(MissionDataDhHotsale, data_id)
    if row is None or row.is_deleted or row.mission_id != mission.id:
        raise not_found("任务数据不存在")
    return row


def delete_hotsale_data(
    db: Session,
    *,
    actor: User,
    mission_id: int,
    data_ids: list[int],
) -> dict:
    """软删除尚未采集完成的热卖任务数据（支持单条或多条）。"""
    now = datetime.now(timezone.utc)
    for data_id in data_ids:
        row = _get_mutable_hotsale_row(
            db,
            actor=actor,
            mission_id=mission_id,
            data_id=data_id,
        )
        if row.collect_status == HOTSALE_STATUS_SUCCESS:
            raise bad_request(f"已完成的数据不能删除（id={data_id}）")
        row.deleted_at = now
        row.updated_by = actor.id
    db.commit()
    return {"count": len(data_ids)}


def mark_hotsale_data_finished(
    db: Session,
    *,
    actor: User,
    mission_id: int,
    data_ids: list[int],
) -> list[MissionHotsaleDataPublic]:
    """把尚未采集完成的任务数据标记结束（支持单条或多条）。"""
    results: list[MissionHotsaleDataPublic] = []
    dirty = False
    for data_id in data_ids:
        row = _get_mutable_hotsale_row(
            db,
            actor=actor,
            mission_id=mission_id,
            data_id=data_id,
        )
        if row.collect_status == HOTSALE_STATUS_SUCCESS:
            raise bad_request(f"已完成的数据不能标记结束（id={data_id}）")
        if row.collect_status != HOTSALE_STATUS_MARKED_FINISHED:
            row.collect_status = HOTSALE_STATUS_MARKED_FINISHED
            row.updated_by = actor.id
            dirty = True
        results.append(MissionHotsaleDataPublic.model_validate(row))
    if dirty:
        db.commit()
        for i, data_id in enumerate(data_ids):
            row = db.get(MissionDataDhHotsale, data_id)
            if row is not None:
                db.refresh(row)
                results[i] = MissionHotsaleDataPublic.model_validate(row)
    return results


def _assert_hotsale_mission_writable(mission: Mission) -> None:
    """热卖提取前置校验：仅校验任务类型。

    任务已完成 / 标记结束后仍允许对 pending / failed 数据手动再提取，
    以便失败商品可重试；不再因任务结束态拦截提取。
    """
    if mission.type != MISSION_TYPE_HOTSALE_DH:
        raise bad_request("该任务不是热卖采集类型")


def _hotsale_open_work_left(db: Session, *, mission_id: int) -> int:
    """未闭环条数：pending（待提取）+ failed（可重试失败）。"""
    return (
        db.scalar(
            select(func.count())
            .select_from(MissionDataDhHotsale)
            .where(
                MissionDataDhHotsale.deleted_at.is_(None),
                MissionDataDhHotsale.mission_id == mission_id,
                MissionDataDhHotsale.collect_status.in_(
                    _EXECUTABLE_HOTSALE_STATUSES
                ),
            )
        )
        or 0
    )


def _sync_hotsale_mission_status(db: Session, *, mission: Mission) -> bool:
    """按未闭环数据同步热卖任务状态。返回是否发生变更。

    - 人工 ``marked_finished``：不自动改
    - 存在 pending/failed → ``running``
    - 否则 → ``finished``

    注意：工程 Session 为 autoflush=False，COUNT 前必须 flush。
    """
    if mission.status == MISSION_STATUS_MARKED_FINISHED:
        return False
    db.flush()
    desired = (
        MISSION_STATUS_RUNNING
        if _hotsale_open_work_left(db, mission_id=mission.id) > 0
        else MISSION_STATUS_FINISHED
    )
    if mission.status == desired:
        return False
    mission.status = desired
    return True


def _mark_hotsale_extract_failed(
    row: MissionDataDhHotsale,
    *,
    reason: str,
    actor_id: int | None,
) -> None:
    """提取失败：写 failed + collect_msg。"""
    row.collect_status = HOTSALE_STATUS_FAILED
    row.collect_msg = (reason or "").strip() or "提取失败"
    row.updated_by = actor_id


def extract_hotsale_product_pages(
    db: Session,
    *,
    actor: User,
    mission_id: int | None = None,
    mission_data_ids: list[int] | None = None,
    supplier_id: int | None = None,
) -> MissionHotsaleDataExtractResult:
    """按任务数据 ID 或任务 ID 拉取商品详情页并入库。

    - mission_data_ids：指定数据（须为 pending / failed）
    - mission_id：该任务下全部 pending / failed（跳过已完成 / 标记结束）
    成功时写入 parse_raw_json，collect_status=success 并清空 collect_msg。
    失败时 collect_status=failed，collect_msg 写入原因。
    结束后按未闭环（pending/failed）同步任务 running/finished（人工标记结束除外）。
    """
    assert_mission_type_perm(db, actor, MISSION_TYPE_HOTSALE_DH, suffix="data")

    by_mission = mission_id is not None
    fails: list[MissionHotsaleDataExtractFailItem] = []
    success_count = 0
    skipped_count = 0
    dirty = False
    target_mission: Mission | None = None
    rows: list[MissionDataDhHotsale] = []

    if by_mission:
        peek = db.get(Mission, mission_id)
        if peek is None or peek.is_deleted:
            raise not_found("任务不存在")
        scoped = _require_supplier_actor(
            db,
            actor,
            supplier_id if supplier_id is not None else peek.supplier_id,
        )
        target_mission = _get_visible_mission(
            db,
            mission_id=mission_id,  # type: ignore[arg-type]
            actor=actor,
            supplier_id=scoped,
        )
        _assert_hotsale_mission_writable(target_mission)
        rows = list(
            db.scalars(
                select(MissionDataDhHotsale)
                .where(
                    MissionDataDhHotsale.deleted_at.is_(None),
                    MissionDataDhHotsale.mission_id == target_mission.id,
                    MissionDataDhHotsale.collect_status.in_(
                        _EXECUTABLE_HOTSALE_STATUSES
                    ),
                )
                .order_by(
                    MissionDataDhHotsale.rank_no.asc().nullslast(),
                    MissionDataDhHotsale.id.asc(),
                )
            ).all()
        )
    else:
        ids = list(mission_data_ids or [])
        if not ids:
            raise bad_request("请至少选择一条任务数据")
        loaded: list[MissionDataDhHotsale] = []
        for data_id in ids:
            row = db.get(MissionDataDhHotsale, data_id)
            if row is None or row.is_deleted:
                fails.append(
                    MissionHotsaleDataExtractFailItem(
                        id=data_id,
                        product_url=None,
                        reason="任务数据不存在",
                    )
                )
                continue
            loaded.append(row)
        if not loaded and fails:
            return MissionHotsaleDataExtractResult(
                success_count=0,
                fail_count=len(fails),
                skipped_count=0,
                fails=fails,
                mission_id=None,
                mission_finished=False,
            )

        mission_ids = {r.mission_id for r in loaded}
        if len(mission_ids) > 1:
            raise bad_request("一次只能提取同一任务下的数据")
        mid = next(iter(mission_ids))
        peek = db.get(Mission, mid)
        if peek is None or peek.is_deleted:
            raise not_found("任务不存在")
        scoped = _require_supplier_actor(
            db,
            actor,
            supplier_id if supplier_id is not None else peek.supplier_id,
        )
        target_mission = _get_visible_mission(
            db,
            mission_id=mid,
            actor=actor,
            supplier_id=scoped,
        )
        _assert_hotsale_mission_writable(target_mission)

        for row in loaded:
            if row.collect_status == HOTSALE_STATUS_SUCCESS:
                fails.append(
                    MissionHotsaleDataExtractFailItem(
                        id=row.id,
                        product_url=row.product_url,
                        reason="已完成，不能重复提取",
                    )
                )
                continue
            if row.collect_status == HOTSALE_STATUS_MARKED_FINISHED:
                fails.append(
                    MissionHotsaleDataExtractFailItem(
                        id=row.id,
                        product_url=row.product_url,
                        reason="已标记结束，不能提取",
                    )
                )
                continue
            if row.collect_status not in _EXECUTABLE_HOTSALE_STATUSES:
                fails.append(
                    MissionHotsaleDataExtractFailItem(
                        id=row.id,
                        product_url=row.product_url,
                        reason=f"状态不可提取：{row.collect_status}",
                    )
                )
                continue
            rows.append(row)

    if by_mission and not rows:
        # 无可提取数据：仍按未闭环同步任务状态
        assert target_mission is not None
        status_changed = _sync_hotsale_mission_status(db, mission=target_mission)
        if status_changed:
            db.commit()
        return MissionHotsaleDataExtractResult(
            success_count=0,
            fail_count=0,
            skipped_count=0,
            fails=[],
            mission_id=target_mission.id,
            mission_finished=target_mission.status == MISSION_STATUS_FINISHED,
            mission_status=target_mission.status,
        )

    for row in rows:
        url = (row.product_url or "").strip()
        if not url:
            reason = "缺少商品链接"
            _mark_hotsale_extract_failed(row, reason=reason, actor_id=actor.id)
            dirty = True
            fails.append(
                MissionHotsaleDataExtractFailItem(
                    id=row.id,
                    product_url=row.product_url,
                    reason=reason,
                )
            )
            continue
        try:
            result = fetch_product_page(url)
        except AppError as exc:
            reason = exc.message or "请求失败"
            _mark_hotsale_extract_failed(row, reason=reason, actor_id=actor.id)
            dirty = True
            fails.append(
                MissionHotsaleDataExtractFailItem(
                    id=row.id,
                    product_url=url,
                    reason=reason,
                )
            )
            continue
        except Exception as exc:
            reason = f"请求异常：{exc}"
            _mark_hotsale_extract_failed(row, reason=reason, actor_id=actor.id)
            dirty = True
            fails.append(
                MissionHotsaleDataExtractFailItem(
                    id=row.id,
                    product_url=url,
                    reason=reason,
                )
            )
            continue

        if not result.get("ok") or not isinstance(result.get("parsed"), dict):
            reason = str(result.get("message") or result.get("reason") or "解析失败")
            _mark_hotsale_extract_failed(row, reason=reason, actor_id=actor.id)
            dirty = True
            fails.append(
                MissionHotsaleDataExtractFailItem(
                    id=row.id,
                    product_url=url,
                    reason=reason,
                )
            )
            continue

        parsed: dict[str, Any] = result["parsed"]
        _apply_hotsale_parsed_fields(row, parsed)
        row.collect_status = HOTSALE_STATUS_SUCCESS
        row.collect_msg = None
        row.updated_by = actor.id
        dirty = True
        success_count += 1

    # 有数据变更或按任务提取：按未闭环同步任务状态
    status_changed = False
    if target_mission is not None and (by_mission or dirty):
        status_changed = _sync_hotsale_mission_status(db, mission=target_mission)

    if dirty or status_changed:
        db.commit()

    assert target_mission is not None
    return MissionHotsaleDataExtractResult(
        success_count=success_count,
        fail_count=len(fails),
        skipped_count=skipped_count,
        fails=fails,
        mission_id=target_mission.id,
        mission_finished=target_mission.status == MISSION_STATUS_FINISHED,
        mission_status=target_mission.status,
    )
