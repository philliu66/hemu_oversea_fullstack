"""商品相关业务（管理端）。"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.deps import Pagination
from app.core.errors import bad_request, not_found
from app.core.store_types import StoreType
from app.models.product_category_dh import ProductCategoryDh
from app.models.product_dh import ProductDh
from app.models.store import Store
from app.schemas.common import PageData
from app.schemas.product import (
    DHGATE_ROOT_PARE_CATE_PUB_ID,
    DhCategoryAttrPublic,
    DhCategoryAttrsPublic,
    DhCategoryAttrValPublic,
    DhCategoryPathPublic,
    DhCategoryPublic,
    DhProductDetailPublic,
    DhProductPublic,
    DhProductSelectedAttrPublic,
    DhProductSelectedAttrValPublic,
    DhProductSkuPublic,
    DhProductSpecSelfDefPublic,
    DhSeedCategoryPublic,
)
from app.services.dhgate import get_category, get_category_path, get_dhgate_client, get_item
from app.services.products_dh import _attr_combo_text, _spec_self_def_lookup

logger = logging.getLogger("app")

_DH_IMAGE_PREFIX = "http://image.dhgate.com/100x100/"
_DH_DETAIL_IMAGE_PREFIX = "https://image.dhgate.com/"
_DH_CATEGORY_PATH_SEP = " > "
_BJ = ZoneInfo("Asia/Shanghai")

# dh.item.get state 编码 → 状态描述
_DH_PRODUCT_STATE_LABELS: dict[str, str] = {
    "100000": "未定义",
    "100100": "上架产品",
    "100200": "待审核产品",
    "100300": "审核未通过产品",
    "100400": "下架产品",
    "100500": "品牌商投诉产品",
    "100600": "疑似侵权产品",
    "100700": "内容违规品",
}


def _to_dh_category_public(row: ProductCategoryDh) -> DhCategoryPublic:
    return DhCategoryPublic(
        id=row.id,
        cate_pub_id=row.cate_pub_id,
        pub_name=row.pub_name,
        pub_name_cn=row.pub_name_cn,
        remark=row.remark,
        leaf=row.leaf,
        pare_cate_pub_id=row.pare_cate_pub_id,
        is_leaf=str(row.leaf) == "1",
    )


def _build_dh_main_image_url(path: str | None) -> str | None:
    """库内相对路径补全敦煌主图前缀；已是完整 URL 则原样返回。"""
    if path is None:
        return None
    text = str(path).strip()
    if not text:
        return None
    if text.startswith(("http://", "https://")):
        return text
    return f"{_DH_IMAGE_PREFIX}{text.lstrip('/')}"


def _build_dh_detail_image_url(path: str | None) -> str | None:
    """详情图：相对路径补全 https://image.dhgate.com/。"""
    if path is None:
        return None
    text = str(path).strip()
    if not text:
        return None
    if text.startswith(("http://", "https://")):
        return text
    return f"{_DH_DETAIL_IMAGE_PREFIX}{text.lstrip('/')}"


def _dh_product_state_label(state: str | None) -> str | None:
    """将敦煌商品 state 编码转为文档状态描述。"""
    if state is None:
        return None
    code = str(state).strip()
    if not code:
        return None
    return _DH_PRODUCT_STATE_LABELS.get(code, code)


def _to_dh_product_public(row: ProductDh) -> DhProductPublic:
    data = DhProductPublic.model_validate(row)
    return data.model_copy(
        update={
            "main_image_url": _build_dh_main_image_url(row.main_image_url),
            "state": _dh_product_state_label(row.state),
        }
    )


def _format_category_path_segment(
    pub_name_cn: str | None,
    pub_name: str | None,
) -> str:
    """单段路径：中文(英文)。缺一侧时仅返回有值一侧。"""
    cn = (pub_name_cn or "").strip()
    en = (pub_name or "").strip()
    if cn and en:
        return f"{cn}({en})"
    return cn or en


def _join_category_path_name(segments: list[str]) -> str:
    return _DH_CATEGORY_PATH_SEP.join(s for s in segments if s)


