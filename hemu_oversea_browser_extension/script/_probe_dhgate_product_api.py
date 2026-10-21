"""One-off: probe DHgate product page HTML/JS for detail API endpoints."""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

tmp = Path(tempfile.gettempdir())
html = (tmp / "dhgate_product.html").read_text(encoding="utf-8", errors="ignore")
js = (tmp / "dhgate_page.js").read_text(encoding="utf-8", errors="ignore")

print("html", len(html), "js", len(js))
print("next_f", html.count("self.__next_f"))
print("itemcode hits", html.lower().count("1069442111"))

patterns = [
    r"https?://[a-zA-Z0-9._\-/:]+(?:api|ajax|mapi|gateway)[a-zA-Z0-9._\-/?=&%]*",
    r'["\'](/[a-zA-Z0-9_\-/]*(?:api|product|item|sku|detail)[a-zA-Z0-9_\-/]*)["\']',
    r"get[A-Z][a-zA-Z]*Product[A-Za-z]*",
    r"fetchProduct|loadProduct|productInfo|prodInfo|itemInfo|getItemDetail",
    r"dhgate\.com/[a-zA-Z0-9_\-/]+\.do",
]

for pat in patterns:
    found = sorted(set(re.findall(pat, js, flags=re.I)))
    print(f"\n=== {pat[:60]}... count={len(found)}")
    for u in found[:40]:
        print(" ", u)

# Also scan other common chunks if present — search HTML for absolute API-looking strings
print("\n=== HTML absolute API-ish URLs ===")
urls = sorted(
    set(
        re.findall(
            r"https?://[a-zA-Z0-9._\-]+(?:dhgate|dhresource)[^\s\"'<>]{0,120}",
            html,
            flags=re.I,
        )
    )
)
for u in urls:
    if re.search(r"api|ajax|mapi|\.do|/prod|/item|sku|detail|gateway", u, re.I):
        print(" ", u[:200])

# Look for RSC payload keys around itemcode
print("\n=== contexts around itemcode (sample) ===")
for m in re.finditer(r".{0,60}1069442111.{0,100}", html):
    s = m.group(0).replace("\n", " ")
    print(" ", s[:180])
    break

# Search for common BFF path fragments in page js
print("\n=== path-like strings with product/sku ===")
paths = sorted(
    set(
        re.findall(
            r'["`](/[a-zA-Z0-9_\-./]{4,80})["`]',
            js,
        )
    )
)
for p in paths:
    if re.search(r"api|product|sku|item|detail|buyer|prod", p, re.I):
        print(" ", p)
