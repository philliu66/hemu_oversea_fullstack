"""全局工具类接口相关请求 / 响应。"""

from pydantic import BaseModel, Field


class FileProductSyncRow(BaseModel):
    store_identifier: str = Field(description="店铺标识（stores.identifier）")
    item_code: str = Field(description="商品编码 itemCode")


class FileProductSyncExtractPublic(BaseModel):
    items: list[FileProductSyncRow] = Field(
        default_factory=list,
        description="从文件中提取的店铺标识 + 商品编码列表",
    )
    row_count: int = Field(description="有效数据行数")
