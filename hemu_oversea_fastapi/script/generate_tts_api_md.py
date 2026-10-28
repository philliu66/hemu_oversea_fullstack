"""根据 Playwright 抓取的 TikTok 文档 JSON，生成 tts_API.md。"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRAPE = Path(__file__).resolve().parent / "_tts_doc_scrape"
OUT = ROOT / "tts_API.md"
DOC = "https://partner.tiktokshop.com/docv2/page"

DROP_TITLES = {
    "request sample",
    "response sample",
    "common parameters",
}
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
MULTI_BLANK = re.compile(r"\n{3,}")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def demote_headings(text: str) -> str:
    """嵌入的官网标题降成正文小标题，避免打乱手册自己的章节层级。"""
    return re.sub(r"(?m)^#{1,6}[ \t]+", "###### ", text)


def absolutize_links(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        label, href = match.group(1), match.group(2).strip()
        if href.startswith(("http://", "https://", "#", "mailto:")):
            return match.group(0)
        return f"[{label}]({DOC}/{href.lstrip('/')})"

    return LINK_RE.sub(repl, text)


def clean(text: str) -> str:
    text = COMMENT_RE.sub("", text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = absolutize_links(text)
    text = demote_headings(text)
    text = MULTI_BLANK.sub("\n\n", text)
    return text.strip()


def split_sections(content: str) -> list[tuple[str, str]]:
    content = content.replace("\r\n", "\n")
    chunks = re.split(r"\n(?=# )", content.strip())
    sections: list[tuple[str, str]] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if chunk.startswith("# "):
            first, _, rest = chunk.partition("\n")
            title = first[2:].strip()
            sections.append((title, rest.strip()))
        else:
            sections.append(("", chunk))
    return sections


def norm_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip().lower()


def section_body(sections: list[tuple[str, str]], *names: str) -> str:
    wanted = {n.lower() for n in names}
    for title, body in sections:
        if norm_title(title) in wanted:
            return body
    return ""


def meta_line(sections: list[tuple[str, str]], prefix: str) -> str:
    prefix_l = prefix.lower()
    for title, body in sections:
        if title.lower().startswith(prefix_l):
            value = title.split(":", 1)[-1].strip() if ":" in title else body.strip()
            value = value.strip("[]")
            return value.split("\n", 1)[0].strip()
    return ""


def keep_sections(sections: list[tuple[str, str]]) -> list[tuple[str, str]]:
    kept = []
    for title, body in sections:
        key = norm_title(title)
        if not title or key in DROP_TITLES:
            continue
        if key.startswith("path:") or key.startswith("method:"):
            continue
        if key in {"function description"}:
            continue
        if not body.strip():
            continue
        kept.append((title, clean(body)))
    return kept


def md_escape_cell(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def first_paragraph(text: str, limit: int = 700) -> str:
    text = clean(text)
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not parts:
        return ""
    para = " ".join(parts[0].split())
    if len(para) > limit:
        para = para[: limit - 1].rstrip() + "…"
    return para


def section_markdown(title: str, body: str) -> str:
    body = clean(body)
    if not body:
        return ""
    if title:
        return f"**{title}**\n\n{body}"
    return body


def scope_line(text: str) -> str:
    match = re.search(r"Required scope:\s*(.+)", text or "", re.I)
    if not match:
        return ""
    return " ".join(match.group(1).split())


def anchor(slug: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "-", slug)


def guide_block(slug: str) -> str:
    path = SCRAPE / "guides" / f"{slug}.json"
    if not path.exists():
        return f"*未抓到 `{slug}`。*\n"
    data = load_json(path)
    sections = split_sections(data.get("content") or "")
    chunks = []
    for title, text in sections:
        key = norm_title(title)
        if key in DROP_TITLES or "sample" in key:
            continue
        if title:
            chunks.append(f"#### {title}\n\n{clean(text)}")
        elif text:
            chunks.append(clean(text))
    rendered = "\n\n".join(c for c in chunks if c.strip())
    return rendered or "*页面无正文。*\n"


def header(api_count: int, module_count: int) -> str:
    return f"""# TikTok Shop 开放平台 API 手册（AI 联调版）

