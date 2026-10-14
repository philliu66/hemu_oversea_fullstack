import copy
import logging
import threading
import time
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased, defer

from app.core.db import SessionLocal
from app.core.deps import Pagination
from app.core.errors import bad_request, forbidden, not_found
from app.core.roles import Role
from app.models.mission import (
    FISSION_STATUS_FAILED,
    FISSION_STATUS_MARKED_FINISHED,
    FISSION_STATUS_PENDING,
    FISSION_STATUS_SUCCESS,
    MISSION_STATUS_FINISHED,
    MISSION_STATUS_MARKED_FINISHED,
    MISSION_STATUS_PENDING,
    MISSION_STATUS_RUNNING,
    Mission,
    MissionDataDhFission,
    MissionLog,
)
from app.models.product_dh import ProductDh
from app.models.store import Store
from app.models.user import User
from app.schemas.common import PageData
from app.schemas.mission import (
    MissionFissionDataDetailPublic,
    MissionFissionDataPublic,
    MissionLogPublic,
    MissionPublic,
)
from app.services.products import _build_dh_main_image_url

PLACEHOLDER_MESSAGE = "功能待补充"
logger = logging.getLogger(__name__)

_PLATFORM_ROLES = {Role.PLATFORM_ADMIN.value, Role.SUPER_ADMIN.value, Role.PLATFORM_STAFF.value}
_SUPPLIER_PORTAL_ROLES = {Role.SUPPLIER_ADMIN.value, Role.SUPPLIER_STAFF.value}
_MARKABLE_STATUSES = {MISSION_STATUS_PENDING, MISSION_STATUS_RUNNING}
_EXECUTABLE_FISSION_STATUSES = {FISSION_STATUS_PENDING, FISSION_STATUS_FAILED}
_MOCK_BATCH_SECONDS = 10


def _scope_supplier_id(actor: User, supplier_id: int | None) -> int:
    if actor.role in _SUPPLIER_PORTAL_ROLES:
        if actor.supplier_id is None:
            raise bad_request("当前账号未绑定供应商")
        return actor.supplier_id
    if actor.role in _PLATFORM_ROLES:
        if supplier_id is None:
            raise bad_request("请指定供应商")
        return supplier_id
    raise forbidden()


def _visible_filters(actor: User, supplier_id: int | None) -> list:
    filters = [
        Mission.deleted_at.is_(None),
        Mission.supplier_id == _scope_supplier_id(actor, supplier_id),
    ]
    if actor.role == Role.SUPPLIER_STAFF.value:
        filters.append(Mission.worker_id == actor.id)
    return filters


def _get_visible_mission(
    db: Session,
    *,
    mission_id: int,
    actor: User,
    supplier_id: int | None,
) -> Mission:
    mission = db.scalar(
        select(Mission).where(
            Mission.id == mission_id,
            *_visible_filters(actor, supplier_id),
        )
    )
    if mission is not None:
        return mission
    existing = db.get(Mission, mission_id)
    if existing is None or existing.is_deleted:
        raise not_found("任务不存在")
    raise forbidden("无权查看该任务")


