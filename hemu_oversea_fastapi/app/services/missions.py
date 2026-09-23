from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.core.deps import Pagination
from app.core.errors import bad_request, forbidden, not_found
from app.core.roles import Role
from app.models.mission import (
    MISSION_STATUS_MARKED_FINISHED,
    MISSION_STATUS_PENDING,
    MISSION_STATUS_RUNNING,
    Mission,
    MissionDataDhFission,
    MissionLog,
)
from app.models.user import User
from app.schemas.common import PageData
from app.schemas.mission import (
    MissionFissionDataPublic,
    MissionLogPublic,
    MissionPublic,
)

PLACEHOLDER_MESSAGE = "功能待补充"

_PLATFORM_ROLES = {Role.SUPER_ADMIN.value, Role.PLATFORM_STAFF.value}
_SUPPLIER_PORTAL_ROLES = {Role.SUPPLIER_ADMIN.value, Role.SUPPLIER_STAFF.value}
_MARKABLE_STATUSES = {MISSION_STATUS_PENDING, MISSION_STATUS_RUNNING}


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
    supplier_id = _require_supplier_admin(actor)
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


def mark_mission_finished(
    db: Session,
    *,
    mission_id: int,
    actor: User,
) -> MissionPublic:
    supplier_id = _require_supplier_admin(actor)
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
    rows = db.scalars(
        select(MissionDataDhFission)
        .where(*filters)
        .order_by(MissionDataDhFission.id.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()
    return PageData(
        items=[MissionFissionDataPublic.model_validate(row) for row in rows],
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
