"""用真实 RSC Flight 校验 parse_flight / 文档规则。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.dhgate.product_page import (  # noqa: E402
    _blocks,
    _json_all,
    _resolve_ref,
    parse_flight,
)

BODY = Path(__file__).with_name("_body_rsc.bin")


def main() -> None:
    raw = BODY.read_text(encoding="utf-8", errors="replace")
    print("raw_len", len(raw))
    print("ctype_hint lines with itemCode", len(re.findall(r'"itemCode"', raw)))
    print("prodSeller count", len(re.findall(r'"prodSeller"', raw)))
    print("suppliername count", len(re.findall(r'"suppliername"', raw)))
    print("itemWholesaleRangeVos count", len(re.findall(r'"itemWholesaleRangeVos"', raw)))

    # 列出 itemWholesaleRangeVos 每次出现的值类型
    dec = json.JSONDecoder()
    for i, m in enumerate(re.finditer(r'"itemWholesaleRangeVos"\s*:\s*', raw)):
        try:
            val, _ = dec.raw_decode(raw, m.end())
        except Exception as exc:
            print(f"  vos[{i}] decode_err {exc}")
            continue
        print(f"  vos[{i}] type={type(val).__name__} preview={str(val)[:120]}")
        if isinstance(val, list) and val:
            print("  vos full ladder:")
            print(json.dumps(val, ensure_ascii=False, indent=2))

    for i, m in enumerate(re.finditer(r'"prodSeller"\s*:\s*', raw)):
        try:
            val, _ = dec.raw_decode(raw, m.end())
        except Exception as exc:
            print(f"  seller[{i}] decode_err {exc}")
            continue
        print(f"  seller[{i}] type={type(val).__name__} preview={str(val)[:200]}")

    blocks = _blocks(raw)
    products = [
        b
        for b in blocks.values()
        if isinstance(b, dict) and b.get("itemCode") and b.get("productName")
    ]
    print("product_blocks", len(products))
    if products:
        p = products[0]
        print("product keys sample", sorted(p.keys())[:40])
        print("itemCode", p.get("itemCode"))
        print("productName", (p.get("productName") or "")[:120])
        print("cateDispName", p.get("cateDispName"), "cateDispId", p.get("cateDispId"))
        print("supplierId", p.get("supplierId"))
        vos = p.get("itemWholesaleRangeVos")
        print("vos_on_product", type(vos).__name__, str(vos)[:80])
        print("resolved_vos", type(_resolve_ref(vos, blocks)).__name__)

    parsed = parse_flight(raw)
    print("--- parsed ---")
    print(json.dumps(parsed, ensure_ascii=False, indent=2))

    # 对照文档期望字段是否齐全
    checks = {
        "item_code": parsed.get("item_code") == "1069442111",
        "title_nonempty": bool(parsed.get("title")),
        "single_price": parsed.get("price", {}).get("single_price") is not None,
        "category_name": bool((parsed.get("category") or {}).get("name")),
        "shop_name": bool((parsed.get("shop") or {}).get("name")),
        "shop_seq": (parsed.get("shop") or {}).get("seq") is not None,
    }
    print("--- checks ---")
    for k, v in checks.items():
        print(f"  {k}: {v}")

    # WebFetch 侧可见线索：店名 Oc2024_cobbler, 价格约 9.55
    title = parsed.get("title") or ""
    shop = (parsed.get("shop") or {}).get("name")
    price = (parsed.get("price") or {}).get("single_price")
    print("title_has_VD50010", "VD50010" in title or "Sleeveless" in title)
    print("shop", shop, "price", price)


if __name__ == "__main__":
    main()
