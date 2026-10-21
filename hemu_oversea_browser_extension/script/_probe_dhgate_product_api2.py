"""Deeper probe: productInfo context + shared chunks + RSC headers."""
from __future__ import annotations

import re
import tempfile
import urllib.request
from pathlib import Path

tmp = Path(tempfile.gettempdir())
js = (tmp / "dhgate_page.js").read_text(encoding="utf-8", errors="ignore")
html = (tmp / "dhgate_product.html").read_text(encoding="utf-8", errors="ignore")

print("=== productInfo contexts ===")
for m in re.finditer(r".{0,120}productInfo.{0,200}", js, flags=re.I):
    print(m.group(0).replace("\n", " ")[:300])
    print("---")

print("\n=== /prod/ paths in page.js ===")
for p in sorted(set(re.findall(r"/prod/[a-zA-Z0-9_./?\-]+", js))):
    print(p)

# Download shared chunks from HTML script tags
srcs = re.findall(
    r'src="(https://js\.dhresource\.com/buyerassets/_next/static/chunks/[^"]+)"',
    html,
)
print(f"\n=== scanning {len(srcs)} chunks for API paths ===")
ua = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}
api_hits: dict[str, set[str]] = {}
for url in srcs:
    name = url.rsplit("/", 1)[-1]
    path = tmp / f"dh_chunk_{name}"
    if not path.exists() or path.stat().st_size < 100:
        try:
            req = urllib.request.Request(url, headers=ua)
            path.write_bytes(urllib.request.urlopen(req, timeout=30).read())
        except Exception as e:
            print("fail", name, e)
            continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    found = set()
    for pat in [
        r"https?://[a-zA-Z0-9._\-]+(?:dhgate|dhresource)[a-zA-Z0-9._\-/?=&%]{0,100}",
        r"/prod/[a-zA-Z0-9_./?\-]+",
        r"/buyer[a-zA-Z0-9_./?\-]+",
        r"/mapi/[a-zA-Z0-9_./?\-]+",
        r"/api/[a-zA-Z0-9_./?\-]+",
        r"getProduct[A-Za-z0-9_]*",
        r"productDetail[A-Za-z0-9_]*",
        r"itemDetail[A-Za-z0-9_]*",
        r"skuDetail[A-Za-z0-9_]*",
    ]:
        found |= set(re.findall(pat, text, flags=re.I))
    # keep interesting only
    interesting = {
        x
        for x in found
        if re.search(
            r"api|ajax|mapi|\.do|/prod/|product|sku|item|detail|gateway|buyer",
            x,
            re.I,
        )
        and not re.search(r"\.(png|jpg|svg|css|webp)|/svg/", x, re.I)
    }
    if interesting:
        api_hits[name] = interesting

for name, hits in sorted(api_hits.items(), key=lambda kv: -len(kv[1])):
    print(f"\n[{name}] {len(hits)} hits")
    for h in sorted(hits)[:30]:
        print(" ", h[:160])

# Try RSC request for same product URL
print("\n=== try RSC fetch ===")
prod = "https://www.dhgate.com/product/vd50010-women-s-sleeveless-vest-tank-top/1069442111.html.html"
headers = {
    **ua,
    "RSC": "1",
    "Next-Router-State-Tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22product%22%2C%7B%22children%22%3A%5B%5B%22itemcode%5D%22%2C%22vd50010-women-s-sleeveless-vest-tank-top%2F1069442111.html.html%22%2C%22d%22%5D%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%5D%7D%5D%7D%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
    "Accept": "text/x-component",
}
try:
    req = urllib.request.Request(prod, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read(5000)
        print("status", resp.status, "ctype", resp.headers.get("content-type"))
        print(body[:800])
except Exception as e:
    print("RSC fail", e)
