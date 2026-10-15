from __future__ import annotations

import re
from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import bad_request, forbidden, not_found
from app.core.permission_catalog import (
    PLATFORM_TREE_SCOPES,
    SUPPLIER_POOL_SCOPES,
)
from app.core.roles import (
    Role,
    is_platform_admin,
)
from app.models.permission import (
    BizRole,
    Permission,
    RolePermission,
    SupplierPermission,
    UserRole,
)
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.permission import PermissionPublic, PermissionTreeNode

_PERMISSION_CODE_RE = re.compile(
    r"^[a-zA-Z][a-zA-Z0-9]*(?:\.[a-zA-Z][a-zA-Z0-9]*)*$"
)
_VALID_TYPES = frozenset({"menu", "button"})
_VALID_SCOPES = frozenset({"platform", "supplier", "common"})


def to_user_public_dict(user: User, db: Session) -> dict:
    """组装带 permission_codes 的 UserPublic 字典。"""
    from app.schemas.user import UserPublic

    data = UserPublic.model_validate(user).model_dump()
    data["permission_codes"] = resolve_permission_codes(db, user)
    data["supplier_name"] = None
    if user.supplier_id is not None:
        supplier = db.get(Supplier, user.supplier_id)
        if supplier is not None and supplier.deleted_at is None:
            data["supplier_name"] = supplier.name
    return data


def resolve_permission_codes(db: Session, user: User) -> list[str]:
    role = user.role

    if is_platform_admin(role):
        rows = db.scalars(
            select(Permission.code).where(Permission.is_active.is_(True))
        ).all()
        return sorted(rows)

    if role == Role.PLATFORM_STAFF.value:
        return sorted(_codes_from_user_roles(db, user.id, supplier_id=None))

    if role == Role.SUPPLIER_ADMIN.value:
        if user.supplier_id is None:
            return []
        return sorted(_codes_from_supplier_pool(db, user.supplier_id))

    if role == Role.SUPPLIER_STAFF.value:
        if user.supplier_id is None:
            return []
        role_codes = set(
            _codes_from_user_roles(db, user.id, supplier_id=user.supplier_id)
        )
        pool = set(_codes_from_supplier_pool(db, user.supplier_id))
        return sorted(role_codes & pool)

    return []


def user_has_permissions(
    db: Session,
    user: User,
    *codes: str,
    require_all: bool = True,
) -> bool:
    if not codes:
        return True
    if is_platform_admin(user.role):
        return True
    owned = set(resolve_permission_codes(db, user))
    needed = set(codes)
    if require_all:
        return needed <= owned
    return bool(needed & owned)


def _codes_from_user_roles(
    db: Session,
    user_id: int,
    *,
    supplier_id: int | None,
) -> list[str]:
    stmt = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(BizRole, BizRole.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == BizRole.id)
        .where(
            UserRole.user_id == user_id,
            BizRole.deleted_at.is_(None),
            BizRole.is_active.is_(True),
            Permission.is_active.is_(True),
        )
    )
    if supplier_id is None:
        stmt = stmt.where(BizRole.supplier_id.is_(None))
    else:
        stmt = stmt.where(BizRole.supplier_id == supplier_id)
    return list(db.scalars(stmt).all())


def _codes_from_supplier_pool(db: Session, supplier_id: int) -> list[str]:
    return list(
        db.scalars(
            select(Permission.code)
            .join(
                SupplierPermission,
                SupplierPermission.permission_id == Permission.id,
            )
            .where(
                SupplierPermission.supplier_id == supplier_id,
                Permission.is_active.is_(True),
            )
        ).all()
    )


def expand_permission_codes_with_ancestors(
    db: Session,
    codes: list[str],
) -> list[str]:
    """勾选子节点时补齐祖先菜单码，保证路由 access 生效。"""
    if not codes:
        return []
    all_perms = list(
        db.scalars(select(Permission).where(Permission.is_active.is_(True))).all()
    )
    by_code = {p.code: p for p in all_perms}
    by_id = {p.id: p for p in all_perms}
    result: set[str] = set()
    for code in codes:
        cur = by_code.get(code)
        while cur is not None:
            result.add(cur.code)
            cur = by_id.get(cur.parent_id) if cur.parent_id else None
    return sorted(result)