def _list_product_img_urls(detail: dict[str, Any]) -> list[str]:
    images = detail.get("itemImgList")
    if not isinstance(images, list):
        return []
    urls: list[str] = []
    for img in images:
        if not isinstance(img, dict):
            continue
        url = _build_dh_detail_image_url(_as_str(img.get("imgUrl")))
        if url:
            urls.append(url)
    return urls


def _list_product_skus(detail: dict[str, Any]) -> list[DhProductSkuPublic]:
    sku_list = detail.get("itemSkuList")
    if not isinstance(sku_list, list):
        return []
    spec_lookup = _spec_self_def_lookup(detail)
    items: list[DhProductSkuPublic] = []
    for index, sku in enumerate(sku_list, start=1):
        if not isinstance(sku, dict):
            continue
        combo = sku.get("itemSkuAttrValueList")
        combo_list = combo if isinstance(combo, list) else []
        normalized_combo = [x for x in combo_list if isinstance(x, dict)]
        items.append(
            DhProductSkuPublic(
                id=index,
                sku_id=_as_str(sku.get("skuId")),
                sku_code=_as_str(sku.get("skuCode")),
                retail_price=_as_decimal(sku.get("retailPrice")),
                inventory=_as_int(sku.get("inventory")),
                sale_status=_as_str(sku.get("saleStatus")),
                pic_url=_build_dh_detail_image_url(_as_str(sku.get("picUrl"))),
                attr_combo_text=_attr_combo_text(normalized_combo, spec_lookup),
            )
        )
    return items


def _get_product_category(
    db: Session,
    cate_pub_id: str | None,
) -> DhCategoryPublic | None:
    if cate_pub_id is None or not str(cate_pub_id).strip():
        return None
    row = db.scalar(
        select(ProductCategoryDh).where(
            ProductCategoryDh.cate_pub_id == str(cate_pub_id).strip()
        )
    )
    if row is None:
        return None
    return _to_dh_category_public(row)


def _get_category_by_pub_id(
    db: Session,
    cate_pub_id: str,
) -> ProductCategoryDh | None:
    return db.scalar(
        select(ProductCategoryDh).where(
            ProductCategoryDh.cate_pub_id == cate_pub_id
        )
    )


def _walk_local_category_path(
    db: Session,
    cate_pub_id: str,
) -> list[DhCategoryPublic]:
    """本地 product_category_dh 向上回溯父级，再反转为根→叶。"""
    chain: list[ProductCategoryDh] = []
    current = str(cate_pub_id).strip()
    seen: set[str] = set()
    while current and current != DHGATE_ROOT_PARE_CATE_PUB_ID:
        if current in seen:
            break
        seen.add(current)
        row = _get_category_by_pub_id(db, current)
        if row is None:
            break
        chain.append(row)
        parent = (row.pare_cate_pub_id or "").strip()
        if not parent or parent == DHGATE_ROOT_PARE_CATE_PUB_ID:
            break
        current = parent
    chain.reverse()
    return [_to_dh_category_public(row) for row in chain]


def _path_items_from_dhgate_list(
    db: Session,
    publish_list: list[dict[str, Any]],
) -> list[DhCategoryPublic]:
    """将敦煌 categoryPublishList 转为展示节点（尽量补本地 id）。"""
    items: list[DhCategoryPublic] = []
    for raw in publish_list:
        if not isinstance(raw, dict):
            continue
        cate_pub_id = str(raw.get("catePubId") or "").strip()
        if not cate_pub_id:
            continue
        local = _get_category_by_pub_id(db, cate_pub_id)
        if local is not None:
            items.append(_to_dh_category_public(local))
            continue
        leaf = str(raw.get("leaf") or "0")
        items.append(
            DhCategoryPublic(
                id=0,
                cate_pub_id=cate_pub_id,
                pub_name=str(raw.get("pubName") or ""),
                pub_name_cn=(
                    str(raw.get("pubNameCn")).strip()
                    if raw.get("pubNameCn") not in (None, "")
                    else None
                ),
                remark=(
                    str(raw.get("remark")).strip()
                    if raw.get("remark") not in (None, "")
                    else None
                ),
                leaf=leaf,
                pare_cate_pub_id=(
                    str(raw.get("pareCatePubId")).strip()
                    if raw.get("pareCatePubId") not in (None, "")
                    else None
                ),
                is_leaf=leaf == "1",
            )
        )
    return items


