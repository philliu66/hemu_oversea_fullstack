"""全局工具类接口相关请求 / 响应。"""

from pydantic import BaseModel, Field


class DhgateImgInfoPublic(BaseModel):
    """敦煌相册图片信息（img_url 不加前缀）。"""

    img_url: str | None = Field(default=None, description="官方 imgUrl，相对路径")
    img_md5: str | None = Field(default=None, description="官方 imgMd5")
    type: str | None = Field(default=None, description="官方 type")


class DhgateUploadImgPublic(BaseModel):
    """微调并上传后的原图 / 现图。"""

    original: DhgateImgInfoPublic = Field(description="微调前的原图片")
    tweaked: DhgateImgInfoPublic = Field(description="微调并上传后的现图片")


class FileProductSyncRow(BaseModel):
    store_identifier: str = Field(description="店铺标识（stores.identifier）")
    item_code: str = Field(description="商品编码 itemCode")


class FileProductSyncExtractPublic(BaseModel):
    items: list[FileProductSyncRow] = Field(
        default_factory=list,
        description="从文件中提取的店铺标识 + 商品编码列表",
    )
    row_count: int = Field(description="有效数据行数")