def get_permissions_by_codes(
    db: Session,
    codes: list[str],
) -> list[Permission]:
    expanded = expand_permission_codes_with_ancestors(db, codes)
    if not expanded:
        return []
    rows = db.scalars(
        select(Permission).where(
            Permission.code.in_(expanded),
            Permission.is_active.is_(True),
        )
    ).all()
    found = {p.code for p in rows}
    missing = set(expanded) - found
    if missing:
        raise bad_request(f"无效权限码: {', '.join(sorted(missing))}")
    return list(rows)


def assert_codes_subset(
    allowed: set[str],
    codes: list[str],
    *,
    message: str = "权限超出可分配范围",
) -> None:
    extra = set(codes) - allowed
    if extra:
        raise forbidden(f"{message}: {', '.join(sorted(extra))}")


def actor_grantable_codes(db: Session, actor: User) -> set[str]:
    if is_platform_admin(actor.role):
        return set(
            db.scalars(
                select(Permission.code).where(Permission.is_active.is_(True))
            ).all()
        )
    return set(resolve_permission_codes(db, actor))


def list_permission_tree(
    db: Session,
    *,
    scopes: set[str] | frozenset[str] | None = None,
    only_codes: set[str] | None = None,
    include_inactive: bool = False,
) -> list[PermissionTreeNode]:
    stmt = select(Permission)
    if not include_inactive:
        stmt = stmt.where(Permission.is_active.is_(True))
    if scopes is not None:
        stmt = stmt.where(Permission.scope.in_(list(scopes)))
    rows = list(db.scalars(stmt.order_by(Permission.sort_order, Permission.id)).all())
    if only_codes is not None:
        # 含祖先：勾选子节点时树仍完整
        by_id = {p.id: p for p in rows}
        keep_ids: set[int] = set()
        code_set = only_codes
        for p in rows:
            if p.code not in code_set:
                continue
            cur: Permission | None = p
            while cur is not None and cur.id not in keep_ids:
                keep_ids.add(cur.id)
                cur = by_id.get(cur.parent_id) if cur.parent_id else None
        rows = [p for p in rows if p.id in keep_ids]

    children_map: dict[int | None, list[Permission]] = defaultdict(list)
    for p in rows:
        children_map[p.parent_id].append(p)

    def build(parent_id: int | None) -> list[PermissionTreeNode]:
        nodes: list[PermissionTreeNode] = []
        for p in children_map.get(parent_id, []):
            nodes.append(
                PermissionTreeNode(
                    id=p.id,
                    code=p.code,
                    title=p.title,
                    type=p.type,
                    scope=p.scope,
                    path=p.path,
                    sort_order=p.sort_order,
                    is_active=p.is_active,
                    children=build(p.id),
                )
            )
        return nodes

    return build(None)


def platform_permission_tree(db: Session) -> list[PermissionTreeNode]:
    return list_permission_tree(db, scopes=PLATFORM_TREE_SCOPES)


def supplier_assignable_permission_tree(db: Session) -> list[PermissionTreeNode]:
    """平台给供应商勾选池时用：supplier + common。"""
    return list_permission_tree(db, scopes=SUPPLIER_POOL_SCOPES)


def supplier_pool_permission_tree(
    db: Session,
    supplier_id: int,
) -> list[PermissionTreeNode]:
    codes = set(_codes_from_supplier_pool(db, supplier_id))
    return list_permission_tree(db, only_codes=codes)


def replace_supplier_pool(
    db: Session,
    *,
    supplier_id: int,
    permission_codes: list[str],
) -> None:
    perms = get_permissions_by_codes(db, permission_codes)
    for p in perms:
        if p.scope not in SUPPLIER_POOL_SCOPES:
            raise bad_request(f"权限 {p.code} 不可分配给供应商")

    new_ids = {p.id for p in perms}
    existing = list(
        db.scalars(
            select(SupplierPermission).where(
                SupplierPermission.supplier_id == supplier_id
            )
        ).all()
    )
    existing_ids = {row.permission_id for row in existing}
    to_add = new_ids - existing_ids
    to_remove = existing_ids - new_ids

    for pid in to_add:
        db.add(
            SupplierPermission(supplier_id=supplier_id, permission_id=pid)
        )

    if to_remove:
        db.execute(
            delete(SupplierPermission).where(
                SupplierPermission.supplier_id == supplier_id,
                SupplierPermission.permission_id.in_(to_remove),
            )
        )
        # 缩池：清理该供应商角色上越权的权限
        role_ids = list(
            db.scalars(
                select(BizRole.id).where(
                    BizRole.supplier_id == supplier_id,
                    BizRole.deleted_at.is_(None),
                )
            ).all()
        )
        if role_ids:
            db.execute(
                delete(RolePermission).where(
                    RolePermission.role_id.in_(role_ids),
                    RolePermission.permission_id.in_(to_remove),
                )
            )


