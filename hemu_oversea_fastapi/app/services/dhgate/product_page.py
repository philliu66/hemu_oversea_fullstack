"""敦煌商品详情页 RSC Flight 取数与解析（公开商品页，无需登录）。

规范见：docs/敦煌商品详情信息提取文档.md
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.core.errors import bad_request

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

BLOCK_MARKS = ("TCaptcha", "captcha", "访问验证", "安全验证", "punish")
ALLOWED_HOSTS = frozenset({"www.dhgate.com", "dhgate.com"})
_FETCH_TIMEOUT = 20.0


def assert_dhgate_product_url(url: str) -> str:
    """SSRF 防护：必须 https，且 hostname 在白名单。返回 strip 后的 url。"""
    raw = (url or "").strip()
    if not raw:
        raise bad_request("请提供敦煌商品链接")
    try:
        parsed = urlsplit(raw)
    except Exception as exc:
        raise bad_request("商品链接无效") from exc
    if parsed.scheme != "https":
        raise bad_request("商品链接须为 https")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in ALLOWED_HOSTS:
        raise bad_request("仅支持 www.dhgate.com / dhgate.com 商品链接")
    return raw


def _json_all(buf: str, key: str, want: type) -> Any | None:
    """同一 key 可能多次出现：首次常为引用指针 \"$62\"，取第一个类型匹配的真值。"""
    dec = json.JSONDecoder()
    for m in re.finditer(rf'"{re.escape(key)}"\s*:\s*', buf):
        try:
            val, _ = dec.raw_decode(buf, m.end())
        except Exception:
            continue
        if isinstance(val, want):
            return val
    return None


def _blocks(buf: str) -> dict[str, Any]:
    """flight 数据块：'5b:{...}' / '5b:[...]'，按行切分。"""
    out: dict[str, Any] = {}
    for line in buf.split("\n"):
        m = re.match(r"^([0-9a-f]{1,4}):(.*)$", line, re.S)
        if not m or not m.group(2).startswith(("{", "[")):
            continue
        try:
            out[m.group(1)] = json.loads(m.group(2))
        except Exception:
            pass
    return out


def flight_from_html(html: str) -> str:
    """降级：从 HTML 中 self.__next_f.push([1,\"...\"]) 还原 flight 文本。"""
    parts: list[str] = []
    for chunk in re.findall(
        r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)',
        html,
    ):
        try:
            parts.append(json.loads(chunk))
        except Exception:
            pass
    return "".join(parts)


def _resolve_ref(value: Any, blocks: dict[str, Any]) -> Any:
    """解析 Flight 引用指针，如 \"$62\" → blocks['62']。"""
    if isinstance(value, str) and value.startswith("$"):
        ref = value[1:]
        if ref in blocks:
            return blocks[ref]
    return value