> 数据来源：官网文档站 [Partner Center](https://partner.tiktokshop.com/docv2/page/tts-developer-guide)。页面为 SPA，本手册由 Playwright 打开文档站后，拉取与页面相同的 `document/tree`、`document/detail` 整理而成。
> **用途**：给 AI / 开发者做接口对照——接口做什么、方法与路径、请求/响应字段、错误码。字段与枚举以各接口小节中的官网原文为准，不要另造取值。
> **收录**：API Reference 下全部接口文档 **{api_count}** 篇，分 **{module_count}** 个模块。同一能力若有多个日期版本，全部展开；日期更大不代表可以无差别替换旧版。
> **统一入口**：业务 API `https://open-api.tiktokglobalshop.com`（区域域名以控制台为准）。授权换 token 的地址见下方「授权」原文，不走这条业务域名。

---

## 〇、怎么读这份手册

1. 先看「一、调用约定」里的公共参数、签名、授权。各接口小节不再重复公共参数表。
2. 业务接口成功看响应体 `code == 0`。HTTP 200 不能单独当成成功。
3. 店铺级接口通常要带该店的 `shop_cipher`（来自 Get Authorized Shops）。一个 access_token 对应一次授权主体，不要跨店混用。
4. 参数表沿用官网层级：`^` 表示上一级对象的子字段，`^^` 再下一层。枚举写在「Properties description」里，只使用文档写出的值。
5. 请求示例 / 响应示例未收录，避免把示例值当成字段全集。需要示例时打开该接口的官网详情。

---

## 一、调用约定（官网原文）

下面是文档站对应页面的正文（已去掉请求/响应示例）。联调以这里的原文为准。

### 1.1 公共参数

官网：<{DOC}/common-parameters>

{guide_block("common-parameters")}

### 1.2 签名

官网：<{DOC}/sign-your-api-request>

{guide_block("sign-your-api-request")}

### 1.3 公共错误与限流

官网：<{DOC}/common-errors> · <{DOC}/rate-limits>

{guide_block("common-errors")}

{guide_block("rate-limits")}

### 1.4 授权

官网：<{DOC}/authorization-overview-202407> · <{DOC}/seller-authorization-guide> · <{DOC}/creator-authorization-guide> · <{DOC}/partner-authorization-guide>

{guide_block("authorization-overview-202407")}

{guide_block("seller-authorization-guide")}

{guide_block("creator-authorization-guide")}

{guide_block("partner-authorization-guide")}

### 1.5 版本、区域、Scope

官网：<{DOC}/api-versioning> · <{DOC}/regions-and-languages> · <{DOC}/access-scope>

{guide_block("api-versioning")}

{guide_block("regions-and-languages")}

{guide_block("access-scope")}

---

## 二、模块与接口详情

"""


def render_api(node: dict, detail: dict) -> str:
    slug = node.get("document_path") or ""
    content = detail.get("content") or ""
    sections = split_sections(content)
    path = meta_line(sections, "path")
    method = meta_line(sections, "method")
    desc = clean(section_body(sections, "Function Description"))
    desc = re.sub(r"\n+---\s*$", "", desc).strip()
    summary = first_paragraph(desc)
    scope = scope_line(desc)
    lines = [
        f"#### {detail.get('title') or node.get('name') or slug} {{#{anchor(slug)}}}",
        "",
        f"- **做什么**：{summary or '见官网详情'}",
    ]
    if method or path:
        lines.append(f"- **HTTP**：`{method or '?'} {path or '?'}`")
    if scope:
        lines.append(f"- **Required scope**：{scope}")
    lines.append(f"- **官网详情**：<{DOC}/{slug}>")
    lines.append("")
    extra = desc
    if summary and extra.startswith(summary[:80]):
        extra = ""
    else:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", desc) if p.strip()]
        if paragraphs:
            extra = "\n\n".join(paragraphs[1:]).strip()
    if extra:
        lines.append(extra)
        lines.append("")
    for title, body in keep_sections(sections):
        if norm_title(title) == "function description":
            continue
        lines.append(f"**{title}**")
        lines.append("")
        lines.append(body)
        lines.append("")
    # 没有标准章节时保留正文，避免漏定义
    if not keep_sections(sections) and not path:
        lines.append(clean(content))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def module_nodes(tree: list[dict]) -> list[tuple[dict, list[dict]]]:
    children: dict[str, list[dict]] = defaultdict(list)
    for node in tree:
        children[node.get("parent_id") or ""].append(node)
    root = next(n for n in tree if n.get("name") == "API Reference" and not n.get("parent_id"))

    def descendants(node_id: str) -> list[dict]:
        out: list[dict] = []
        for child in children.get(node_id, []):
            if child.get("is_dir"):
                out.extend(descendants(child["document_id"]))
            elif child.get("is_api_doc") and child.get("document_path"):
                out.append(child)
        return out

    modules = []
    for child in children.get(root["document_id"], []):
        if child.get("is_dir"):
            apis = descendants(child["document_id"])
            if apis:
                modules.append((child, apis))
        elif child.get("is_api_doc") and child.get("document_path"):
            modules.append((child, [child]))
    return modules


def render_webhook_section() -> str:
    folder = SCRAPE / "webhooks"
    if not folder.exists():
        return ""
    files = sorted(folder.glob("*.json"))
    if not files:
        return ""
    lines = [
        "## 三、Webhook 事件",
        "",
        f"官网总览：<{DOC}/tts-webhooks-overview> · 配置：<{DOC}/configuration-guide>",
        "",
        guide_block("tts-webhooks-overview"),
        "",
        guide_block("configuration-guide"),
        "",
        "### 事件列表",
        "",
    ]
    for path in files:
        data = load_json(path)
        slug = data.get("slug") or path.stem
        title = data.get("title") or slug
        summary = first_paragraph(data.get("content") or "", limit=280)
        lines.append(f"#### {title} {{#{anchor(slug)}}}")
        lines.append("")
        lines.append(f"- **做什么**：{summary or '见官网'}")
        lines.append(f"- **官网**：<{DOC}/{slug}>")
        lines.append("")
        sections = split_sections(data.get("content") or "")
        kept = keep_sections(sections)
        if kept:
            for title_s, body in kept:
                if "sample" in norm_title(title_s):
                    continue
                lines.append(f"**{title_s}**")
                lines.append("")
                lines.append(body)
                lines.append("")
        else:
            lines.append(clean(data.get("content") or ""))
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    tree = load_json(SCRAPE / "tree.json")["data"]["document_tree"]
    modules = module_nodes(tree)
    api_count = sum(len(apis) for _, apis in modules)
    parts = [header(api_count, len(modules))]
    toc = []
    for index, (mod, apis) in enumerate(modules, start=1):
        slug = mod.get("document_path") or anchor(mod["name"])
        toc.append(
            f"{index}. [{mod['name']}](#{anchor(slug)}) — **{len(apis)}**"
        )
    parts.append("\n".join(toc))
    parts.append("\n")
    missing = []
    for mod, apis in modules:
        slug = mod.get("document_path") or anchor(mod["name"])
        parts.append(f"### {mod['name']} {{#{anchor(slug)}}}\n")
        if mod.get("document_path"):
            parts.append(f"- **官网模块**：<{DOC}/{mod['document_path']}>\n")
        overview = []
        endpoints = []
        for api in apis:
            detail_path = SCRAPE / "details" / f"{api['document_path']}.json"
            if not detail_path.exists():
                missing.append(api["document_path"])
                continue
            detail = load_json(detail_path)
            content = detail.get("content") or ""
            if "# Path:" not in content and "# Path：" not in content:
                overview.append((api, detail))
            else:
                endpoints.append((api, detail))
        if overview:
            parts.append("**模块说明**（官网原文，不含示例）\n")
            for api, detail in overview:
                title = detail.get("title") or api["name"]
                parts.append(f"#### {title} {{#{anchor(api['document_path'])}}}\n")
                parts.append(f"- **官网**：<{DOC}/{api['document_path']}>\n")
                sections = split_sections(detail.get("content") or "")
                kept = keep_sections(sections)
                if kept:
                    for title_s, body in kept:
                        parts.append(f"**{title_s}**\n\n{body}\n")
                else:
                    parts.append(clean(detail.get("content") or ""))
                    parts.append("")
        parts.append("| 接口 | Method | Path | 官网 |")
        parts.append("| --- | --- | --- | --- |")
        rendered = []
        for api, detail in endpoints:
            sections = split_sections(detail.get("content") or "")
            method = meta_line(sections, "method") or ""
            path = meta_line(sections, "path") or ""
            title = detail.get("title") or api.get("name") or ""
            link = f"[{md_escape_cell(title)}](#{anchor(api['document_path'])})"
            parts.append(
                f"| {link} | `{md_escape_cell(method)}` | `{md_escape_cell(path)}` | [详情]({DOC}/{api['document_path']}) |"
            )
            rendered.append(render_api(api, detail))
        parts.append("")
        parts.extend(rendered)
        parts.append("")
    webhook = render_webhook_section()
    if webhook:
        parts.append(webhook)
    parts.append(
        "\n---\n\n## 四、维护\n\n"
        "```bash\n"
        "python script/scrape_tts_open_docs.py\n"
        "python script/generate_tts_api_md.py\n"
        "```\n\n"
        "重新抓取会跳过已存在的 JSON。要全量更新，先删 `script/_tts_doc_scrape/details`。\n"
    )
    OUT.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    print(f"wrote {OUT} apis={api_count} missing={len(missing)}")
    if missing:
        print("missing", ", ".join(missing[:20]))


if __name__ == "__main__":
    main()