def _pick_dhgate_store_id(db: Session, preferred_store_id: int | None) -> int:
    """优先用指定店铺；否则取任一已授权敦煌店。"""
    if preferred_store_id is not None:
        store = db.get(Store, preferred_store_id)
        if (
            store is not None
            and store.deleted_at is None
            and store.store_type == StoreType.DHGATE.value
            and store.access_token
        ):
            return store.id

    store = db.scalar(
        select(Store)
        .where(
            Store.deleted_at.is_(None),
            Store.store_type == StoreType.DHGATE.value,
            Store.access_token.isnot(None),
        )
        .order_by(Store.id.asc())
        .limit(1)
    )
    if store is None:
        raise bad_request("无可用的已授权敦煌店铺")
    return store.id


def resolve_dh_category_path(
    db: Session,
    *,
    cate_pub_id: str,
    store_id: int | None = None,
) -> tuple[list[DhCategoryPublic], str]:
    """
    获取类目全路径节点与 path_name。

    优先调用 dh.category.path.get；失败时回退本地表父子回溯。
    """
    cate_id = str(cate_pub_id or "").strip()
    if not cate_id:
        return [], ""

    path_items: list[DhCategoryPublic] = []
    try:
        client = get_dhgate_client(db, _pick_dhgate_store_id(db, store_id))
        payload = get_category_path(client, cate_pub_id=cate_id)
        publish_list = payload.get("categoryPublishList")
        if isinstance(publish_list, list) and publish_list:
            path_items = _path_items_from_dhgate_list(db, publish_list)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "敦煌类目路径查询失败，回退本地 cate_pub_id=%s: %s",
            cate_id,
            exc,
        )

    if not path_items:
        path_items = _walk_local_category_path(db, cate_id)

    path_name = _join_category_path_name(
        [
            _format_category_path_segment(item.pub_name_cn, item.pub_name)
            for item in path_items
        ]
    )
    return path_items, path_name


def list_dh_categories_by_parent(
    db: Session,
    *,
    parent_id: str | None,
) -> list[DhCategoryPublic]:
    """
    按父类目查询直接子类目（一层）。

    parent_id 为空时查一级类目（pare_cate_pub_id = 平台根 ID）。
    """
    if parent_id is None or not str(parent_id).strip():
        parent_key = DHGATE_ROOT_PARE_CATE_PUB_ID
    else:
        parent_key = str(parent_id).strip()

    rows = db.scalars(
        select(ProductCategoryDh)
        .where(ProductCategoryDh.pare_cate_pub_id == parent_key)
        .order_by(
            ProductCategoryDh.pub_name_cn.asc().nulls_last(),
            ProductCategoryDh.pub_name.asc(),
            ProductCategoryDh.cate_pub_id.asc(),
        )
    ).all()
    return [_to_dh_category_public(row) for row in rows]


def _to_dh_seed_category_public(
    row: ProductCategoryDh,
    *,
    product_count: int,
    is_leaf: bool,
) -> DhSeedCategoryPublic:
    return DhSeedCategoryPublic(
        id=row.id,
        cate_pub_id=row.cate_pub_id,
        pub_name=row.pub_name,
        pub_name_cn=row.pub_name_cn,
        remark=row.remark,
        leaf=row.leaf,
        pare_cate_pub_id=row.pare_cate_pub_id,
        is_leaf=is_leaf,
        product_count=product_count,
    )


def _orphan_dh_seed_category(
    cate_pub_id: str,
    product_count: int,
) -> DhSeedCategoryPublic:
    return DhSeedCategoryPublic(
        id=0,
        cate_pub_id=cate_pub_id,
        pub_name=cate_pub_id,
        pub_name_cn=None,
        remark=None,
        leaf="1",
        pare_cate_pub_id=None,
        is_leaf=True,
        product_count=product_count,
    )


