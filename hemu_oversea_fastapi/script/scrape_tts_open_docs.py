"""从 partner.tiktokshop.com 抓取 API Reference 与公共约定页。

文档站是 SPA。页面加载后会请求：
  /api/v1/document/tree
  /api/v1/document/detail?document_id=<slug>

本脚本用 Playwright 打开文档站，再按同样的接口把正文拉下来，供 generate_tts_api_md.py 使用。

用法:
  python script/scrape_tts_open_docs.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "_tts_doc_scrape"
DETAILS = OUT / "details"
GUIDES = OUT / "guides"
TREE_URL = (
    "https://partner.tiktokshop.com/api/v1/document/tree"
    "?workspace_id=3&aid=359713&locale=en-US"
)
DETAIL_URL = (
    "https://partner.tiktokshop.com/api/v1/document/detail"
    "?document_id={slug}&workspace_id=3&aid=359713&locale=en-US"
)
ENTRY = "https://partner.tiktokshop.com/docv2/page/tts-developer-guide"

GUIDE_SLUGS = [
    "sign-your-api-request",
    "common-parameters",
    "common-errors",
    "rate-limits",
    "api-versioning",
    "methods-and-endpoints",
    "tts-api-concepts-overview",
    "authorization-overview-202407",
    "seller-authorization-guide",
    "creator-authorization-guide",
    "partner-authorization-guide",
    "access-scope",
    "tts-webhooks-overview",
    "configuration-guide",
    "regions-and-languages",
]


def fetch_batch(page, slugs: list[str]) -> list[dict]:
    return page.evaluate(
        """async (slugs) => {
          const tpl = %s;
          const jobs = slugs.map(async (slug) => {
            const url = tpl.replace('{slug}', encodeURIComponent(slug));
            try {
              const r = await fetch(url, { credentials: 'include' });
              const text = await r.text();
              return { slug, status: r.status, text };
            } catch (err) {
              return { slug, status: 0, text: String(err) };
            }
          });
          return await Promise.all(jobs);
        }"""
        % json.dumps(DETAIL_URL),
        slugs,
    )


def save_payload(folder: Path, slug: str, raw_text: str) -> str:
    data = json.loads(raw_text)
    if data.get("code") not in (0, "0", None) and not data.get("data"):
        raise RuntimeError(f"{slug} code={data.get('code')} message={data.get('message')}")
    inner = data.get("data") or {}
    payload = {
        "slug": slug,
        "title": inner.get("title") or "",
        "content": inner.get("content") or "",
        "update_time": inner.get("update_time"),
        "is_api_doc": inner.get("is_api_doc"),
        "document_id": inner.get("document_id"),
        "doc_type": inner.get("doc_type"),
    }
    path = folder / f"{slug}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload["title"]


def collect_targets(tree: list[dict]) -> tuple[list[str], list[str]]:
    by_id = {node["document_id"]: node for node in tree}
    api_slugs: list[str] = []
    webhook_slugs: list[str] = []
    webhook_root = next(
        (n for n in tree if n.get("name") == "Webhooks" and not n.get("parent_id")),
        None,
    )

    def under_webhook(node: dict) -> bool:
        if webhook_root is None:
            return False
        cur = node
        seen = set()
        while cur and cur.get("parent_id") and cur["document_id"] not in seen:
            seen.add(cur["document_id"])
            if cur["parent_id"] == webhook_root["document_id"] or cur["document_id"] == webhook_root["document_id"]:
                return True
            cur = by_id.get(cur["parent_id"])
        return False

    for node in tree:
        slug = (node.get("document_path") or "").strip()
        if not slug or node.get("is_dir"):
            continue
        if node.get("is_api_doc"):
            api_slugs.append(slug)
        elif under_webhook(node):
            webhook_slugs.append(slug)
    return api_slugs, webhook_slugs


def download(page, slugs: list[str], folder: Path, label: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    pending = [s for s in slugs if not (folder / f"{s}.json").exists()]
    print(f"[{label}] total={len(slugs)} pending={len(pending)}")
    batch = 6
    for i in range(0, len(pending), batch):
        chunk = pending[i : i + batch]
        rows = fetch_batch(page, chunk)
        for row in rows:
            slug = row["slug"]
            if row["status"] != 200:
                print(f"  fail {slug} status={row['status']} {row['text'][:160]}")
                continue
            try:
                title = save_payload(folder, slug, row["text"])
            except Exception as exc:
                print(f"  fail {slug} {exc}")
                continue
            print(f"  ok {slug} {title}")
        time.sleep(0.3)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="en-US", viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto(ENTRY, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        tree_resp = page.evaluate(
            """async (url) => {
              const r = await fetch(url, { credentials: 'include' });
              return { status: r.status, text: await r.text() };
            }""",
            TREE_URL,
        )
        if tree_resp["status"] != 200:
            raise SystemExit(f"tree status {tree_resp['status']}")
        (OUT / "tree.json").write_text(tree_resp["text"], encoding="utf-8")
        tree = json.loads(tree_resp["text"])["data"]["document_tree"]
        api_slugs, webhook_slugs = collect_targets(tree)
        download(page, api_slugs, DETAILS, "api")
        download(page, webhook_slugs, OUT / "webhooks", "webhook")
        download(page, GUIDE_SLUGS, GUIDES, "guide")
        browser.close()
    print("done")


if __name__ == "__main__":
    main()
