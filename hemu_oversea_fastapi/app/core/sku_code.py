"""SKU 编码清洗工具（统一入口）。"""

from __future__ import annotations

import re

# 字母+数字，可选紧跟 -数字；其后特殊字符等截断
# 例：XQ992^ → XQ992；TN101-1 → TN101-1；MK241&#039; → MK241
_SKU_SPEC_MODEL_RE = re.compile(r"^[A-Za-z]+[0-9]+(?:-[0-9]+)?")


def normalize_sku_code(sku_code: str | None) -> str:
    """
    清洗 SKU 编码型号，供查询 / 入库前统一调用。

    - 去首尾空白
    - 仅保留开头合法型号段（字母+数字，可选 -数字）
    - 无法匹配时回退为去空白后的原文
    """
    text = str(sku_code or "").strip()
    if not text:
        return ""
    matched = _SKU_SPEC_MODEL_RE.match(text)
    return matched.group(0) if matched else text
