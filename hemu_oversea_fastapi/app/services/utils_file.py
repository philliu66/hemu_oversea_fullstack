"""全局工具：文件解析（Excel 等）。"""

from __future__ import annotations

import re
from io import BytesIO

from fastapi import UploadFile
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.worksheet.worksheet import Worksheet

from app.core.errors import bad_request
from app.schemas.utils import FileProductSyncExtractPublic, FileProductSyncRow

_COL_LETTER_RE = re.compile(r"^[A-Za-z]{1,3}$")
_ALLOWED_EXCEL_SUFFIXES = (".xlsx", ".xlsm")


def _normalize_col_letter(value: str, *, field_name: str) -> str:
    text = str(value or "").strip().upper()
    if not text or not _COL_LETTER_RE.fullmatch(text):
        raise bad_request(f"{field_name} 须为 Excel 列字母，如 A / B / AA")
    try:
        column_index_from_string(text)
    except ValueError as exc:
        raise bad_request(f"{field_name} 不是有效的列字母：{text}") from exc
    return text


def _cell_to_str(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        text = format(value, "f").rstrip("0").rstrip(".")
        return text
    text = str(value).strip()
    if re.fullmatch(r"\d+\.0+", text):
        return text.split(".", 1)[0]
    return text


def _extract_rows_from_sheet(
    sheet: Worksheet,
    *,
    store_idx: int,
    item_idx: int,
    start_row: int,
) -> list[FileProductSyncRow]:
    items: list[FileProductSyncRow] = []
    for row in sheet.iter_rows(min_row=start_row, values_only=True):
        store_val = _cell_to_str(
            row[store_idx - 1] if len(row) >= store_idx else None
        )
        item_val = _cell_to_str(
            row[item_idx - 1] if len(row) >= item_idx else None
        )
        if not store_val or not item_val:
            continue
        items.append(
            FileProductSyncRow(
                store_identifier=store_val,
                item_code=item_val,
            )
        )
    return items


def extract_product_sync_rows_from_file(
    *,
    file: UploadFile,
    store_col: str,
    item_code_col: str,
    content: bytes,
    has_header: bool = True,
    sheet_index: int = 1,
) -> FileProductSyncExtractPublic:
    """
    从 Excel 表格按列字母提取店铺标识与商品编码。

    - 支持 .xlsx / .xlsm
    - 空行、任一字段为空的行会跳过
    - has_header=True 时每个 sheet 都跳过第一行表头
    - sheet_index=0 读取全部工作表；>=1 为从 1 开始的工作表序号
    """
    store_letter = _normalize_col_letter(store_col, field_name="store_col")
    item_letter = _normalize_col_letter(item_code_col, field_name="item_code_col")
    if store_letter == item_letter:
        raise bad_request("store_col 与 item_code_col 不能为同一列")
    if sheet_index < 0:
        raise bad_request("sheet_index 不能为负数（0=全部，1 起为指定工作表）")

    filename = (file.filename or "").strip().lower()
    if not filename.endswith(_ALLOWED_EXCEL_SUFFIXES):
        raise bad_request("仅支持 .xlsx / .xlsm 格式的 Excel 文件")

    if not content:
        raise bad_request("上传文件为空")

    store_idx = column_index_from_string(store_letter)
    item_idx = column_index_from_string(item_letter)
    start_row = 2 if has_header else 1

    try:
        workbook = load_workbook(
            filename=BytesIO(content),
            read_only=True,
            data_only=True,
        )
    except InvalidFileException as exc:
        raise bad_request("无法解析 Excel 文件，请确认文件未损坏且为 xlsx/xlsm") from exc
    except Exception as exc:  # noqa: BLE001
        raise bad_request(f"读取 Excel 失败：{exc}") from exc

    try:
        sheets = list(workbook.worksheets)
        if not sheets:
            raise bad_request("Excel 中没有可用的工作表")

        if sheet_index == 0:
            target_sheets = sheets
        else:
            if sheet_index > len(sheets):
                raise bad_request(
                    f"sheet_index={sheet_index} 超出范围，当前文件共 {len(sheets)} 个工作表"
                )
            target_sheets = [sheets[sheet_index - 1]]

        items: list[FileProductSyncRow] = []
        for sheet in target_sheets:
            items.extend(
                _extract_rows_from_sheet(
                    sheet,
                    store_idx=store_idx,
                    item_idx=item_idx,
                    start_row=start_row,
                )
            )
    finally:
        workbook.close()

    return FileProductSyncExtractPublic(items=items, row_count=len(items))
