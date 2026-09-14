"""全局工具类接口（common:utils）。"""

from fastapi import APIRouter, File, Form, UploadFile

# from app.core.deps import get_current_account
from app.schemas.common import ApiResponse, success
from app.schemas.utils import FileProductSyncExtractPublic
from app.services import utils_file as utils_file_service

router = APIRouter(
    prefix="/utils",
    tags=["common:utils"],
    # dependencies=[Depends(get_current_account)],
)


@router.post(
    "/getdatafromfile",
    response_model=ApiResponse[FileProductSyncExtractPublic],
    summary="从 Excel 文件提取店铺标识与商品编码",
)
async def get_data_from_file(
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
) -> ApiResponse[FileProductSyncExtractPublic]:
    """
    上传 Excel，按列字母提取「店铺标识 + 商品编码」列表，
    供后续批量同步敦煌商品使用。

    空行或任一字段为空的行会跳过。
    sheet_index=0 合并读取全部工作表；>0 仅读取对应序号工作表。
    """
    content = await file.read()
    data = utils_file_service.extract_product_sync_rows_from_file(
        file=file,
        store_col=store_col,
        item_code_col=item_code_col,
        content=content,
        has_header=has_header,
        sheet_index=sheet_index,
    )
    return success(data)
