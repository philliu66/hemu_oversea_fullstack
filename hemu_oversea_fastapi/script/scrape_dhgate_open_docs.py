"""从 open.dhgate.com 抓取卖家/公共 API 列表与详情，供生成 dhgate_API.md。

用法（系统已装 playwright）:
  python script/scrape_dhgate_open_docs.py
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT_DIR = Path(__file__).resolve().parent / "_dhgate_doc_scrape"
BASE = "https://open.dhgate.com"

# 卖家 API 模块（与官网侧栏一致）+ 尝试公共/分销
MODULES = [
    ("相册API", "001001"),
    ("基础API", "001002"),
    ("类目API", "001003"),
    ("客户评论API", "001004"),
    ("物流API", "001005"),
    ("站内信API", "001006"),
    ("订单API", "001007"),
    ("产品API", "001008"),
    ("用户API", "001009"),
    ("在线发货API", "001010"),
    ("数据API(限免)", "001011"),
    ("增值API", "001012"),
]


def wait_detail_links(page, timeout_ms: int = 30000) -> None:
    page.wait_for_selector(
        'a[href*="/docs/api/detail/"]',
        timeout=timeout_ms,
        state="attached",
    )
    page.wait_for_timeout(800)


def extract_list(page) -> dict:
    return page.evaluate(
        """() => {
      const links = [...document.querySelectorAll('a[href*="/docs/api/detail/"]')].map(a => {
        const tr = a.closest('tr');
        let desc = '';
        if (tr) {
          const tds = [...tr.querySelectorAll('td')];
          desc = tds.length ? (tds[tds.length-1].innerText||'').trim() : '';
        }
        return { name: (a.innerText||'').trim(), href: a.href, desc };
      }).filter(x => x.name.startsWith('dh.'));
      const intro = (document.body.innerText.match(/API介绍\\n([\\s\\S]*?)\\nAPI列表/)||[])[1] || '';
      // 公共 API 子模块链接
      const subMods = [...document.querySelectorAll('a[href*="/docs/api/00"]')].map(a => ({
        text: (a.innerText||'').trim(), href: a.href
      }));
      return { intro: intro.trim(), apis: links, subMods };
    }"""
    )


def parse_version(name: str) -> tuple[str, tuple[int, ...]]:
    m = re.match(r"^(dh\.[^$]+)\$([\d.]+)$", name.strip())
    if not m:
        return name, (0,)
    method, ver = m.group(1), m.group(2)
    parts = tuple(int(x) for x in ver.split(".") if x.isdigit())
    return method, parts


def pick_preferred(apis: list[dict]) -> list[dict]:
    """同一 method 只保留最高版本。"""
    best: dict[str, dict] = {}
    for api in apis:
        method, ver = parse_version(api["name"])
        cur = best.get(method)
        if cur is None or ver > cur["_ver"]:
            best[method] = {**api, "_ver": ver, "method": method, "version": ".".join(map(str, ver))}
    out = []
    for item in best.values():
        item.pop("_ver", None)
        out.append(item)
    out.sort(key=lambda x: x["name"])
    return out


def extract_detail(page) -> dict:
    return page.evaluate(
        """() => {
      const text = document.body.innerText || '';
      const title = (text.match(/dh\\.[^\\n]+/)||[])[0] || document.title;
      const overview = {
        url: (text.match(/接口地址\\n([^\\n]+)/)||[])[1] || 'http://api.dhgate.com/dop/router',
        desc: (text.match(/接口说明\\n([^\\n]+)/)||[])[1] || '',
        timeout: (text.match(/超时控制\\n([^\\n]+)/)||[])[1] || '',
        created: (text.match(/创建时间\\n([^\\n]+)/)||[])[1] || '',
        publicVisit: (text.match(/公网访问\\n([^\\n]+)/)||[])[1] || '',
        level: (text.match(/API授权级别\\n([^\\n]+)/)||[])[1] || '',
      };
      function parseTableAfter(header) {
        const idx = text.indexOf(header);
        if (idx < 0) return [];
        // 取到下一个大段标题前
        const rest = text.slice(idx + header.length);
        const stop = rest.search(/\\n(公共参数|请求参数|响应参数|请求示例|响应示例|异常示例|错误码解释|API工具)\\n/);
        const chunk = stop >= 0 ? rest.slice(0, stop) : rest.slice(0, 4000);
        const lines = chunk.split('\\n').map(s => s.trim()).filter(Boolean);
        // 跳过表头行
        const rows = [];
        // 表格在 DOM 里更可靠
        return null;
      }
      function tablesAfterHeading(headingText) {
        const headings = [...document.querySelectorAll('h2,h3,h4,.title,div,p,span')]
          .filter(el => (el.innerText||'').trim() === headingText);
        const out = [];
        for (const h of headings) {
          let el = h.parentElement;
          // 向上找附近 table
          let table = null;
          let cur = h;
          for (let i=0;i<8 && cur;i++) {
            table = cur.parentElement && cur.parentElement.querySelector('table');
            if (table) break;
            cur = cur.parentElement;
          }
          if (!table) {
            // 向后找 sibling
            let sib = h.nextElementSibling;
            for (let i=0;i<10 && sib;i++) {
              if (sib.tagName === 'TABLE') { table = sib; break; }
              const t = sib.querySelector && sib.querySelector('table');
              if (t) { table = t; break; }
              sib = sib.nextElementSibling;
            }
          }
          if (!table) continue;
          const rows = [...table.querySelectorAll('tr')].map(tr =>
            [...tr.querySelectorAll('th,td')].map(c => (c.innerText||'').trim())
          ).filter(r => r.length);
          if (rows.length) out.push(rows);
        }
        return out;
      }
      // 更稳：所有 table，按前文标题归类
      const allTables = [...document.querySelectorAll('table')].map(table => {
        let label = '';
        let p = table.previousElementSibling;
        for (let i=0;i<6 && p;i++) {
          const t = (p.innerText||'').trim().split('\\n')[0];
          if (t && t.length < 40) { label = t; break; }
          p = p.previousElementSibling;
        }
        const rows = [...table.querySelectorAll('tr')].map(tr =>
          [...tr.querySelectorAll('th,td')].map(c => (c.innerText||'').trim())
        ).filter(r => r.length);
        return { label, rows };
      }).filter(t => t.rows.length >= 2);

      const commonParams = [];
      const requestParams = [];
      const responseParams = [];
      const errorCodes = [];
      for (const t of allTables) {
        const label = t.label || '';
        const header = (t.rows[0] || []).join('|');
        const body = t.rows.slice(1);
        const mapped = body.map(r => ({
          name: r[0] || '',
          type: r[1] || '',
          required: r[2] || '',
          values: r[3] || '',
          desc: r[4] || r[3] || '',
          raw: r,
        }));
        if (label.includes('公共参数') || header.includes('参数名称') && label.includes('公共')) {
          commonParams.push(...mapped);
        } else if (label.includes('请求参数')) {
          requestParams.push(...mapped);
        } else if (label.includes('响应参数')) {
          responseParams.push(...mapped);
        } else if (label.includes('错误码')) {
          errorCodes.push(...mapped);
        }
      }
      // 若 label 识别失败：按含「是否必须」的表依次归入 公共/请求/响应
      if (!requestParams.length) {
        const paramTables = allTables.filter(t =>
          (t.rows[0]||[]).join('|').includes('参数名称') &&
          (t.rows[0]||[]).join('|').includes('是否必须')
        );
        if (paramTables.length >= 1 && !commonParams.length) {
          commonParams.push(...paramTables[0].rows.slice(1).map(r => ({
            name:r[0], type:r[1], required:r[2], values:r[3], desc:r[4]||'', raw:r
          })));
        }
        if (paramTables.length >= 2) {
          requestParams.push(...paramTables[1].rows.slice(1).map(r => ({
            name:r[0], type:r[1], required:r[2], values:r[3], desc:r[4]||'', raw:r
          })));
        }
        if (paramTables.length >= 3) {
          responseParams.push(...paramTables[2].rows.slice(1).map(r => ({
            name:r[0], type:r[1], required:r[2], values:r[3], desc:r[4]||'', raw:r
          })));
        }
      }

      // 正文「请求参数」段兜底
      let requestText = '';
      const ridx = text.indexOf('请求参数');
      if (ridx >= 0) {
        const rest = text.slice(ridx, ridx + 8000);
        const stop = rest.search(/\\n(响应参数|请求示例|响应示例|异常示例|错误码解释|API工具)\\n/);
        requestText = (stop >= 0 ? rest.slice(0, stop) : rest).trim();
      }

      // 响应示例 JSON
      let responseExample = '';
      const m = text.match(/响应示例\\njsonxml\\n([\\s\\S]*?)\\n异常示例/);
      if (m) responseExample = m[1].trim().slice(0, 4000);

      return {
        title,
        overview,
        commonParams,
        requestParams,
        responseParams,
        errorCodes,
        responseExample,
        requestText,
        tablesCount: allTables.length,
        textLen: text.length,
      };
    }"""
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    modules_path = OUT_DIR / "modules.json"
    details_path = OUT_DIR / "details.json"

    with sync_playwright() as p:
        # 官网对无头/非标准 UA 可能不渲染文档正文；优先用本机 Chrome
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="zh-CN",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()
        modules: list[dict] = []

        # 先打开任一页预热
        page.goto(f"{BASE}/docs/api/001001", wait_until="networkidle", timeout=90000)
        time.sleep(3)

        for module_name, code in MODULES:
            url = f"{BASE}/docs/api/{code}"
            print(f"[list] {module_name} {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                wait_detail_links(page)
            except Exception as exc:
                print(f"  warn: no links: {exc}")
            data = extract_list(page)
            preferred = pick_preferred(data.get("apis") or [])
            modules.append(
                {
                    "module": module_name,
                    "code": code,
                    "url": url,
                    "intro": data.get("intro") or "",
                    "apis_all": data.get("apis") or [],
                    "apis_preferred": preferred,
                }
            )
            print(f"  apis={len(data.get('apis') or [])} preferred={len(preferred)}")
            time.sleep(0.4)

        # 公共 API：从侧栏找链接
        print("[list] probe 公共API / 分销API")
        page.goto(f"{BASE}/docs/api/001001", wait_until="domcontentloaded", timeout=60000)
        time.sleep(1.5)
        extra = page.evaluate(
            """() => {
          const items = [...document.querySelectorAll('a')].map(a => ({
            text: (a.innerText||'').trim(), href: a.href
          })).filter(x => /docs\\/api\\/\\d+/.test(x.href));
          return items;
        }"""
        )
        known = {m["code"] for m in modules}
        for item in extra:
            m = re.search(r"/docs/api/(\\d+)", item["href"])
            if not m:
                continue
            code = m.group(1)
            if code in known:
                continue
            text = item["text"]
            if not text or text in ("API文档",):
                continue
            # 只收 003xxx 公共 / 分销 等
            if not code.startswith("003") and "公共" not in text and "分销" not in text and "基础" not in text:
                continue
            print(f"[list-extra] {text} {code}")
            page.goto(item["href"], wait_until="domcontentloaded", timeout=60000)
            try:
                wait_detail_links(page)
            except Exception:
                pass
            data = extract_list(page)
            preferred = pick_preferred(data.get("apis") or [])
            if not preferred and not data.get("apis"):
                continue
            modules.append(
                {
                    "module": text or f"模块{code}",
                    "code": code,
                    "url": item["href"],
                    "intro": data.get("intro") or "",
                    "apis_all": data.get("apis") or [],
                    "apis_preferred": preferred,
                }
            )
            known.add(code)

        modules_path.write_text(
            json.dumps(modules, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"wrote {modules_path}")

        # 抓详情：仅 preferred
        details: dict[str, dict] = {}
        for mod in modules:
            for api in mod["apis_preferred"]:
                name = api["name"]
                href = api["href"]
                if name in details:
                    continue
                print(f"[detail] {name}")
                page.goto(href, wait_until="domcontentloaded", timeout=60000)
                try:
                    page.wait_for_function(
                        """() => document.body.innerText.includes('接口概述') || document.body.innerText.includes('请求参数')""",
                        timeout=15000,
                    )
                except Exception as exc:
                    print(f"  warn: {exc}")
                time.sleep(0.3)
                detail = extract_detail(page)
                detail["name"] = name
                detail["href"] = href
                detail["module"] = mod["module"]
                detail["list_desc"] = api.get("desc") or ""
                details[name] = detail
                time.sleep(0.25)

        details_path.write_text(
            json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"wrote {details_path} count={len(details)}")
        browser.close()


if __name__ == "__main__":
    main()
