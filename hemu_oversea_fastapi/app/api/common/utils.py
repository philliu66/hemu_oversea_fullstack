"""全局工具类接口（common:utils）。"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

# from app.core.deps import get_current_account
from app.core.db import get_db
from app.core.errors import bad_request
from app.schemas.common import ApiResponse, success
from app.schemas.mail import SendMailPublic, SendMailRequest
from app.schemas.product import DhMeasuresUnitPublic
from app.schemas.utils import (
    DhSkuBaseInfoPublic,
    DhSkuBaseInfoRequest,
    DhgateImgInfoPublic,
    DhgateProductPageFetchPublic,
    DhgateProductPageFetchRequest,
    DhgateTweakImgPublic,
    DhgateUpdateProductFromFilePublic,
    DhgateUpdateProductPublic,
    DhgateUpdateProductRequest,
    DhgateUpdateSkuBaseInfoFromFilePublic,
    FileExtractPublic,
    FileExtractSummaryPublic,
)
from app.services import utils_file as utils_file_service
from app.services.mail import send_email
from app.services.dhgate import (
    get_dhgate_client,
    tweak_product_image,
    upload_product_image,
)
from app.services.dhgate.product_page import fetch_product_page
from app.services.measures_units_dh import list_measures_units_dh
from app.services.product_package_weight import execute_dhgate_product_updates
from app.services.sku_base_infos_dh import (
    SKU_BASE_INFO_REQUIRED_FIELDS,
    get_sku_base_info,
    upsert_sku_base_infos_from_items,
)

router = APIRouter(
    prefix="/utils",
    tags=["common:utils"],
    # dependencies=[Depends(get_current_account)],
)


@router.post(
    "/sendmail",
    response_model=ApiResponse[SendMailPublic],
    summary="发送邮件（阿里云 DirectMail）",
)
def send_mail(payload: SendMailRequest) -> ApiResponse[SendMailPublic]:
    """
    通用发信工具：通过阿里云邮件推送 SingleSendMail 发送单封邮件。

    - 收件人 `to` 支持字符串（逗号分隔）或字符串列表，最多 100 个
    - `html` / `text` 至少传一个
    - 发信地址与 RAM 密钥从环境变量读取，不在请求体中传入
    """
    result = send_email(
        to=payload.to,
        subject=payload.subject,
        html=payload.html,
        text=payload.text,
        from_alias=payload.from_alias,
        tag_name=payload.tag_name,
    )
    return success(
        SendMailPublic(
            ok=result.ok,
            to=result.to,
            subject=result.subject,
            request_id=result.request_id,
            env_id=result.env_id,
        )
    )


@router.post(
    "/getdatafromfile",
    response_model=ApiResponse[FileExtractPublic],
    summary="从 Excel 文件中提取对应的信息",
)
async def get_data_from_file(
    file: UploadFile = File(..., description="Excel 文件（.xlsx / .xlsm）"),
    extract_field_info: str = Form(
        ...,
        description=(
            "提取字段映射（JSON 对象）。键=输出字段名，值=列字母。"
            "商品更新请使用官网字段名："
            '{"itemCode":"B","grossWeight":"C","baseQt":"D","stepQt":"E","stepWeight":"F"}；'
            "其他通用提取仍可自定义键名，如 "
            '{"store_identifier":"A","item_code":"B"}'
        ),
        examples=[
            '{"itemCode":"B","grossWeight":"C","baseQt":"D","stepQt":"E","stepWeight":"F"}'
        ],
    ),
    start_row: int = Form(
        default=2,
        ge=1,
        description="开始提取的行号（1 起）。默认 2=跳过表头；无表头时设为 1",
    ),
    row_count: int = Form(
        default=0,
        ge=0,
        description="计划提取行数。默认 0=从 start_row 起全部；超出实际数据不报错，只返回有效行",
    ),
    sheet_index: int = Form(
        default=1,
        ge=0,
        description="工作表索引：0=读取全部 sheet；1 起为指定 sheet（1=第一个）",
    ),
) -> ApiResponse[FileExtractPublic]:
    """
    通用 Excel 提取工具：按 extract_field_info 从指定 sheet 提取字段。

    - extract_field_info：键名为结果字段名，值为列字母（A/B/C…）
    - 用于敦煌商品更新时，键名须与官网 API 字段一致
      （itemCode / grossWeight / baseQt / stepQt / stepWeight 等）
    - start_row：从该行开始读；默认 2（第 1 行视为表头）
    - row_count：计划提取行数；0=全部；超过文件实际行数不报错
    - 空行，或任一映射字段为空的行会跳过；返回 skipped_rows 汇总
      sheet_index + row_index，便于定位不完整数据
    - sheet_index=0 合并读取全部工作表；>0 仅读取对应序号工作表
    - 响应 row_count=计划提取行数，valid_count=实际有效行数
    """
    content = await file.read()
    data = utils_file_service.extract_rows_from_file(
        file=file,
        content=content,
        extract_field_info=extract_field_info,
        start_row=start_row,
        row_count=row_count,
        sheet_index=sheet_index,
    )
    return success(data)


@router.post(
    "/dhgate/updateproduct",
    response_model=ApiResponse[DhgateUpdateProductPublic],
    summary="敦煌商品更新",
)
def update_dhgate_product(
    payload: DhgateUpdateProductRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[DhgateUpdateProductPublic]:
    """
    批量更新敦煌商品；items 字段名与官网 API 一致。

    流程：
    1. 按 supplier_id 加载该供应商下全部已授权敦煌店铺
    2. 每条 item 用 itemCode 查 product_dh 得到店铺，再取对应 token
    3. dh.item.get → 按入参官网字段改详情 → dh.item.update 原样提交
    4. dry_run=false 时同步写回 product_dh，并写入 product_dh_update_log
       （失败时 error_message 记录官方错误）；dry_run=true 仅试跑不落库

    官方 update 特殊错误：
    - 含「该产品正在参加促销活动」：下架 → 再更新 → 上架
    - 含「不可以做修改操作」：无法官方更新；只改本地库，日志保留官网错误并补充本地变更说明

    当前已支持的包装重量字段：
    itemCode / grossWeight / baseQt / stepQt / stepWeight
    （对应 itemPackage.grossWeight 与 itemPackage.itemWeigthRange）
    """
    data = execute_dhgate_product_updates(
        db,
        supplier_id=payload.supplier_id,
        items=payload.items,
        dry_run=payload.dry_run,
        operator_id=payload.operator_id,
    )
    return success(data)


@router.post(
    "/dhgate/updateproductfromfile",
    response_model=ApiResponse[DhgateUpdateProductFromFilePublic],
    summary="从本地文件中更新商品详情",
)
async def update_dhgate_product_from_file(
    db: Session = Depends(get_db),
    file: UploadFile = File(..., description="Excel 文件（.xlsx / .xlsm）"),
    extract_field_info: str = Form(
        ...,
        description=(
            "提取字段映射（JSON 对象）。键=官网 API 字段名，值=列字母。"
            '示例：{"itemCode":"B","grossWeight":"C","baseQt":"D",'
            '"stepQt":"E","stepWeight":"F"}'
        ),
        examples=[
            '{"itemCode":"B","grossWeight":"C","baseQt":"D","stepQt":"E","stepWeight":"F"}'
        ],
    ),
    start_row: int = Form(
        default=2,
        ge=1,
        description="开始提取的行号（1 起）。默认 2=跳过表头；无表头时设为 1",
    ),
    row_count: int = Form(
        default=0,
        ge=0,
        description="计划提取行数。默认 0=从 start_row 起全部；超出实际数据不报错，只返回有效行",
    ),
    sheet_index: int = Form(
        default=1,
        ge=0,
        description="工作表索引：0=读取全部 sheet；1 起为指定 sheet（1=第一个）",
    ),
    supplier_id: int = Form(..., description="供应商 ID；将加载该供应商下全部敦煌店铺"),
    dry_run: bool = Form(
        default=False,
        description="true=仅试跑不写敦煌/不落库/不记日志；false=真实更新并同步本地与日志",
    ),
    operator_id: int = Form(
        default=0,
        ge=0,
        description="操作人用户 ID；0=系统操作者",
    ),
) -> ApiResponse[DhgateUpdateProductFromFilePublic]:
    """
    从 Excel 提取后直接更新商品（字段名与官网 API 一致）。

    1. 按 extract_field_info 提取 items（键名=官网字段）
    2. get 详情 → 改对应字段 → update 原样提交
    3. 促销中：下架 → 再更新 → 上架；含「不可以做修改操作」：只改本地库并记失败日志

    当前包装重量映射示例：
    itemCode / grossWeight / baseQt / stepQt / stepWeight

    响应含 extract（提取摘要与跳过明细，不含 items）与 update（成功数 / 失败明细）。
    """
    content = await file.read()
    extract = utils_file_service.extract_rows_from_file(
        file=file,
        content=content,
        extract_field_info=extract_field_info,
        start_row=start_row,
        row_count=row_count,
        sheet_index=sheet_index,
    )
    if extract.valid_count <= 0:
        raise bad_request("Excel 中未解析到有效数据行")

    update = execute_dhgate_product_updates(
        db,
        supplier_id=supplier_id,
        items=extract.items,
        dry_run=dry_run,
        operator_id=operator_id,
    )
    return success(
        DhgateUpdateProductFromFilePublic(
            extract=FileExtractSummaryPublic(
                row_count=extract.row_count,
                valid_count=extract.valid_count,
                skipped_count=extract.skipped_count,
                skipped_rows=extract.skipped_rows,
            ),
            update=update,
        )
    )


@router.post(
    "/dhgate/updateskubaseinfofromfile",
    response_model=ApiResponse[DhgateUpdateSkuBaseInfoFromFilePublic],
    summary="从本地文件更新 SKU 基础信息",
)
async def update_dhgate_sku_base_info_from_file(
    db: Session = Depends(get_db),
    file: UploadFile = File(..., description="Excel 文件（.xlsx / .xlsm）"),
    extract_field_info: str = Form(
        ...,
        description=(
            "提取字段映射（JSON 对象）。键=表字段名，值=列字母。"
            "必填：sku_code / sku_series / unit_price；"
            "可选：shipping_template_name / weight_kg / packing_quantity / min_wholesale_qty。"
            '示例：{"sku_code":"B","sku_series":"C","unit_price":"D",'
            '"shipping_template_name":"F","weight_kg":"G",'
            '"packing_quantity":"H","min_wholesale_qty":"I"}'
        ),
        examples=[
            '{"sku_code":"B","sku_series":"C","unit_price":"D",'
            '"shipping_template_name":"F","weight_kg":"G",'
            '"packing_quantity":"H","min_wholesale_qty":"I"}'
        ],
    ),
    start_row: int = Form(
        default=2,
        ge=1,
        description="开始提取的行号（1 起）。默认 2=跳过表头；无表头时设为 1",
    ),
    row_count: int = Form(
        default=0,
        ge=0,
        description="计划提取行数。默认 0=从 start_row 起全部；超出实际数据不报错，只返回有效行",
    ),
    sheet_index: int = Form(
        default=1,
        ge=0,
        description="工作表索引：0=读取全部 sheet；1 起为指定 sheet（1=第一个）",
    ),
    supplier_id: int = Form(
        default=0,
        ge=0,
        description="供应商 ID；默认 0",
    ),
    updated_by: int = Form(
        default=0,
        ge=0,
        description="更新人用户 ID；0=系统，其它值=对应用户 uid",
    ),
) -> ApiResponse[DhgateUpdateSkuBaseInfoFromFilePublic]:
    """
    从本地 Excel 提取后批量 upsert sku_base_info_dh（SKU 基础信息）。

    1. 按 extract_field_info 提取行
    2. 自动去掉售价前缀 `$` 等货币符号后写入 unit_price
    3. 按 supplier_id + sku_code 新建或更新；
       supplier_id / updated_by 由表单传入，默认均为 0（updated_by=0 表示系统）
    4. 物流模板 / 重量 / 打包数 / 起订量可为空（Excel 空单元格写入 null，不跳过该行）

    价格表映射示例（对应截图表头）：
    序号 | 产品型号 | 产品系列 | 售价(DH) | 售价(SMT) | 物流模板 | 重量(kg) | 打包(DH) | 起批量(DH)
    A    | B        | C        | D        | E         | F        | G        | H        | I
    {"sku_code":"B","sku_series":"C","unit_price":"D","shipping_template_name":"F","weight_kg":"G","packing_quantity":"H","min_wholesale_qty":"I"}
    """
    content = await file.read()
    extract = utils_file_service.extract_rows_from_file(
        file=file,
        content=content,
        extract_field_info=extract_field_info,
        start_row=start_row,
        row_count=row_count,
        sheet_index=sheet_index,
        required_fields=SKU_BASE_INFO_REQUIRED_FIELDS,
    )
    if extract.valid_count <= 0:
        raise bad_request("Excel 中未解析到有效数据行")

    update = upsert_sku_base_infos_from_items(
        db,
        items=extract.items,
        supplier_id=supplier_id,
        updated_by=updated_by,
    )
    return success(
        DhgateUpdateSkuBaseInfoFromFilePublic(
            extract=FileExtractSummaryPublic(
                row_count=extract.row_count,
                valid_count=extract.valid_count,
                skipped_count=extract.skipped_count,
                skipped_rows=extract.skipped_rows,
            ),
            update=update,
        )
    )


@router.post(
    "/dhgate/uploadimg",
    response_model=ApiResponse[DhgateImgInfoPublic],
    summary="上传图片到敦煌相册（dh.album.img.upload$2.1）",
)
async def upload_dhgate_image(
    db: Session = Depends(get_db),
    store_id: int = Form(..., description="店铺 ID，用于取该店 access_token"),
    img: UploadFile = File(..., description="上传图片文件（jpg/png 等，最大 2MB）"),
) -> ApiResponse[DhgateImgInfoPublic]:
    """
    直接上传本地图片到敦煌相册，不进行微调。

    表单字段：store_id + img（文件）。
    返回 img_url / img_md5 / type（img_url 不加前缀）。
    """
    image_bytes = await img.read()
    if not image_bytes:
        raise bad_request("上传文件为空")

    client = get_dhgate_client(db, store_id)
    data = upload_product_image(
        client,
        image_bytes=image_bytes,
        image_filename=img.filename,
    )
    return success(DhgateImgInfoPublic.model_validate(data))


@router.post(
    "/dhgate/tweakimg",
    response_model=ApiResponse[DhgateTweakImgPublic],
    summary="微调并上传图片到敦煌相册（dh.album.img.upload$2.1）",
)
async def tweak_dhgate_image(
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
) -> ApiResponse[DhgateTweakImgPublic]:
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
    return success(DhgateTweakImgPublic.model_validate(data))


@router.post(
    "/dhgate/getmeasuresunitlist",
    response_model=ApiResponse[list[DhMeasuresUnitPublic]],
    summary="查询敦煌计件单位列表",
)
def get_dhgate_measures_unit_list(
    db: Session = Depends(get_db),
) -> ApiResponse[list[DhMeasuresUnitPublic]]:
    """
    查询本地 measures_unit_dh 计件单位（默认仅返回 valid=1）。

    数据由 testAPI dh.base.measures.get 同步入库，本接口不请求敦煌。
    """
    return success(list_measures_units_dh(db, valid_only=True))


@router.post(
    "/dhgate/getskubaseinfo",
    response_model=ApiResponse[DhSkuBaseInfoPublic],
    summary="获取 SKU 基础信息",
)
def get_dhgate_sku_base_info(
    payload: DhSkuBaseInfoRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[DhSkuBaseInfoPublic]:
    """
    按 supplier_id + sku_code 查询 sku_base_info_dh。

    sku_code 可原样传入（如 XQ992^）；服务端统一清洗后再查表。
    返回 unit_price、shipping_template_name、weight_kg、packing_quantity、
    min_wholesale_qty 等基础信息字段。
    """
    return success(
        get_sku_base_info(
            db,
            supplier_id=payload.supplier_id,
            sku_code=payload.sku_code,
        )
    )


@router.post(
    "/dhgate/fetchproductrscdata",
    response_model=ApiResponse[DhgateProductPageFetchPublic],
    summary="联调：获取并解析敦煌商品 RSC Flight",
)
def fetch_dhgate_product_rsc_data(
    payload: DhgateProductPageFetchRequest,
) -> ApiResponse[DhgateProductPageFetchPublic]:
    """
    解析敦煌商品详情 RSC Flight。

    - 若传 `flight_content`：优先按该原文解析，服务端不再向上游发起 RSC 请求
      （典型场景：浏览器扩展 background 代拉后回传）。
    - 若仅传 `url`：服务端单次 HTTP GET（`RSC: 1`）取 Flight 再解析。

    返回：
    - `parsed`：标题/价格/类目/店铺/销量/起订/包装/最近修改等
    - `raw`：完整 Flight 原文（仅本联调接口；业务提取接口不返回）
    - `elapsed_ms` / `channel` / `content_type` 等诊断字段

    无需店铺授权；仅供联调，勿对 `blocked` 自动重试。
    """
    data = fetch_product_page(
        payload.url,
        flight_content=payload.flight_content,
        include_raw=True,
    )
    return success(DhgateProductPageFetchPublic.model_validate(data))
