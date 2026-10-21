"""补抓 requestParams 为空的接口详情（改善表格识别 + 保存正文片段）。"""

from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "_dhgate_doc_scrape" / "details.json"


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

      const allTables = [...document.querySelectorAll('table')].map(table => {
        let label = '';
        let p = table.previousElementSibling;
        for (let i=0;i<8 && p;i++) {
          const t = (p.innerText||'').trim().split('\\n')[0];
          if (t && t.length < 60) { label = t; break; }
          p = p.previousElementSibling;
        }
        // 再向上找父级附近标题
        if (!label) {
          let cur = table.parentElement;
          for (let i=0;i<6 && cur;i++) {
            const h = cur.querySelector('h2,h3,h4,.ant-typography');
            if (h) { label = (h.innerText||'').trim().split('\\n')[0]; break; }
            cur = cur.parentElement;
          }
        }
        const rows = [...table.querySelectorAll('tr')].map(tr =>
          [...tr.querySelectorAll('th,td')].map(c => (c.innerText||'').trim())
        ).filter(r => r.length);
        return { label, rows };
      }).filter(t => t.rows.length >= 2);

      function mapRows(body) {
        return body.map(r => ({
          name: r[0] || '',
          type: r[1] || '',
          required: r[2] || '',
          values: r[3] || '',
          desc: r[4] || r[3] || '',
          raw: r,
        }));
      }

      const commonParams = [];
      const requestParams = [];
      const responseParams = [];
      const errorCodes = [];
      for (const t of allTables) {
        const label = t.label || '';
        const header = (t.rows[0] || []).join('|');
        const mapped = mapRows(t.rows.slice(1));
        if (label.includes('公共参数')) commonParams.push(...mapped);
        else if (label.includes('请求参数')) requestParams.push(...mapped);
        else if (label.includes('响应参数')) responseParams.push(...mapped);
        else if (label.includes('错误码')) errorCodes.push(...mapped);
        else if (header.includes('参数名称') && header.includes('是否必须')) {
          // 未识别 label：按出现顺序稍后处理
        }
      }
      if (!requestParams.length) {
        const paramTables = allTables.filter(t => {
          const h = (t.rows[0]||[]).join('|');
          return h.includes('参数名称') && (h.includes('是否必须') || h.includes('必须'));
        });
        if (paramTables.length >= 1 && !commonParams.length) {
          commonParams.push(...mapRows(paramTables[0].rows.slice(1)));
        }
        if (paramTables.length >= 2) {
          requestParams.push(...mapRows(paramTables[1].rows.slice(1)));
        }
        if (paramTables.length >= 3) {
          responseParams.push(...mapRows(paramTables[2].rows.slice(1)));
        }
      }

      // 正文「请求参数」段（表格解析失败时兜底）
      let requestText = '';
      const idx = text.indexOf('请求参数');
      if (idx >= 0) {
        const rest = text.slice(idx, idx + 8000);
        const stop = rest.search(/\\n(响应参数|请求示例|响应示例|异常示例|错误码解释|API工具)\\n/);
        requestText = (stop >= 0 ? rest.slice(0, stop) : rest).trim();
      }

      let responseExample = '';
      const m = text.match(/响应示例\\njsonxml\\n([\\s\\S]*?)\\n异常示例/);
      if (m) responseExample = m[1].trim().slice(0, 4000);

      return {
        title, overview, commonParams, requestParams, responseParams, errorCodes,
        responseExample, requestText,
        tablesCount: allTables.length,
        tableLabels: allTables.map(t => t.label),
        textLen: text.length,
      };
    }"""
    )


def main() -> None:
    details = json.loads(OUT.read_text(encoding="utf-8"))
    empty = [
        k
        for k, v in details.items()
        if not [
            r
            for r in (v.get("requestParams") or [])
            if r.get("name") and r.get("name") != "参数名称"
        ]
    ]
    print("empty", empty)
    if not empty:
        return

    with sync_playwright() as p:
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
        for name in empty:
            href = details[name]["href"]
            print("[rescrape]", name, href)
            page.goto(href, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_function(
                    "() => document.body.innerText.includes('接口概述') || document.body.innerText.includes('请求参数')",
                    timeout=20000,
                )
            except Exception as exc:
                print("  warn", exc)
            time.sleep(0.8)
            # 尝试展开折叠
            page.evaluate(
                """() => {
              document.querySelectorAll('.ant-collapse-header, .ant-tabs-tab').forEach(el => {
                try { el.click(); } catch(e) {}
              });
            }"""
            )
            time.sleep(0.5)
            detail = extract_detail(page)
            details[name].update(detail)
            reqn = len(
                [
                    r
                    for r in detail.get("requestParams") or []
                    if r.get("name") and r.get("name") != "参数名称"
                ]
            )
            print(
                f"  tables={detail.get('tablesCount')} labels={detail.get('tableLabels')} req={reqn} textLen={len(detail.get('requestText') or '')}"
            )
        OUT.write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")
        browser.close()
    print("done")


if __name__ == "__main__":
    main()