def parse_flight(buf: str) -> dict[str, Any]:
    """输入 flight 文本，输出标题/价格/分类/店铺等结构化字段。"""
    blocks = _blocks(buf)

    product: dict[str, Any] = {}
    for block in blocks.values():
        if isinstance(block, dict) and block.get("itemCode") and block.get("productName"):
            product = block
            break

    seller = _json_all(buf, "prodSeller", dict) or {}
    seller = _resolve_ref(seller, blocks) if isinstance(seller, str) else seller
    if not isinstance(seller, dict):
        seller = {}
    if not seller.get("suppliername"):
        pid = product.get("supplierId")
        for block in blocks.values():
            if (
                isinstance(block, dict)
                and block.get("suppliername")
                and pid
                and block.get("supplierid") == pid
            ):
                seller = block
                break

    def _ladder_dicts_from(value: Any) -> list[dict[str, Any]]:
        """把 vos 值规范成价档 dict 列表。

        真实 Flight 可能是：
        - \"$6c\" → [\"$6d\", \"$6e\"]（元素仍是引用）
        - 或直接 [{\"startQty\":1,\"originalPrice\":10}, ...]
        """
        value = _resolve_ref(value, blocks)
        if not isinstance(value, list):
            return []
        out: list[dict[str, Any]] = []
        for item in value:
            item = _resolve_ref(item, blocks)
            if isinstance(item, dict):
                out.append(item)
        return out

    # 阶梯价：遍历所有 itemWholesaleRangeVos，解析引用后取第一个「元素为 dict」的 list
    ladder_raw: list[dict[str, Any]] = _ladder_dicts_from(
        product.get("itemWholesaleRangeVos")
    )
    if not ladder_raw:
        dec = json.JSONDecoder()
        for m in re.finditer(r'"itemWholesaleRangeVos"\s*:\s*', buf):
            try:
                val, _ = dec.raw_decode(buf, m.end())
            except Exception:
                continue
            ladder_raw = _ladder_dicts_from(val)
            if ladder_raw:
                break

    ladder: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for item in ladder_raw:
        original = item.get("originalPrice")
        # 真实样本（2026-10-21 item 1069442111）可无 promDiscountPrice；
        # 有促销时才有该键。展示价 = promDiscountPrice（存在且非 0）否则 originalPrice。
        prom = item.get("promDiscountPrice")
        display = prom if isinstance(prom, (int, float)) and prom != 0 else original
        if original is None and display is None:
            continue
        key = (item.get("startQty"), item.get("endQty"), original, display)
        if key in seen:
            continue
        seen.add(key)
        ladder.append(
            {
                "qty_from": item.get("startQty"),
                "qty_to": item.get("endQty"),
                "original_price": original,
                "discount_price": display,
                "has_promo": isinstance(prom, (int, float)) and prom != 0,
            }
        )
    ladder.sort(key=lambda x: (x["qty_from"] or 0))
    single = next(
        (x for x in ladder if (x["qty_from"] or 0) <= 1),
        ladder[0] if ladder else None,
    )
    # 标题里 "From $x" 常取阶梯最低展示价，不一定等于起购单价
    from_prices = [
        x["discount_price"]
        for x in ladder
        if isinstance(x.get("discount_price"), (int, float))
    ]
    from_price = min(from_prices) if from_prices else None

    seq = seller.get("supplierSeq")
    title = product.get("productName")
    suspicious = bool(
        isinstance(title, str)
        and any(m in title for m in ("VIP link", "pay link", "only for"))
    )

    return {
        "item_code": product.get("itemCode"),
        "product_id": product.get("productId"),
        "title": title,
        "suspicious_title": suspicious,
        "seo_name": product.get("seoName"),
        "canonical": product.get("canonical"),
        "category": {
            "name": product.get("cateDispName"),
            "id": product.get("cateDispId"),
            # 发布类目 ID（后台口径，与展示类目可能不同）
            "pub_id": product.get("catePubId"),
        },
        "sales": {
            # 页面销量展示文案，如 "142"；saleNum 数值口径可能为 0
            "display": product.get("saleNumStr"),
            "num": product.get("saleNum"),
        },
        "order": {
            "min_order": product.get("minOrder"),
            "max_sale_qty": product.get("maxSaleQty"),
            "unit": product.get("measureName"),
            "unit_plural": product.get("plural"),
        },
        "package": {
            "weight_kg": product.get("grossweight"),
            "length": product.get("length"),
            "width": product.get("width"),
            "height": product.get("height"),
        },
        "last_modify_date": product.get("lastModifyDate"),
        "shop": {
            "name": seller.get("suppliername"),
            "id": seller.get("supplierid"),
            "seq": seq,
            "url": (
                f"https://www.dhgate.com/store/{seq}" if seq is not None else None
            ),
            "address": seller.get("address"),
            "year": seller.get("year"),
            "grade": seller.get("grade"),
        },
        "price": {
            "currency": "USD",
            # 起购档（startQty<=1）展示价；无促销时等于 originalPrice
            "single_price": single["discount_price"] if single else None,
            "single_original": single["original_price"] if single else None,
            # 阶梯最低价（页面 From $x 常见口径）
            "from_price": from_price,
            "ladder": ladder,
        },
    }


def _is_eo_bot_challenge(body: str) -> bool:
    head = body[:4000]
    return "EO_Bot_Ssid" in head and "self.__next_f.push" not in body


