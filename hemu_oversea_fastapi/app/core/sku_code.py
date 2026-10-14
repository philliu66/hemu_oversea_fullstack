"""SKU 编码清洗工具（统一入口）。"""

from __future__ import annotations

import re

# 字母+数字，可选紧跟 -数字；其后特殊字符等截断
# 例：XQ992^ → XQ992；TN101-1 → TN101-1；MK241&#039; → MK241
_SKU_SPEC_MODEL_RE = re.compile(r"^[A-Za-z]+[0-9]+(?:-[0-9]+)?")

# 变体型号：基型号后紧跟 -数字（如 BD001-1）；列表下拉只展示基型号 BD001
_SKU_VARIANT_RE = re.compile(r"^[A-Za-z]+[0-9]+-[0-9]+$")
# PostgreSQL ~ 用：与 _SKU_VARIANT_RE 同义
SKU_VARIANT_PG_REGEX = r"^[A-Za-z]+[0-9]+-[0-9]+$"


def is_sku_variant_code(sku_code: str | None) -> bool:
    """是否为同型号变体编码（如 BD001-1），基型号 BD001 返回 False。"""
    text = str(sku_code or "").strip()
    if not text:
        return False
    return _SKU_VARIANT_RE.match(text) is not None


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


def to_base_sku_code(sku_code: str | None) -> str:
    """
    归类为基型号：先 normalize_sku_code，再去掉尾部 -数字变体后缀。

    例：BD001 / BD001-1 / BD001*' → BD001
    """
    code = normalize_sku_code(sku_code)
    if not code:
        return ""
    return re.sub(r"-\d+$", "", code)