def _seed_product_counts_by_cate_pub_id(db: Session) -> dict[str, int]:
    """product_dh 中 is_seed=1 按 cate_pub_id groupby 的商品数。"""
    rows = db.execute(
        select(ProductDh.cate_pub_id, func.count())
        .where(
            ProductDh.is_seed == "1",
            ProductDh.cate_pub_id.isnot(None),
            ProductDh.cate_pub_id != "",
        )
        .group_by(ProductDh.cate_pub_id)
    ).all()
    counts: dict[str, int] = {}
    for cate_pub_id, total in rows:
        key = str(cate_pub_id or "").strip()
        if not key:
            continue
        counts[key] = int(total or 0)
    return counts


def _build_dh_seed_category_index(
    db: Session,
) -> tuple[
    dict[str, int],
    dict[str, ProductCategoryDh],
    dict[str, list[ProductCategoryDh]],
    dict[str, int],
]:
    """
    构建种子商品类目索引。

    返回：
    - own_counts: 叶子/商品所属类目的 groupby 数量
    - by_pub_id: cate_pub_id → 类目行
    - children_map: 父 cate_pub_id → 直接子类目
    - subtree_counts: 各类目种子商品数（含全部下级汇总）
    """
    own_counts = _seed_product_counts_by_cate_pub_id(db)
    rows = db.scalars(select(ProductCategoryDh)).all()
    by_pub_id: dict[str, ProductCategoryDh] = {
        row.cate_pub_id: row for row in rows
    }
    children_map: dict[str, list[ProductCategoryDh]] = defaultdict(list)
    for row in rows:
        parent_key = (
            (row.pare_cate_pub_id or "").strip() or DHGATE_ROOT_PARE_CATE_PUB_ID
        )
        children_map[parent_key].append(row)

    subtree_counts: dict[str, int] = defaultdict(int)
    for cate_pub_id, total in own_counts.items():
        current = cate_pub_id
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            subtree_counts[current] += total
            row = by_pub_id.get(current)
            if row is None:
                break
            parent = (row.pare_cate_pub_id or "").strip()
            if not parent or parent == DHGATE_ROOT_PARE_CATE_PUB_ID:
                break
            if parent not in by_pub_id:
                break
            current = parent

    return own_counts, by_pub_id, children_map, dict(subtree_counts)


def _seed_category_sort_key(item: DhSeedCategoryPublic) -> tuple[str, str, str]:
    return (item.pub_name_cn or "", item.pub_name, item.cate_pub_id)


def _seed_category_has_visible_child(
    cate_pub_id: str,
    children_map: dict[str, list[ProductCategoryDh]],
    subtree_counts: dict[str, int],
) -> bool:
    return any(
        subtree_counts.get(child.cate_pub_id, 0) > 0
        for child in children_map.get(cate_pub_id, [])
    )


def list_dh_seed_categories_by_parent(
    db: Session,
    *,
    parent_id: str | None,
) -> list[DhSeedCategoryPublic]:
    """
    按父类目查询种子商品涉及的直接子类目（一层）。

    仅返回子树中存在 is_seed=1 商品的类目。
    子类目 product_count 为下级汇总；根类目 product_count 由
    product_dh groupby cate_pub_id 向上累计得到。
    """
    if parent_id is None or not str(parent_id).strip():
        parent_key = DHGATE_ROOT_PARE_CATE_PUB_ID
        is_root = True
    else:
        parent_key = str(parent_id).strip()
        is_root = False

    own_counts, by_pub_id, children_map, subtree_counts = (
        _build_dh_seed_category_index(db)
    )

    items: list[DhSeedCategoryPublic] = []
    attached: set[str] = set()
    for row in children_map.get(parent_key, []):
        product_count = subtree_counts.get(row.cate_pub_id, 0)
        if product_count <= 0:
            continue
        items.append(
            _to_dh_seed_category_public(
                row,
                product_count=product_count,
                is_leaf=not _seed_category_has_visible_child(
                    row.cate_pub_id,
                    children_map,
                    subtree_counts,
                ),
            )
        )
        attached.add(row.cate_pub_id)

    if is_root:
        for cate_pub_id, product_count in own_counts.items():
            if product_count <= 0 or cate_pub_id in attached or cate_pub_id in by_pub_id:
                continue
            items.append(_orphan_dh_seed_category(cate_pub_id, product_count))
            attached.add(cate_pub_id)

        for cate_pub_id, product_count in subtree_counts.items():
            if product_count <= 0 or cate_pub_id in attached:
                continue
            row = by_pub_id.get(cate_pub_id)
            if row is None:
                continue
            parent = (
                (row.pare_cate_pub_id or "").strip()
                or DHGATE_ROOT_PARE_CATE_PUB_ID
            )
            if parent == DHGATE_ROOT_PARE_CATE_PUB_ID or parent in by_pub_id:
                continue
            items.append(
                _to_dh_seed_category_public(
                    row,
                    product_count=product_count,
                    is_leaf=not _seed_category_has_visible_child(
                        row.cate_pub_id,
                        children_map,
                        subtree_counts,
                    ),
                )
            )
            attached.add(cate_pub_id)

    items.sort(key=_seed_category_sort_key)
    return items