def _http_get_rsc(url: str) -> tuple[int, str, str]:
    """
    拉取商品页。优先 curl（TLS 指纹更接近浏览器，不易触发 EO_Bot）；
    无 curl 时回退 httpx。
    返回 (status_code, content_type, body_text)。
    """
    curl_bin = shutil.which("curl") or shutil.which("curl.exe")
    if curl_bin:
        proc = subprocess.run(
            [
                curl_bin,
                "-sS",
                "--compressed",
                "-L",
                "--max-time",
                str(int(_FETCH_TIMEOUT)),
                "-A",
                UA,
                "-H",
                "RSC: 1",
                "-H",
                "Accept: text/x-component",
                "-H",
                "Accept-Language: en-US,en;q=0.9",
                "-w",
                "\n__CURL_META__%{http_code}|%{content_type}",
                url,
            ],
            capture_output=True,
            timeout=_FETCH_TIMEOUT + 5,
        )
        if proc.returncode != 0:
            err = (proc.stderr or b"").decode("utf-8", errors="replace")
            raise httpx.HTTPError(f"curl failed: {err or proc.returncode}")
        raw_out = (proc.stdout or b"").decode("utf-8", errors="replace")
        if "__CURL_META__" not in raw_out:
            raise httpx.HTTPError("curl meta missing")
        body, meta = raw_out.rsplit("__CURL_META__", 1)
        code_s, ctype = (meta.strip().split("|", 1) + [""])[:2]
        return int(code_s or "0"), ctype, body

    with httpx.Client(
        timeout=_FETCH_TIMEOUT,
        follow_redirects=True,
        headers={
            "User-Agent": UA,
            "RSC": "1",
            "Accept": "text/x-component",
            "Accept-Language": "en-US,en;q=0.9",
        },
    ) as client:
        response = client.get(url)
        return (
            response.status_code,
            response.headers.get("content-type") or "",
            response.text or "",
        )


def fetch_product_page(url: str, *, include_raw: bool = False) -> dict[str, Any]:
    """
    拉取并解析敦煌商品详情页。

    返回结构：
    - ok / reason / message / url
    - channel / http_status / elapsed_ms
    - parsed：解析后的结构化数据
    - raw / content_type：仅当 include_raw=True（联调接口）时返回完整 Flight 原文
    """
    safe_url = assert_dhgate_product_url(url)
    started = time.perf_counter()

    result: dict[str, Any] = {
        "ok": False,
        "reason": "upstream_error",
        "message": None,
        "url": safe_url,
        "channel": None,
        "http_status": None,
        "elapsed_ms": 0.0,
        "parsed": None,
    }
    if include_raw:
        result["raw"] = None
        result["content_type"] = None

    try:
        status_code, content_type, body = _http_get_rsc(safe_url)
    except httpx.TimeoutException:
        result["reason"] = "upstream_error"
        result["message"] = "请求敦煌商品页超时"
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
        return result
    except Exception as exc:
        result["reason"] = "upstream_error"
        result["message"] = f"请求失败: {exc}"
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
        return result

    result["http_status"] = status_code
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    if include_raw:
        result["content_type"] = content_type

    if status_code == 404:
        result["reason"] = "not_found"
        result["message"] = "商品不存在或已下架"
        return result

    if any(mark in body[:4000] for mark in BLOCK_MARKS):
        result["reason"] = "blocked"
        result["message"] = "疑似触发风控验证，请勿自动重试"
        return result

    if _is_eo_bot_challenge(body):
        result["reason"] = "blocked"
        result["message"] = "EO_Bot 门禁未通过，请稍后重试（勿对 blocked 自动重试）"
        return result

    ctype = (content_type or "").lower()
    if "text/x-component" in ctype:
        flight = body
        channel = "rsc"
    else:
        flight = flight_from_html(body)
        channel = "html-fallback"

    result["channel"] = channel
    if include_raw:
        result["raw"] = flight

    if not flight.strip():
        result["reason"] = "parse_failed"
        result["message"] = "未获取到 Flight 数据（可能页面改版）"
        return result

    parsed = parse_flight(flight)
    result["parsed"] = parsed

    if not parsed.get("item_code") or not parsed.get("title"):
        result["reason"] = "parse_failed"
        result["message"] = "解析失败：缺少 itemCode 或 productName"
        return result

    result["ok"] = True
    result["reason"] = "ok"
    result["message"] = "ok"
    return result