def _require_supplier_actor(actor: User) -> int:
    if actor.role not in _SUPPLIER_PORTAL_ROLES:
        raise forbidden("只有供应商账号可以操作")
    if actor.supplier_id is None:
        raise bad_request("当前账号未绑定供应商")
    return actor.supplier_id


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
) -> MissionPublic:
    return MissionPublic(
        id=mission.id,
        supplier_id=mission.supplier_id,
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


def create_mission(
    db: Session,
    *,
    actor: User,
    title: str,
    description: str | None,
    worker_id: int,
) -> MissionPublic:
    supplier_id = _require_supplier_actor(actor)
    cleaned_title = title.strip()
    if not cleaned_title:
        raise bad_request("请填写任务标题")
    worker = _get_assignable_worker(db, supplier_id=supplier_id, worker_id=worker_id)
    cleaned_description = description.strip() if description else ""
    mission = Mission(
        supplier_id=supplier_id,
        title=cleaned_title,
        description=cleaned_description or None,
        status=MISSION_STATUS_PENDING,
        worker_id=worker.id,
        created_by=actor.id,
    )
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return _to_public(mission, worker=worker, creator=actor)


def list_missions(
    db: Session,
    *,
    actor: User,
    supplier_id: int | None,
    keyword: str | None,
    pagination: Pagination,
) -> PageData[MissionPublic]:
    filters = _visible_filters(actor, supplier_id)
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
    return PageData(
        items=[
            _to_public(
                mission,
                worker=users.get(mission.worker_id),
                creator=users.get(mission.created_by) if mission.created_by else None,
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
    users = _load_users(
        db,
        {mission.worker_id, *([mission.created_by] if mission.created_by else [])},
    )
    return _to_public(
        mission,
        worker=users.get(mission.worker_id),
        creator=users.get(mission.created_by) if mission.created_by else None,
    )


def update_mission(
    db: Session,
    *,
    actor: User,
    mission_id: int,
    title: str,
    description: str | None,
    worker_id: int,
) -> MissionPublic:
    supplier_id = _require_supplier_actor(actor)
    mission = _get_visible_mission(
        db,
        mission_id=mission_id,
        actor=actor,
        supplier_id=supplier_id,
    )
    if mission.status not in _MARKABLE_STATUSES:
        raise bad_request("仅未开始或进行中的任务可编辑")
    cleaned_title = title.strip()
    if not cleaned_title:
        raise bad_request("请填写任务标题")
    worker = _get_assignable_worker(db, supplier_id=supplier_id, worker_id=worker_id)
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
) -> MissionPublic:
    supplier_id = _require_supplier_actor(actor)
    mission = _get_visible_mission(
        db,
        mission_id=mission_id,
        actor=actor,
        supplier_id=supplier_id,
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
    total = (
        db.scalar(
            select(func.count()).select_from(MissionDataDhFission).where(*filters)
        )
        or 0
    )
    rows = db.execute(
        select(MissionDataDhFission, Store.name, ProductDh.item_code)
        .options(
            defer(MissionDataDhFission.seed_json),
            defer(MissionDataDhFission.raw_json),
        )
        .outerjoin(Store, Store.id == MissionDataDhFission.store_id)
        .outerjoin(ProductDh, ProductDh.id == MissionDataDhFission.seed_product_id)
        .where(*filters)
        .order_by(MissionDataDhFission.id.desc())
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
    supplier_id = _require_supplier_actor(actor)
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
    supplier_id = _require_supplier_actor(actor)
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
    data_id: int,
) -> None:
    """软删除一条尚未裂变成功的任务数据。"""
    row = _get_mutable_fission_row(
        db,
        actor=actor,
        mission_id=mission_id,
        data_id=data_id,
    )
    if row.fission_status == FISSION_STATUS_SUCCESS:
        raise bad_request("裂变成功的数据不能删除")
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()


def mark_fission_data_finished(
    db: Session,
    *,
    actor: User,
    mission_id: int,
    data_id: int,
) -> MissionFissionDataPublic:
    """把尚未裂变成功的任务数据标记结束，只改裂变状态。"""
    row = _get_mutable_fission_row(
        db,
        actor=actor,
        mission_id=mission_id,
        data_id=data_id,
    )
    if row.fission_status == FISSION_STATUS_SUCCESS:
        raise bad_request("裂变成功的数据不能标记结束")
    if row.fission_status != FISSION_STATUS_MARKED_FINISHED:
        row.fission_status = FISSION_STATUS_MARKED_FINISHED
        db.commit()
        db.refresh(row)
    return MissionFissionDataPublic.model_validate(row)


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
    mission = _get_visible_mission(
        db,
        mission_id=mission_id,
        actor=actor,
        supplier_id=supplier_id,
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