def _cate_pub_ids_for_product_filter(db: Session, cate_pub_id: str) -> list[str]:
    """选中类目及其全部下级 cate_pub_id（含自身）。"""
    selected = str(cate_pub_id).strip()
    if not selected:
        return []

    _own_counts, _by_pub_id, children_map, _subtree_counts = (
        _build_dh_seed_category_index(db)
    )
    collected: list[str] = []
    seen: set[str] = set()
    stack = [selected]
    while stack:
        current = stack.pop()
        if not current or current in seen:
            continue
        seen.add(current)
        collected.append(current)
        for child in children_map.get(current, []):
            stack.append(child.cate_pub_id)
    return collected


def search_dh_categories(
    db: Session,
    *,
    keyword: str,
    leaf_only: bool = True,
    limit: int = 50,
) -> list[DhCategoryPublic]:
    """按中英文名称模糊搜索类目（默认仅叶子类目）。"""
    text = str(keyword).strip()
    if not text:
        return []

    pattern = f"%{text}%"
    filters = [
        or_(
            ProductCategoryDh.pub_name_cn.ilike(pattern),
            ProductCategoryDh.pub_name.ilike(pattern),
            ProductCategoryDh.cate_pub_id.ilike(pattern),
        )
    ]
    if leaf_only:
        filters.append(ProductCategoryDh.leaf == "1")

    rows = db.scalars(
        select(ProductCategoryDh)
        .where(*filters)
        .order_by(
            ProductCategoryDh.pub_name_cn.asc().nulls_last(),
            ProductCategoryDh.pub_name.asc(),
            ProductCategoryDh.cate_pub_id.asc(),
        )
        .limit(limit)
    ).all()
    return [_to_dh_category_public(row) for row in rows]


