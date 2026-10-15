"""SKU 属性模版 CRUD。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import Pagination
from app.core.errors import bad_request, conflict, not_found
from app.core.sku_code import normalize_sku_code, to_base_sku_code
from app.models.product_category_dh import ProductCategoryDh
from app.models.sku_attr_template_dh import SkuAttrTemplateDh
from app.models.sku_base_info_dh import SkuBaseInfoDh
from app.schemas.common import PageData
from app.schemas.sku_attr_template import (
    SkuAttrTemplateListItemPublic,
    SkuAttrTemplateLookupItemPublic,
    SkuAttrTemplateLookupPublic,
    SkuAttrTemplatePublic,
)


def _format_cate_name(pub_name_cn: str | None, pub_name: str | None) -> str:
    cn = (pub_name_cn or "").strip()
    en = (pub_name or "").strip()
    if cn and en:
        return f"{cn}({en})"
    return cn or en


def _require_supplier_id(supplier_id: int | None) -> int:
    if supplier_id is None or supplier_id <= 0:
        raise bad_request("当前账号未绑定供应商，无法操作属性模板")
    return supplier_id


def _normalize_raw_json(raw_json: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw_json, dict):
        raise bad_request("raw_json 必须为对象")
    attr_list = raw_json.get("attr_list")
    if attr_list is None:
        attr_list = []
    if not isinstance(attr_list, list):
        raise bad_request("raw_json.attr_list 必须为数组")
    return {"attr_list": attr_list}


def _resolve_leaf_category(db: Session, cate_pub_id: str) -> ProductCategoryDh:
    cate_id = str(cate_pub_id or "").strip()
    if not cate_id:
        raise bad_request("cate_pub_id 不能为空")
    row = db.scalar(
        select(ProductCategoryDh).where(ProductCategoryDh.cate_pub_id == cate_id)
    )
    if row is None:
        raise not_found(f"类目不存在：cate_pub_id={cate_id}")
    if str(row.leaf) != "1":
        raise bad_request("仅叶子类目可配置属性模板，请选择最末级分类")
    return row


def _ensure_sku_exists(db: Session, *, supplier_id: int, sku_code: str) -> str:
    code = normalize_sku_code(sku_code)
    if not code:
        raise bad_request("sku_code 不能为空")
    exists = db.scalar(
        select(SkuBaseInfoDh.id).where(
            SkuBaseInfoDh.supplier_id == supplier_id,
            SkuBaseInfoDh.sku_code == code,
        )
    )
    if exists is None:
        raise bad_request(f"SKU 编码不存在：{code}")
    return code


def _cate_name(row: ProductCategoryDh | None) -> str | None:
    if row is None:
        return None
    return _format_cate_name(row.pub_name_cn, row.pub_name) or None


def _to_list_item(
    row: SkuAttrTemplateDh,
    category: ProductCategoryDh | None,
    *,
    supplier_name: str | None = None,
) -> SkuAttrTemplateListItemPublic:
    return SkuAttrTemplateListItemPublic(
        id=row.id,
        sku_code=row.sku_code,
        cate_pub_id=row.cate_pub_id,
        cate_name=_cate_name(category),
        category_id=category.id if category else None,
        supplier_id=row.supplier_id,
        supplier_name=supplier_name,
        updated_at=row.updated_at,
    )


def _to_public(
    row: SkuAttrTemplateDh,
    category: ProductCategoryDh | None,
    *,
    supplier_name: str | None = None,
) -> SkuAttrTemplatePublic:
    return SkuAttrTemplatePublic(
        id=row.id,
        supplier_id=row.supplier_id,
        supplier_name=supplier_name,
        sku_code=row.sku_code,
        cate_pub_id=row.cate_pub_id,
        cate_name=_cate_name(category),
        category_id=category.id if category else None,
        raw_json=row.raw_json if isinstance(row.raw_json, dict) else {"attr_list": []},
        created_at=row.created_at,
        updated_at=row.updated_at,
        created_by=row.created_by,
        updated_by=row.updated_by,
    )


def _get_owned_row(
    db: Session,
    *,
    template_id: int,
    supplier_id: int,
) -> SkuAttrTemplateDh:
    row = db.get(SkuAttrTemplateDh, template_id)
    if row is None or row.supplier_id != supplier_id:
        raise not_found("属性模板不存在")
    return row


def _find_conflict(
    db: Session,
    *,
    supplier_id: int,
    sku_code: str,
    cate_pub_id: str,
    exclude_id: int | None = None,
) -> bool:
    stmt = select(SkuAttrTemplateDh.id).where(
        SkuAttrTemplateDh.supplier_id == supplier_id,
        SkuAttrTemplateDh.sku_code == sku_code,
        SkuAttrTemplateDh.cate_pub_id == cate_pub_id,
    )
    if exclude_id is not None:
        stmt = stmt.where(SkuAttrTemplateDh.id != exclude_id)
    return db.scalar(stmt) is not None


def list_sku_attr_templates(
    db: Session,
    *,
    supplier_id: int | None,
    sku_code: str | None,
    cate_pub_id: str | None,
    pagination: Pagination,
) -> PageData[SkuAttrTemplateListItemPublic]:
    sid = _require_supplier_id(supplier_id)
    stmt = select(SkuAttrTemplateDh).where(SkuAttrTemplateDh.supplier_id == sid)
    count_stmt = (
        select(func.count())
        .select_from(SkuAttrTemplateDh)
        .where(SkuAttrTemplateDh.supplier_id == sid)
    )

    code_kw = (sku_code or "").strip()
    if code_kw:
        like = f"%{code_kw}%"
        stmt = stmt.where(SkuAttrTemplateDh.sku_code.ilike(like))
        count_stmt = count_stmt.where(SkuAttrTemplateDh.sku_code.ilike(like))

    cate = (cate_pub_id or "").strip()
    if cate:
        stmt = stmt.where(SkuAttrTemplateDh.cate_pub_id == cate)
        count_stmt = count_stmt.where(SkuAttrTemplateDh.cate_pub_id == cate)

    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(
        stmt.order_by(SkuAttrTemplateDh.id.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()

    cate_ids = {row.cate_pub_id for row in rows}
    categories: dict[str, ProductCategoryDh] = {}
    if cate_ids:
        for cat in db.scalars(
            select(ProductCategoryDh).where(
                ProductCategoryDh.cate_pub_id.in_(cate_ids)
            )
        ).all():
            categories[cat.cate_pub_id] = cat

    from app.models.supplier import Supplier

    supplier_name = db.scalar(select(Supplier.name).where(Supplier.id == sid))
    return PageData(
        items=[
            _to_list_item(
                row,
                categories.get(row.cate_pub_id),
                supplier_name=supplier_name,
            )
            for row in rows
        ],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def get_sku_attr_template(
    db: Session,
    *,
    supplier_id: int | None,
    template_id: int,
) -> SkuAttrTemplatePublic:
    sid = _require_supplier_id(supplier_id)
    row = _get_owned_row(db, template_id=template_id, supplier_id=sid)
    category = db.scalar(
        select(ProductCategoryDh).where(
            ProductCategoryDh.cate_pub_id == row.cate_pub_id
        )
    )
    return _to_public(row, category)


def create_sku_attr_template(
    db: Session,
    *,
    supplier_id: int | None,
    actor_id: int,
    sku_code: str,
    cate_pub_id: str,
    raw_json: dict[str, Any],
) -> SkuAttrTemplatePublic:
    sid = _require_supplier_id(supplier_id)
    code = _ensure_sku_exists(db, supplier_id=sid, sku_code=sku_code)
    category = _resolve_leaf_category(db, cate_pub_id)
    payload = _normalize_raw_json(raw_json)
    if _find_conflict(
        db,
        supplier_id=sid,
        sku_code=code,
        cate_pub_id=category.cate_pub_id,
    ):
        raise conflict("该 SKU 在此分类下已存在属性模板")

    row = SkuAttrTemplateDh(
        supplier_id=sid,
        sku_code=code,
        cate_pub_id=category.cate_pub_id,
        raw_json=payload,
        created_by=actor_id,
        updated_by=actor_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_public(row, category)


def update_sku_attr_template(
    db: Session,
    *,
    supplier_id: int | None,
    actor_id: int,
    template_id: int,
    sku_code: str,
    cate_pub_id: str,
    raw_json: dict[str, Any],
) -> SkuAttrTemplatePublic:
    sid = _require_supplier_id(supplier_id)
    row = _get_owned_row(db, template_id=template_id, supplier_id=sid)
    code = _ensure_sku_exists(db, supplier_id=sid, sku_code=sku_code)
    category = _resolve_leaf_category(db, cate_pub_id)
    payload = _normalize_raw_json(raw_json)
    if _find_conflict(
        db,
        supplier_id=sid,
        sku_code=code,
        cate_pub_id=category.cate_pub_id,
        exclude_id=row.id,
    ):
        raise conflict("该 SKU 在此分类下已存在属性模板")

    row.sku_code = code
    row.cate_pub_id = category.cate_pub_id
    row.raw_json = payload
    row.updated_by = actor_id
    db.commit()
    db.refresh(row)
    return _to_public(row, category)


def delete_sku_attr_template(
    db: Session,
    *,
    supplier_id: int | None,
    template_id: int,
) -> None:
    sid = _require_supplier_id(supplier_id)
    row = _get_owned_row(db, template_id=template_id, supplier_id=sid)
    db.delete(row)
    db.commit()


def lookup_sku_attr_templates(
    db: Session,
    *,
    supplier_id: int | None,
    cate_pub_id: str,
    sku_codes: list[str],
) -> SkuAttrTemplateLookupPublic:
    """按供应商 + 基型号列表 + 叶子分类批量查找属性模板。"""
    sid = _require_supplier_id(supplier_id)
    cate = str(cate_pub_id or "").strip()
    if not cate:
        raise bad_request("cate_pub_id 不能为空")

    # 保持入参顺序去重
    bases: list[str] = []
    seen: set[str] = set()
    for raw in sku_codes:
        base = to_base_sku_code(raw)
        if not base or base in seen:
            continue
        seen.add(base)
        bases.append(base)
    if not bases:
        raise bad_request("sku_codes 无有效产品型号")

    rows = db.scalars(
        select(SkuAttrTemplateDh).where(
            SkuAttrTemplateDh.supplier_id == sid,
            SkuAttrTemplateDh.cate_pub_id == cate,
            SkuAttrTemplateDh.sku_code.in_(bases),
        )
    ).all()
    by_code = {row.sku_code: row for row in rows}

    items: list[SkuAttrTemplateLookupItemPublic] = []
    for code in bases:
        row = by_code.get(code)
        if row is None:
            items.append(
                SkuAttrTemplateLookupItemPublic(
                    sku_code=code,
                    found=False,
                    raw_json=None,
                )
            )
            continue
        raw = row.raw_json if isinstance(row.raw_json, dict) else {"attr_list": []}
        items.append(
            SkuAttrTemplateLookupItemPublic(
                sku_code=code,
                found=True,
                raw_json=raw,
            )
        )
    return SkuAttrTemplateLookupPublic(items=items)
