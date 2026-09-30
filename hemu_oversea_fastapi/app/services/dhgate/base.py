"""敦煌 Basic API（基础模块）封装。

文档：https://open.dhgate.com/docs/api/001002
"""

from __future__ import annotations

from typing import Literal

from app.core.errors import bad_request
from app.services.dhgate.client import DhgateClient

ThirdType = Literal["brand", "other"]


def list_punish_brand(
    client: DhgateClient,
    *,
    third_type: ThirdType,
    page_no: int,
    page_size: int,
) -> dict:
    """
    查询卖家处罚信息第三方投诉接口。

    method: dh.punish.brand.list.get
    version: 1.0
    """
    if third_type not in ("brand", "other"):
        raise bad_request("third_type 仅支持 brand（品牌商投诉）或 other（其他第三方投诉）")
    if page_no < 1:
        raise bad_request("page_no 不能小于 1")
    if page_size < 1 or page_size > 200:
        raise bad_request("page_size 须在 1～200 之间")

    return client.call(
        "dh.punish.brand.list.get",
        version="1.0",
        params={
            "thirdType": third_type,
            "pageNo": page_no,
            "pageSize": page_size,
        },
        http_method="GET",
    )


def list_punish(
    client: DhgateClient,
    *,
    start_date: str,
    end_date: str,
    page_no: int,
    page_size: int,
    punish_id: str | None = None,
) -> dict:
    """
    查询卖家处罚信息接口。

    method: dh.punish.list.get
    version: 1.0
    """
    if not start_date:
        raise bad_request("start_date 不能为空")
    if not end_date:
        raise bad_request("end_date 不能为空")
    if page_no < 1:
        raise bad_request("page_no 不能小于 1")
    if page_size < 1 or page_size > 200:
        raise bad_request("page_size 须在 1～200 之间")

    params: dict[str, str | int] = {
        "startDate": start_date,
        "endDate": end_date,
        "pageNo": page_no,
        "pageSize": page_size,
    }
    if punish_id:
        params["punishId"] = punish_id

    return client.call(
        "dh.punish.list.get",
        version="1.0",
        params=params,
        http_method="GET",
    )


def list_measures(client: DhgateClient) -> dict:
    """
    获取计件单位列表。

    method: dh.base.measures.get
    version: 1.0
    文档字段名为 meauserList（官方拼写）。
    """
    return client.call(
        "dh.base.measures.get",
        version="1.0",
        params={},
        http_method="POST",
    )