def get_supplier_permission_codes(db: Session, supplier_id: int) -> list[str]:
    return sorted(_codes_from_supplier_pool(db, supplier_id))


def replace_role_permissions(
    db: Session,
    *,
    role_id: int,
    permission_codes: list[str],
) -> None:
    perms = get_permissions_by_codes(db, permission_codes)
    new_ids = {p.id for p in perms}
    db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    for pid in new_ids:
        db.add(RolePermission(role_id=role_id, permission_id=pid))


def replace_user_roles(
    db: Session,
    *,
    user_id: int,
    role_ids: list[int],
    expected_supplier_id: int | None,
) -> None:
    """expected_supplier_id=None 表示平台角色。"""
    unique_ids = list(dict.fromkeys(role_ids))
    if unique_ids:
        roles = list(
            db.scalars(
                select(BizRole).where(
                    BizRole.id.in_(unique_ids),
                    BizRole.deleted_at.is_(None),
                )
            ).all()
        )
        if len(roles) != len(unique_ids):
            raise bad_request("存在无效或已删除的角色")
        for role in roles:
            if expected_supplier_id is None:
                if role.supplier_id is not None:
                    raise bad_request("不能绑定供应商角色")
            elif role.supplier_id != expected_supplier_id:
                raise bad_request("角色不属于当前供应商")

    db.execute(delete(UserRole).where(UserRole.user_id == user_id))
    for rid in unique_ids:
        db.add(UserRole(user_id=user_id, role_id=rid))


def list_role_permission_codes(db: Session, role_id: int) -> list[str]:
    return sorted(
        db.scalars(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
        ).all()
    )


def list_user_role_summaries(
    db: Session,
    user_ids: list[int],
) -> dict[int, list[dict]]:
    if not user_ids:
        return {}
    rows = db.execute(
        select(UserRole.user_id, BizRole.id, BizRole.name)
        .join(BizRole, BizRole.id == UserRole.role_id)
        .where(
            UserRole.user_id.in_(user_ids),
            BizRole.deleted_at.is_(None),
        )
    ).all()
    result: dict[int, list[dict]] = defaultdict(list)
    for user_id, role_id, name in rows:
        result[user_id].append({"id": role_id, "name": name})
    return result


def _normalize_permission_code(code: str) -> str:
    cleaned = code.strip()
    if not cleaned or not _PERMISSION_CODE_RE.fullmatch(cleaned):
        raise bad_request(
            "权限码格式无效，示例：mission.logs（字母数字分段，点号连接）"
        )
    return cleaned


def _resolve_parent_id(
    db: Session,
    *,
    parent_id: int | None,
    parent_code: str | None,
) -> int | None:
    if parent_id is not None:
        parent = db.get(Permission, parent_id)
        if parent is None:
            raise bad_request("父权限不存在")
        return parent.id
    if parent_code:
        parent = db.scalar(
            select(Permission).where(Permission.code == parent_code.strip())
        )
        if parent is None:
            raise bad_request(f"父权限不存在: {parent_code}")
        return parent.id
    return None


def _assert_no_parent_cycle(
    db: Session,
    *,
    permission_id: int,
    parent_id: int | None,
) -> None:
    if parent_id is None:
        return
    if parent_id == permission_id:
        raise bad_request("父权限不能是自身")
    cur_id: int | None = parent_id
    seen: set[int] = set()
    while cur_id is not None:
        if cur_id == permission_id:
            raise bad_request("父权限不能是自身的子节点")
        if cur_id in seen:
            break
        seen.add(cur_id)
        parent = db.get(Permission, cur_id)
        if parent is None:
            break
        cur_id = parent.parent_id


def _grant_permission_to_all_suppliers(db: Session, permission_id: int) -> None:
    supplier_ids = list(
        db.scalars(
            select(Supplier.id).where(Supplier.deleted_at.is_(None))
        ).all()
    )
    if not supplier_ids:
        return
    existing = set(
        db.scalars(
            select(SupplierPermission.supplier_id).where(
                SupplierPermission.permission_id == permission_id,
                SupplierPermission.supplier_id.in_(supplier_ids),
            )
        ).all()
    )
    for sid in supplier_ids:
        if sid in existing:
            continue
        db.add(SupplierPermission(supplier_id=sid, permission_id=permission_id))


