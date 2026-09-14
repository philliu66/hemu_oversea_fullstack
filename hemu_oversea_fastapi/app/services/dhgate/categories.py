"""敦煌 Category API（卖家发布类目）封装。

文档：
- dh.category.list$2.0
  https://open.dhgate.com/docs/api/detail/79dff528fce6490c829476e6063651c5
- dh.category.get$2.0
  https://open.dhgate.com/docs/api/detail/0c39f5a828134110901bbf78356ef1ec
- dh.category.path.get$2.0
  https://open.dhgate.com/docs/api/detail/caf3c526acf54886b29fe82da245248b
"""

from __future__ import annotations

from typing import Any

from app.core.errors import AppError, bad_request
from app.services.dhgate.client import DhgateClient

# 查询无子类目时平台常返回该码 + catePubList=null
_EMPTY_CHILD_STATUS_CODES = frozenset({"00000001"})


def list_category(
    client: DhgateClient,
    *,
    parent_id: str | None = None,
) -> dict[str, Any]:
    """
    按父类目查询发布类目列表。

    method: dh.category.list
    version: 2.0

    parent_id 为空时返回一级类目；可再以返回的 catePubId 作为 parentId 递归查询子类目。
    """
    params: dict[str, str] = {}
    if parent_id is not None and str(parent_id).strip() != "":
        params["parentId"] = str(parent_id).strip()

    return client.call(
        "dh.category.list",
        version="2.0",
        params=params,
        http_method="GET",
    )


def get_category(
    client: DhgateClient,
    *,
    cate_pub_id: str,
) -> dict[str, Any]:
    """
    获取发布类目详情（含属性、属性值、关键词限制等）。

    method: dh.category.get
    version: 2.0

    cate_pub_id 必须是有效叶子类目 ID（来自 dh.category.list）。
    """
    cate_id = str(cate_pub_id or "").strip()
    if not cate_id:
        raise bad_request("cate_pub_id 不能为空（须为叶子发布类目 ID）")

    return client.call(
        "dh.category.get",
        version="2.0",
        params={"catePubId": cate_id},
        http_method="GET",
    )


def get_category_path(
    client: DhgateClient,
    *,
    cate_pub_id: str,
) -> dict[str, Any]:
    """
    获取发布类目从根到当前节点的主线路径。

    method: dh.category.path.get
    version: 2.0

    cate_pub_id 须为有效叶子发布类目 ID；返回 categoryPublishList（由上至下）。
    """
    cate_id = str(cate_pub_id or "").strip()
    if not cate_id:
        raise bad_request("cate_pub_id 不能为空（须为叶子发布类目 ID）")

    return client.call(
        "dh.category.path.get",
        version="2.0",
        params={"catePubId": cate_id},
        http_method="GET",
    )


def _extract_cate_pub_list(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not payload:
        return []
    items = payload.get("catePubList")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _is_empty_child_category_error(exc: AppError) -> bool:
    """平台对无子类目的“空成功”：code=00000001 且 catePubList 为空。"""
    data = exc.data or {}
    code = str(data.get("dhgate_error_code") or "")
    if code in _EMPTY_CHILD_STATUS_CODES:
        return True
    message = (exc.message or "").lower()
    if "null value returned" in message:
        return True
    response = data.get("dhgate_response")
    if isinstance(response, dict) and response.get("catePubList") is None:
        status = response.get("status")
        if isinstance(status, dict) and str(status.get("code") or "") in _EMPTY_CHILD_STATUS_CODES:
            return True
    return False


def list_child_categories(
    client: DhgateClient,
    *,
    parent_id: str | None,
) -> list[dict[str, Any]]:
    """查询子类目；若平台返回空结果（已到最底层），视为无子类目并跳过。"""
    try:
        payload = list_category(client, parent_id=parent_id)
    except AppError as exc:
        if _is_empty_child_category_error(exc):
            return []
        raise
    return _extract_cate_pub_list(payload)


def list_all_categories(client: DhgateClient) -> list[dict[str, Any]]:
    """
    从根类目递归拉取全部发布类目，汇总为平级 list。

    规则：
    1. 首次 parentId 为空，取一级类目
    2. 对 leaf != \"1\" 的节点，以 catePubId 作为 parentId 继续查询
    3. 子类目为空（含平台 00000001 / catePubList=null）视为已到最底层，跳过
    4. 全程去重后扁平返回

    原始调用明细由 client.call_history / last_raw 提供。
    """
    flat: list[dict[str, Any]] = []
    visited: set[str] = set()

    def walk(parent_id: str | None) -> None:
        children = list_child_categories(client, parent_id=parent_id)
        for item in children:
            cate_id = str(item.get("catePubId") or "").strip()
            if cate_id:
                if cate_id in visited:
                    continue
                visited.add(cate_id)
            flat.append(item)

            if str(item.get("leaf")) == "1":
                continue
            if cate_id:
                walk(cate_id)

    walk(None)
    return flat
