"""敦煌多店铺编排联调（仅调试）。

路径：/api/v1/common/testAPI/dhgate/commerce
用于验证敦煌店铺多店汇总 / 同步逻辑，非正式业务接口。
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
# from app.core.deps import get_current_account
from app.core.errors import bad_request
from app.schemas.common import ApiResponse, success
from app.schemas.test_api.commerce import (
    ProductSyncTestRequest,
    PunishSummaryTestRequest,
)
from app.services import utils_file as utils_file_service
from app.services.commerce import summarize_supplier_punish
from app.services.products_dh import (
    find_missing_product_sync_items,
    summarize_sync_result,
    sync_products_dh,
)

router = APIRouter(
    prefix="/dhgate/commerce",
    tags=["common:testAPI:dhgate"],
    # dependencies=[Depends(get_current_account)],
)


@router.post(
    "/punish/summary",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] 敦煌多店铺处罚信息汇总",
)
def test_punish_summary(
    payload: PunishSummaryTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """敦煌店铺多店处罚信息汇总（供应商下多店 / 指定单店）。"""
    summary = summarize_supplier_punish(
        db,
        supplier_id=payload.supplier_id,
        store_id=payload.store_id,
        query_days=payload.query_days,
        page_no=payload.page_no,
        page_size=payload.page_size,
    )
    return success(asdict(summary))


@router.post(
    "/product/sync",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] 敦煌多店铺商品详情同步入库",
)
def test_product_sync(
    payload: ProductSyncTestRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    按 store_identifier + item_code 批量拉取 dh.item.get 并写入 product_dh 及相关子表。

    - store_identifier 对应 stores.identifier，内部解析店铺与 access_token
    - 可跨店铺一次传入多个商品
    - site_id 默认 EN
    - 同步成功的商品 is_seed=1
    - 单条失败不中断整批
    """
    result = sync_products_dh(
        db,
        items=[item.model_dump() for item in payload.items],
    )
    return success(result)


@router.post(
    "/product/syncfromfile",
    response_model=ApiResponse[dict[str, Any]],
    summary="[联调] 从 Excel 提取后多店铺商品详情同步入库",
)
async def test_product_sync_from_file(
    db: Session = Depends(get_db),
    file: UploadFile = File(..., description="Excel 文件（.xlsx / .xlsm）"),
    store_col: str = Form(
        ...,
        min_length=1,
        max_length=3,
        description="店铺标识列字母索引，如 A",
        examples=["A"],
    ),
    item_code_col: str = Form(
        ...,
        min_length=1,
        max_length=3,
        description="商品 item_code 列字母索引，如 B",
        examples=["B"],
    ),
    has_header: bool = Form(
        default=True,
        description="是否含表头：true 跳过第一行（默认），false 从第一行起读",
    ),
    sheet_index: int = Form(
        default=1,
        ge=0,
        description="工作表索引：0=读取全部 sheet；1 起为指定 sheet（1=第一个）",
    ),
    is_autocheck: int = Form(
        default=0,
        ge=0,
        le=1,
        description="是否自动检查遗漏：0=否（同步全部提取行），1=是（仅同步库中不存在的商品）",
    ),
) -> ApiResponse[dict[str, Any]]:
    """
    合并流程：
    1. 按 getdatafromfile 相同参数从 Excel 提取 items
    2. is_autocheck=0：对全部提取行执行同步入库
    3. is_autocheck=1：先检查 item_code（按店铺）是否已在 product_dh，
       仅对遗漏项自动落库，并返回遗漏明细

    响应仅返回简要统计：成功数、失败数、遗漏补充数及遗漏列表。
    """
    content = await file.read()
    extract = utils_file_service.extract_product_sync_rows_from_file(
        file=file,
        store_col=store_col,
        item_code_col=item_code_col,
        content=content,
        has_header=has_header,
        sheet_index=sheet_index,
    )
    if extract.row_count <= 0:
        raise bad_request("Excel 中未解析到有效的店铺标识与商品编码")

    all_items = [row.model_dump() for row in extract.items]
    missing_items: list[dict[str, str]] = []
    if is_autocheck == 1:
        missing_items = find_missing_product_sync_items(db, items=all_items)
        sync_items = missing_items
    else:
        sync_items = all_items

    if not sync_items:
        return success(
            {
                "success_count": 0,
                "failed_count": 0,
                "missing_count": 0,
                "missing_items": [],
            }
        )

    sync_result = sync_products_dh(db, items=sync_items)
    return success(
        summarize_sync_result(
            sync_result,
            missing_items=missing_items if is_autocheck == 1 else None,
        )
    )
