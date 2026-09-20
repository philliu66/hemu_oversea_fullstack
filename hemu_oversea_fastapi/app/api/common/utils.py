"""全局工具类接口（common:utils）。"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

# from app.core.deps import get_current_account
from app.core.db import get_db
from app.core.errors import bad_request
from app.schemas.common import ApiResponse, success
from app.schemas.utils import (
    DhgateUploadImgPublic,
    FileProductSyncExtractPublic,
)
from app.services import utils_file as utils_file_service
from app.services.dhgate import get_dhgate_client, tweak_product_image

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


@router.post(
    "/dhgate/uploadimg",
    response_model=ApiResponse[DhgateUploadImgPublic],
    summary="微调并上传图片到敦煌相册（dh.album.img.upload$2.1）",
)
async def upload_dhgate_image(
    db: Session = Depends(get_db),
    store_id: int = Form(..., description="店铺 ID，用于取该店 access_token"),
    img_url: str | None = Form(
        default=None,
        description="当前图片官方 imgUrl（相对路径或完整 URL）；有值则按该图微调",
    ),
    img_md5: str | None = Form(
        default=None,
        description="当前图片官方 imgMd5，原样回传到 original",
    ),
    type: str | None = Form(
        default=None,
        description="当前图片官方 type，原样回传到 original / tweaked",
    ),
    img_base64: UploadFile | None = File(
        default=None,
        description="图片文件（接口内转 base64）；未传 img_url 时必填",
    ),
) -> ApiResponse[DhgateUploadImgPublic]:
    """
    使用与联调 item/img/tweak 相同的微调服务，再调用 dh.album.img.upload。

    返回 original（原图）与 tweaked（微调后），img_url / img_md5 / type 均不加前缀。
    """
    source_url = str(img_url or "").strip() or None
    image_bytes: bytes | None = None
    image_filename: str | None = None
    if img_base64 is not None:
        image_bytes = await img_base64.read()
        if not image_bytes:
            raise bad_request("上传文件为空")
        image_filename = img_base64.filename
    if not source_url and not image_bytes:
        raise bad_request("请上传 img_base64 文件，或传入 img_url")

    client = get_dhgate_client(db, store_id)
    data = tweak_product_image(
        client,
        image_url=source_url,
        image_bytes=None if source_url else image_bytes,
        image_filename=image_filename,
        original_img_url=source_url,
        original_img_md5=str(img_md5 or "").strip() or None,
        original_type=str(type or "").strip() or None,
    )
    return success(DhgateUploadImgPublic.model_validate(data))
