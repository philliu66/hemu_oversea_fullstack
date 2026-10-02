"""全局工具类接口相关请求 / 响应。"""

from pydantic import BaseModel, Field


class DhgateImgInfoPublic(BaseModel):
    """敦煌相册图片信息（img_url 不加前缀）。"""

    img_url: str | None = Field(default=None, description="官方 imgUrl，相对路径")
    img_md5: str | None = Field(default=None, description="官方 imgMd5")
    type: str | None = Field(default=None, description="官方 type")


class DhgateTweakImgPublic(BaseModel):
    """微调并上传后的原图 / 现图。"""

    original: DhgateImgInfoPublic = Field(description="微调前的原图片")
    tweaked: DhgateImgInfoPublic = Field(description="微调并上传后的现图片")


# 兼容旧名称
DhgateUploadImgPublic = DhgateTweakImgPublic


class FileExtractSkippedRow(BaseModel):
    """被跳过的行定位信息。"""

    sheet_index: int = Field(description="工作表序号（从 1 起，与入参 sheet_index 口径一致）")
    row_index: int = Field(description="行号（从 1 起，Excel 行号）")
    reason: str = Field(description="跳过原因：empty_row / missing_fields")
    missing_fields: list[str] = Field(
        default_factory=list,
        description="缺失的映射字段名（empty_row 时为全部映射字段）",
    )


class FileExtractPublic(BaseModel):
    """从 Excel 按字段映射提取出的通用结果。"""

    items: list[dict[str, str]] = Field(
        default_factory=list,
        description=(
            "提取出的数据行；每行键名与 extract_field_info 的键一致。"
            "用于敦煌商品更新时，键名须与官网 API 字段一致"
            "（如 itemCode / grossWeight / baseQt / stepQt / stepWeight）"
        ),
    )
    row_count: int = Field(
        description="本次计划提取行数（入参回显；0 表示提取全部）",
    )
    valid_count: int = Field(description="实际提取到的有效数据行数")
    skipped_count: int = Field(
        default=0,
        description="跳过行数（空行或任一映射字段为空）",
    )
    skipped_rows: list[FileExtractSkippedRow] = Field(
        default_factory=list,
        description="跳过明细：sheet 索引 + 行索引，便于定位不完整数据",
    )


class DhgateUpdateProductRequest(BaseModel):
    """敦煌商品批量更新（items 字段名与官网 API 一致）。"""

    supplier_id: int = Field(description="供应商 ID；将加载该供应商下全部敦煌店铺")
    items: list[dict[str, str]] = Field(
        description=(
            "待更新商品列表；字段名与官网一致。"
            "包装重量示例："
            '{"itemCode":"211198221","grossWeight":"0.5","baseQt":"1",'
            '"stepQt":"1","stepWeight":"0.1"}'
        ),
        min_length=1,
    )
    dry_run: bool = Field(
        default=False,
        description="true=仅试跑不写敦煌/不落库/不记日志；false=真实更新并同步本地与日志",
    )
    operator_id: int = Field(
        default=0,
        ge=0,
        description="操作人用户 ID；0=系统操作者",
    )


class DhgateUpdateProductFailedItem(BaseModel):
    itemCode: str = Field(default="", description="商品编码 itemCode")
    store_id: int | None = Field(default=None, description="解析到的店铺 ID（本地）")
    error_message: str = Field(description="失败原因（含敦煌官方错误）")
    log_id: int | None = Field(default=None, description="写入的变更日志 ID")


class DhgateUpdateProductPublic(BaseModel):
    supplier_id: int
    dry_run: bool
    success_count: int = Field(description="操作成功条数")
    failed_count: int = Field(description="操作失败条数")
    failed_items: list[DhgateUpdateProductFailedItem] = Field(
        default_factory=list,
        description="失败明细",
    )


class FileExtractSummaryPublic(BaseModel):
    """文件提取摘要（不含 items 明细，用于合并更新接口响应）。"""

    row_count: int = Field(
        description="本次计划提取行数（入参回显；0 表示提取全部）",
    )
    valid_count: int = Field(description="实际提取到的有效数据行数")
    skipped_count: int = Field(
        default=0,
        description="跳过行数（空行或任一映射字段为空）",
    )
    skipped_rows: list[FileExtractSkippedRow] = Field(
        default_factory=list,
        description="跳过明细：sheet 索引 + 行索引，便于定位不完整数据",
    )


class DhgateUpdateProductFromFilePublic(BaseModel):
    """从 Excel 提取后直接更新商品的合并结果。"""

    extract: FileExtractSummaryPublic = Field(
        description="文件提取摘要（不含 items）"
    )
    update: DhgateUpdateProductPublic = Field(description="商品更新结果")
