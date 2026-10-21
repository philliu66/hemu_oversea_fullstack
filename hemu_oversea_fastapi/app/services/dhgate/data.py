"""敦煌 Data API / 增值广告报表封装。

文档：https://open.dhgate.com/docs/api
手册对照：hemu_oversea_fastapi/dhgate_API.md
- 数据 API(限免)：dh.wis.core.info / dh.wis.detail.page / dh.wis.keywordtop10.info
- 增值 API：dh.seller.ad.*.report.page
"""

from __future__ import annotations

from typing import Any

from app.core.errors import bad_request
from app.services.dhgate.client import DhgateClient


def get_wis_core_info(
    client: DhgateClient,
    *,
    period_type: str,
    site: str,
    end_date: str,
    country_id: str,
    stat_date: str,
) -> dict[str, Any]:
    """
    「数据概览」页核心指标数据下载。

    method: dh.wis.core.info
    version: 1.0
    必填：periodType、site、endDate、countryId、statDate
    取值：periodType=DAY|L7|L30|WEEK|MON；site=TOTAL|app|unapp；countryId 示例 TOTAL

    返回：
    - list：核心经营指标列表（WisCoreDTO[]）
    """
    period = str(period_type or "").strip()
    site_val = str(site or "").strip()
    end = str(end_date or "").strip()
    country = str(country_id or "").strip()
    stat = str(stat_date or "").strip()
    if not period:
        raise bad_request("period_type 不能为空")
    if not site_val:
        raise bad_request("site 不能为空")
    if not end:
        raise bad_request("end_date 不能为空")
    if not country:
        raise bad_request("country_id 不能为空")
    if not stat:
        raise bad_request("stat_date 不能为空")

    return client.call(
        "dh.wis.core.info",
        version="1.0",
        params={
            "periodType": period,
            "site": site_val,
            "endDate": end,
            "countryId": country,
            "statDate": stat,
        },
        http_method="POST",
        timeout=30.0,
    )


def get_wis_detail_page(
    client: DhgateClient,
    *,
    end_date: str,
    stat_date: str,
    site: str,
    page_no: int,
    page_size: int,
    period_type: str | None = None,
) -> dict[str, Any]:
    """
    「商品分析-产品详情」页数据下载。

    method: dh.wis.detail.page
    version: 1.0
    必填：endDate、statDate、site、pageNo、pageSize；可选 periodType
    取值：site=PC|APP|WAP|all；periodType=DAY|L7|L30|WEEK|MON

    返回：
    - list：产品维度分析数据（WisProdDetailDTO[]）
    - count：总量
    """
    end = str(end_date or "").strip()
    stat = str(stat_date or "").strip()
    site_val = str(site or "").strip()
    if not end:
        raise bad_request("end_date 不能为空")
    if not stat:
        raise bad_request("stat_date 不能为空")
    if not site_val:
        raise bad_request("site 不能为空")
    if page_no < 1:
        raise bad_request("page_no 不能小于 1")
    if page_size < 1 or page_size > 200:
        raise bad_request("page_size 须在 1～200 之间")

    params: dict[str, Any] = {
        "endDate": end,
        "statDate": stat,
        "site": site_val,
        "pageNo": page_no,
        "pageSize": page_size,
    }
    period = str(period_type or "").strip()
    if period:
        params["periodType"] = period

    return client.call(
        "dh.wis.detail.page",
        version="1.0",
        params=params,
        http_method="POST",
        timeout=60.0,
    )


def get_wis_keywordtop10_info(
    client: DhgateClient,
    *,
    platform_id: str,
    search_date_type: int,
    item_code: int | str,
    site_id: str,
) -> dict[str, Any]:
    """
    「关键词 TOP」数据下载。

    method: dh.wis.keywordtop10.info
    version: 1.0
    必填：platformId、searchDateType、itemCode、siteId
    说明：官网参数「说明」列对 itemCode 等可能有笔误；按字段名联调
          （itemCode=产品编码，siteId 示例 EN，platformId 示例 ALL）。

    返回：
    - list：WisProdKwordsTop10DTO[]
    """
    platform = str(platform_id or "").strip()
    site = str(site_id or "").strip()
    code_raw = str(item_code or "").strip()
    if not platform:
        raise bad_request("platform_id 不能为空")
    if not site:
        raise bad_request("site_id 不能为空")
    if not code_raw:
        raise bad_request("item_code 不能为空")
    try:
        code = int(code_raw)
    except ValueError as exc:
        raise bad_request("item_code 须为数字型产品编码") from exc

    return client.call(
        "dh.wis.keywordtop10.info",
        version="1.0",
        params={
            "platformId": platform,
            "searchDateType": int(search_date_type),
            "itemCode": code,
            "siteId": site,
        },
        http_method="POST",
        timeout=30.0,
    )


def list_seller_ad_order_report(
    client: DhgateClient,
    *,
    ad_type: str,
    itemcode: str,
    dateline_from: str,
    dateline_to: str,
    page: int,
    limit: int,
) -> dict[str, Any]:
    """
    查询卖家广告消耗列表（订单维度）。

    method: dh.seller.ad.order.report.page
    version: 1.0
    必填：adType、itemcode、datelineFrom、datelineTo、page、limit

    返回：
    - sellerAdOrderReportList / count / pages
    """
    return _call_seller_ad_report(
        client,
        method="dh.seller.ad.order.report.page",
        ad_type=ad_type,
        itemcode=itemcode,
        dateline_from=dateline_from,
        dateline_to=dateline_to,
        page=page,
        limit=limit,
    )


def list_seller_ad_prod_report(
    client: DhgateClient,
    *,
    ad_type: str,
    itemcode: str,
    dateline_from: str,
    dateline_to: str,
    page: int,
    limit: int,
) -> dict[str, Any]:
    """
    查询卖家广告消耗列表（产品维度）。

    method: dh.seller.ad.prod.report.page
    version: 1.0
    必填：adType、itemcode、datelineFrom、datelineTo、page、limit

    返回：
    - sellerAdProdReportList / count / pages
    """
    return _call_seller_ad_report(
        client,
        method="dh.seller.ad.prod.report.page",
        ad_type=ad_type,
        itemcode=itemcode,
        dateline_from=dateline_from,
        dateline_to=dateline_to,
        page=page,
        limit=limit,
    )


def _call_seller_ad_report(
    client: DhgateClient,
    *,
    method: str,
    ad_type: str,
    itemcode: str,
    dateline_from: str,
    dateline_to: str,
    page: int,
    limit: int,
) -> dict[str, Any]:
    # 官方：adType 必传字段，空字符串=所有广告
    ad = "" if ad_type is None else str(ad_type).strip()
    code = str(itemcode or "").strip()
    start = str(dateline_from or "").strip()
    end = str(dateline_to or "").strip()
    if not code:
        raise bad_request("itemcode 不能为空")
    if not start:
        raise bad_request("dateline_from 不能为空")
    if not end:
        raise bad_request("dateline_to 不能为空")
    if page < 1:
        raise bad_request("page 不能小于 1")
    if limit < 1 or limit > 200:
        raise bad_request("limit 须在 1～200 之间")

    return client.call(
        method,
        version="1.0",
        params={
            "adType": ad,
            "itemcode": code,
            "datelineFrom": start,
            "datelineTo": end,
            "page": page,
            "limit": limit,
        },
        http_method="POST",
        timeout=15.0,
    )