def get_dh_category_path(db: Session, category_id: int) -> DhCategoryPathPublic:
    """按本地类目主键 ID 获取从根到当前类目的全路径。"""
    row = db.get(ProductCategoryDh, category_id)
    if row is None:
        raise not_found("类目不存在")

    path_items, path_name = resolve_dh_category_path(
        db,
        cate_pub_id=row.cate_pub_id,
    )
    return DhCategoryPathPublic(
        id=row.id,
        cate_pub_id=row.cate_pub_id,
        path_name=path_name,
        path_items=path_items,
    )


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_int(value: Any) -> int | None:
    text = _as_str(value)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _as_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_dh_datetime(value: Any) -> datetime | None:
    text = _as_str(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(tzinfo=_BJ)
        except ValueError:
            continue
    return None


def _flag01(value: Any, default: str = "0") -> str:
    text = _as_str(value)
    return text if text in {"0", "1"} else default


def _parse_category_attr_values(raw_list: Any) -> list[DhCategoryAttrValPublic]:
    if not isinstance(raw_list, list):
        return []
    items: list[DhCategoryAttrValPublic] = []
    for raw in raw_list:
        if not isinstance(raw, dict):
            continue
        attr_val_id = _as_str(raw.get("attrValId"))
        if not attr_val_id:
            continue
        items.append(
            DhCategoryAttrValPublic(
                cate_pub_attrval_id=_as_int(raw.get("catePubAttrvalId")),
                cate_pub_attr_id=_as_int(raw.get("catePubAttrId")),
                attr_val_id=attr_val_id,
                pic_url=_as_str(raw.get("picUrl")),
                line_attrval_name=_as_str(raw.get("lineAttrvalName")),
                line_attrval_name_cn=_as_str(raw.get("lineAttrvalNameCn")),
            )
        )
    return items


def _parse_category_attrs(raw_list: Any) -> list[DhCategoryAttrPublic]:
    if not isinstance(raw_list, list):
        return []
    items: list[DhCategoryAttrPublic] = []
    for raw in raw_list:
        if not isinstance(raw, dict):
            continue
        attr_id = _as_str(raw.get("attrId"))
        if not attr_id:
            continue
        items.append(
            DhCategoryAttrPublic(
                cate_pub_attr_id=_as_int(raw.get("catePubAttrId")),
                attr_id=attr_id,
                cate_pub_id=_as_str(raw.get("catePubId")),
                required=_flag01(raw.get("required")),
                located=_flag01(raw.get("located")),
                sale_attr=_flag01(raw.get("saleAttr")),
                buy_attr=_flag01(raw.get("buyAttr")),
                style=_as_str(raw.get("style")) or "1",
                type=_as_str(raw.get("type")) or "1",
                defined=_flag01(raw.get("defined")),
                is_brand=_flag01(raw.get("isBrand")),
                line_attr_name=_as_str(raw.get("lineAttrName")),
                line_attr_name_cn=_as_str(raw.get("lineAttrNameCn")),
                isother=_flag01(raw.get("isother")),
                child_attr_id=_as_str(raw.get("childAttrId")),
                values=_parse_category_attr_values(
                    raw.get("categoryPubAttrValList")
                ),
            )
        )
    return items


def get_dh_category_attrs(
    db: Session,
    *,
    category_id: int,
) -> DhCategoryAttrsPublic:
    """按本地类目主键 ID 获取叶子类目属性定义（dh.category.get）。"""
    row = db.get(ProductCategoryDh, category_id)
    if row is None:
        raise not_found("类目不存在")
    if str(row.leaf) != "1":
        raise bad_request("仅叶子类目可查询属性，请选择最末级分类")

    client = get_dhgate_client(db, _pick_dhgate_store_id(db, None))
    payload = get_category(client, cate_pub_id=row.cate_pub_id)
    return DhCategoryAttrsPublic(
        id=row.id,
        cate_pub_id=row.cate_pub_id,
        pub_name=row.pub_name,
        pub_name_cn=row.pub_name_cn,
        leaf=row.leaf,
        attrs=_parse_category_attrs(payload.get("categoryPubAttrList")),
    )


def _parse_product_attr_value(raw: dict[str, Any]) -> DhProductSelectedAttrValPublic | None:
    attr_val_id = _as_str(raw.get("attrValId"))
    attr_name = _as_str(raw.get("attrName"))
    attr_name_cn = _as_str(raw.get("attrNameCn"))
    line_attrval_name = _as_str(raw.get("lineAttrvalName"))
    line_attrval_name_cn = _as_str(raw.get("lineAttrvalNameCn"))
    pic_url = _build_dh_detail_image_url(_as_str(raw.get("picUrl")))
    brand_id = _as_str(raw.get("brandId"))
    if not any(
        [
            attr_val_id,
            attr_name,
            attr_name_cn,
            line_attrval_name,
            line_attrval_name_cn,
            pic_url,
            brand_id,
        ]
    ):
        return None
    return DhProductSelectedAttrValPublic(
        attr_val_id=attr_val_id,
        attr_name=attr_name,
        attr_name_cn=attr_name_cn,
        line_attrval_name=line_attrval_name,
        line_attrval_name_cn=line_attrval_name_cn,
        pic_url=pic_url,
        brand_id=brand_id,
    )


def _list_product_selected_attrs(
    detail: dict[str, Any],
) -> list[DhProductSelectedAttrPublic]:
    """产品属性（itemAttrList）：类目属性 + 品牌属性(99) + 自定义属性(11)。"""
    attr_list = detail.get("itemAttrList")
    if not isinstance(attr_list, list):
        return []

    items: list[DhProductSelectedAttrPublic] = []
    for attr in attr_list:
        if not isinstance(attr, dict):
            continue
        attr_id = _as_str(attr.get("attrId"))
        if not attr_id:
            continue
        values: list[DhProductSelectedAttrValPublic] = []
        raw_values = attr.get("itemAttrValList")
        if isinstance(raw_values, list):
            for raw_val in raw_values:
                if not isinstance(raw_val, dict):
                    continue
                parsed_val = _parse_product_attr_value(raw_val)
                if parsed_val is not None:
                    values.append(parsed_val)
        items.append(
            DhProductSelectedAttrPublic(
                attr_id=attr_id,
                attr_name=_as_str(attr.get("attrName")),
                attr_name_cn=_as_str(attr.get("attrNameCn")),
                is_brand=_flag01(
                    attr.get("isbrand")
                    if attr.get("isbrand") is not None
                    else attr.get("isBrand")
                ),
                values=values,
            )
        )
    return items


def _parse_spec_self_def_item(raw: dict[str, Any]) -> DhProductSpecSelfDefPublic | None:
    attr_val_id = _as_str(raw.get("attrValId"))
    spec_attr_name = _as_str(raw.get("specAttrName"))
    attr_val_name = _as_str(raw.get("attrValName"))
    pic_url = _build_dh_detail_image_url(_as_str(raw.get("picUrl")))
    if not any([attr_val_id, spec_attr_name, attr_val_name, pic_url]):
        return None
    return DhProductSpecSelfDefPublic(
        attr_val_id=attr_val_id,
        spec_attr_name=spec_attr_name,
        attr_val_name=attr_val_name,
        pic_url=pic_url,
    )


def _list_product_spec_self_defs(
    detail: dict[str, Any],
) -> list[DhProductSpecSelfDefPublic]:
    """自定义规格（itemSpecSelfDefList），与产品属性无关。"""
    spec_list = detail.get("itemSpecSelfDefList")
    if not isinstance(spec_list, list):
        return []
    items: list[DhProductSpecSelfDefPublic] = []
    for raw_item in spec_list:
        if not isinstance(raw_item, dict):
            continue
        parsed = _parse_spec_self_def_item(raw_item)
        if parsed is not None:
            items.append(parsed)
    return items


def list_dh_products(
    db: Session,
    *,
    list_type: int,
    state: str | None,
    item_code: str | None,
    item_name: str | None,
    store_id: int | None,
    cate_pub_id: str | None,
    sort: int,
    pagination: Pagination,
) -> PageData[DhProductPublic]:
    """分页查询敦煌商品（product_dh）。"""
    filters = []
    # list_type: 0=全部，1=仅种子商品
    if list_type == 1:
        filters.append(ProductDh.is_seed == "1")

    if state is not None and str(state).strip():
        filters.append(ProductDh.state == str(state).strip())
    if item_code is not None and str(item_code).strip():
        filters.append(ProductDh.item_code == str(item_code).strip())
    if item_name is not None and str(item_name).strip():
        filters.append(ProductDh.item_name.ilike(f"%{str(item_name).strip()}%"))
    if store_id is not None:
        filters.append(ProductDh.store_id == store_id)
    if cate_pub_id is not None and str(cate_pub_id).strip():
        cate_ids = _cate_pub_ids_for_product_filter(db, str(cate_pub_id).strip())
        if cate_ids:
            filters.append(ProductDh.cate_pub_id.in_(cate_ids))
        else:
            filters.append(ProductDh.cate_pub_id == str(cate_pub_id).strip())

    count_stmt = select(func.count()).select_from(ProductDh)
    stmt = select(ProductDh)
    if filters:
        count_stmt = count_stmt.where(*filters)
        stmt = stmt.where(*filters)

    total = db.scalar(count_stmt) or 0

    # sort: 0=同步时间倒序，1=同步时间正序
    order_expr = (
        ProductDh.last_synced_at.asc().nulls_last()
        if sort == 1
        else ProductDh.last_synced_at.desc().nulls_last()
    )

    rows = db.scalars(
        stmt.order_by(order_expr, ProductDh.id.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).all()

    return PageData(
        items=[_to_dh_product_public(row) for row in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def _sku_price_stats(
    sku_list: list[DhProductSkuPublic],
) -> tuple[Decimal | None, Decimal | None, int, int]:
    prices: list[Decimal] = []
    total_inventory = 0
    for sku in sku_list:
        inventory = sku.inventory or 0
        total_inventory += inventory
        if sku.retail_price is not None and sku.sale_status != "0":
            prices.append(sku.retail_price)
    if not prices:
        return None, None, len(sku_list), total_inventory
    return min(prices), max(prices), len(sku_list), total_inventory


def _to_dh_product_detail_public(
    db: Session,
    row: ProductDh,
    detail: dict[str, Any],
) -> DhProductDetailPublic:
    """用敦煌 dh.item.get 结果组装详情，不写库。"""
    item_base = detail.get("itemBase") if isinstance(detail.get("itemBase"), dict) else {}
    sale = (
        detail.get("itemSaleSetting")
        if isinstance(detail.get("itemSaleSetting"), dict)
        else {}
    )
    package = (
        detail.get("itemPackage") if isinstance(detail.get("itemPackage"), dict) else {}
    )
    sku_list = _list_product_skus(detail)
    price_min, price_max, sku_count, total_inventory = _sku_price_stats(sku_list)
    cate_pub_id = _as_str(detail.get("catePubId"))
    return DhProductDetailPublic(
        id=row.id,
        store_id=row.store_id,
        item_code=row.item_code,
        site_id=row.site_id,
        is_seed=row.is_seed,
        supplier_id=_as_str(detail.get("supplierId")),
        cate_pub_id=cate_pub_id,
        state=_dh_product_state_label(_as_str(detail.get("state"))),
        item_name=_as_str(item_base.get("itemName")),
        short_desc=_as_str(item_base.get("shortDesc")),
        html_content=_as_str(item_base.get("htmlContent")),
        key_word1=_as_str(item_base.get("keyWord1")),
        key_word2=_as_str(item_base.get("keyWord2")),
        key_word3=_as_str(item_base.get("keyWord3")),
        video_url=_as_str(item_base.get("videoUrl")),
        min_wholesale_qty=_as_int(sale.get("minWholesaleQty")),
        max_sale_qty=_as_int(sale.get("maxSaleQty")),
        leading_time=_as_int(sale.get("leadingTime")),
        price_config_type=_as_str(sale.get("priceConfigType")),
        gross_weight=_as_decimal(package.get("grossWeight")),
        length=_as_decimal(package.get("length")),
        width=_as_decimal(package.get("width")),
        height=_as_decimal(package.get("height")),
        packing_quantity=_as_int(package.get("packingQuantity")),
        price_min=price_min,
        price_max=price_max,
        sku_count=sku_count,
        total_inventory=total_inventory,
        issample=_as_str(detail.get("issample")),
        is_dh_optimized=_as_str(detail.get("isDhOptimized")),
        vaild_day=_as_str(detail.get("vaildDay")),
        expire_date=_parse_dh_datetime(detail.get("expireDate")),
        operate_date=_parse_dh_datetime(detail.get("operateDate")),
        last_synced_at=row.last_synced_at,
        sync_state=row.sync_state,
        sync_state_desc=row.sync_state_desc,
        created_at=row.created_at,
        updated_at=row.updated_at,
        img_list=_list_product_img_urls(detail),
        sku_list=sku_list,
        category=_get_product_category(db, cate_pub_id),
        attr_list=_list_product_selected_attrs(detail),
        item_spec_self_def_list=_list_product_spec_self_defs(detail),
    )


def get_dh_product_detail(
    db: Session,
    product_id: int,
) -> DhProductDetailPublic:
    """按本地商品 ID 定位店铺与 item_code，再调 dh.item.get 返回最新详情（不落库）。"""
    row = db.get(ProductDh, product_id)
    if row is None:
        raise not_found("商品不存在")

    client = get_dhgate_client(db, row.store_id)
    detail = get_item(client, item_code=row.item_code, site_id=row.site_id or "EN")
    return _to_dh_product_detail_public(db, row, detail)