def get_permission(db: Session, permission_id: int) -> PermissionPublic:
    row = db.get(Permission, permission_id)
    if row is None:
        raise not_found("权限不存在")
    return PermissionPublic.model_validate(row)


def create_permission(
    db: Session,
    *,
    code: str,
    parent_id: int | None,
    parent_code: str | None,
    perm_type: str,
    title: str,
    path: str | None,
    scope: str,
    sort_order: int,
    is_active: bool,
    grant_to_all_suppliers: bool,
) -> PermissionPublic:
    if perm_type not in _VALID_TYPES:
        raise bad_request("type 仅支持 menu / button")
    if scope not in _VALID_SCOPES:
        raise bad_request("scope 仅支持 platform / supplier / common")

    cleaned_code = _normalize_permission_code(code)
    exists = db.scalar(
        select(Permission.id).where(Permission.code == cleaned_code)
    )
    if exists is not None:
        raise bad_request(f"权限码已存在: {cleaned_code}")

    cleaned_title = title.strip()
    if not cleaned_title:
        raise bad_request("请填写权限名称")

    resolved_parent_id = _resolve_parent_id(
        db,
        parent_id=parent_id,
        parent_code=parent_code,
    )
    cleaned_path = path.strip() if path else None
    if cleaned_path == "":
        cleaned_path = None
    if perm_type == "button" and cleaned_path is not None:
        raise bad_request("按钮权限不需要 path")

    row = Permission(
        code=cleaned_code,
        parent_id=resolved_parent_id,
        type=perm_type,
        title=cleaned_title,
        path=cleaned_path,
        scope=scope,
        sort_order=sort_order,
        is_active=is_active,
    )
    db.add(row)
    db.flush()

    if grant_to_all_suppliers and scope in SUPPLIER_POOL_SCOPES:
        _grant_permission_to_all_suppliers(db, row.id)

    db.commit()
    db.refresh(row)
    return PermissionPublic.model_validate(row)


def update_permission(
    db: Session,
    *,
    permission_id: int,
    fields: dict,
) -> PermissionPublic:
    row = db.get(Permission, permission_id)
    if row is None:
        raise not_found("权限不存在")

    if "code" in fields and fields["code"] is not None:
        cleaned_code = _normalize_permission_code(fields["code"])
        if cleaned_code != row.code:
            exists = db.scalar(
                select(Permission.id).where(
                    Permission.code == cleaned_code,
                    Permission.id != row.id,
                )
            )
            if exists is not None:
                raise bad_request(f"权限码已存在: {cleaned_code}")
            row.code = cleaned_code

    if "parent_id" in fields:
        new_parent_id = fields["parent_id"]
        if new_parent_id is not None:
            parent = db.get(Permission, new_parent_id)
            if parent is None:
                raise bad_request("父权限不存在")
            _assert_no_parent_cycle(
                db,
                permission_id=row.id,
                parent_id=new_parent_id,
            )
        row.parent_id = new_parent_id

    if "type" in fields and fields["type"] is not None:
        if fields["type"] not in _VALID_TYPES:
            raise bad_request("type 仅支持 menu / button")
        row.type = fields["type"]

    if "title" in fields and fields["title"] is not None:
        cleaned_title = fields["title"].strip()
        if not cleaned_title:
            raise bad_request("请填写权限名称")
        row.title = cleaned_title

    if "path" in fields:
        cleaned_path = fields["path"].strip() if fields["path"] else None
        if cleaned_path == "":
            cleaned_path = None
        row.path = cleaned_path

    if "scope" in fields and fields["scope"] is not None:
        if fields["scope"] not in _VALID_SCOPES:
            raise bad_request("scope 仅支持 platform / supplier / common")
        row.scope = fields["scope"]

    if "sort_order" in fields and fields["sort_order"] is not None:
        row.sort_order = int(fields["sort_order"])

    if "is_active" in fields and fields["is_active"] is not None:
        row.is_active = bool(fields["is_active"])

    if row.type == "button" and row.path is not None:
        raise bad_request("按钮权限不需要 path")

    db.commit()
    db.refresh(row)
    return PermissionPublic.model_validate(row)


def delete_permission(db: Session, *, permission_id: int) -> None:
    row = db.get(Permission, permission_id)
    if row is None:
        raise not_found("权限不存在")
    child_id = db.scalar(
        select(Permission.id).where(Permission.parent_id == permission_id).limit(1)
    )
    if child_id is not None:
        raise bad_request("请先删除子权限")
    # role_permissions / supplier_permissions 对 permission_id 为 ON DELETE CASCADE
    db.delete(row)
    db.commit()
