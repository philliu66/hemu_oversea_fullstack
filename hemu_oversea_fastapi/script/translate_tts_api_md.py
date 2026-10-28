"""把 tts_API.md 译成 tts_API.zh.md。

字段名、枚举、路径、代码、URL 保持原文；说明文字用必应翻译。
翻译缓存写在 script/_tts_translate_cache.json，中断后可续跑。

用法:
  python script/translate_tts_api_md.py
  python script/translate_tts_api_md.py --count
"""

from __future__ import annotations

import json
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tts_API.md"
DST = ROOT / "tts_API.zh.md"
CACHE_PATH = Path(__file__).resolve().parent / "_tts_translate_cache.json"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
SEP = "<sep/>"
MAX_PACK = 1600

EXACT = {
    "Introduction": "简介",
    "Overview": "概述",
    "Query parameters": "查询参数",
    "Header parameters": "请求头参数",
    "Endpoint-specific common identifiers": "接口级公共标识",
    "Step-by-step breakdown": "分步说明",
    "Request Query Parameters": "请求查询参数",
    "Request Body Parameters": "请求体参数",
    "Request Path Parameters": "请求路径参数",
    "Request Header Parameters": "请求头参数",
    "Response Parameters": "响应参数",
    "Error Code": "错误码",
    "Function Description": "功能说明",
    "Common Parameters": "公共参数",
    "Properties": "属性",
    "Type": "类型",
    "Require": "是否必须",
    "Required": "是否必须",
    "Sample": "示例",
    "Properties description": "属性说明",
    "Parameter": "参数",
    "Location": "位置",
    "Description": "说明",
    "Message": "信息",
    "Code": "错误码",
    "Possible values": "可选值",
    "Possible values:": "可选值：",
    "Changelog": "更新记录",
    "Prerequisites": "前提条件",
    "Best practices": "最佳实践",
    "FAQ": "常见问题",
    "Required parameters": "必填参数",
    "Key response fields": "关键响应字段",
    "Note": "注意",
    "Important": "重要",
    "Warning": "警告",
}

PHRASES = [
    ("category asset cipher", "类目资产密文"),
    ("shop cipher", "店铺密文"),
    ("refresh token", "刷新令牌"),
    ("access token", "访问令牌"),
    ("app secret", "应用密钥"),
    ("request header", "请求头"),
    ("query parameter", "查询参数"),
    ("query string", "查询字符串"),
    ("request body", "请求体"),
    ("response body", "响应体"),
    ("status code", "状态码"),
]

FENCE_RE = re.compile(r"```[\s\S]*?```", re.M)
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*?)([ \t]+\{#[^}]+\})?[ \t]*$")
PROTECT_RE = re.compile(
    r"`[^`\n]*`"
    r"|!\[[^\]]*\]\([^)]+\)"
    r"|https?://[^\s)]+"
    r"|\{#[^}]+\}"
    r"|<[^>\n]+>"
    r"|[\u4e00-\u9fff]+"
    r"|\b[A-Z][A-Z0-9_]{2,}\b"
    r"|/(?:[\w{}._-]+/)*[\w{}._-]+"
)
PLACEHOLDER_RE = re.compile(r"§\d+§")
WORD_RE = re.compile(r"[A-Za-z]{2,}")


def needs_translation(text: str) -> bool:
    return bool(WORD_RE.search(text))


def mask(text: str) -> tuple[str, list[str]]:
    slots: list[str] = []

    def repl(match: re.Match[str]) -> str:
        slots.append(match.group(0))
        return f"§{len(slots) - 1}§"

    return PROTECT_RE.sub(repl, text), slots


def unmask(text: str, slots: list[str]) -> str:
    def repl(match: re.Match[str]) -> str:
        idx = int(match.group(0)[1:-1])
        if 0 <= idx < len(slots):
            return slots[idx]
        return match.group(0)

    return PLACEHOLDER_RE.sub(repl, text)


def apply_phrases(text: str) -> str:
    for src, dst in PHRASES:
        text = re.sub(re.escape(src), dst, text, flags=re.I)
    return text


def bare_key(text: str) -> str:
    return text.strip().strip("*").strip()


def is_identifier_cell(text: str) -> bool:
    value = bare_key(text)
    if not value:
        return True
    if value in EXACT:
        return False
    if re.fullmatch(r"[\^*`\w./\[\]{}-]+", value):
        return True
    if re.fullmatch(r"[A-Z0-9_]{2,}", value):
        return True
    if re.fullmatch(r"[\d.:+-]+", value):
        return True
    if " " not in value and len(value) > 24:
        return True
    return False


def is_table_separator(line: str) -> bool:
    stripped = line.strip()
    return bool(re.fullmatch(r"\|[\s|:-]+\|", stripped)) and "-" in stripped


def split_table_row(line: str) -> list[str] | None:
    if is_table_separator(line):
        return None
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    inner = stripped[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    cells: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(inner):
        if inner[i] == "\\" and i + 1 < len(inner):
            buf.append(inner[i : i + 2])
            i += 2
            continue
        if inner[i] == "|":
            cells.append("".join(buf))
            buf = []
        else:
            buf.append(inner[i])
        i += 1
    cells.append("".join(buf))
    return cells


def prepare(text: str) -> str | None:
    """返回需要发给翻译接口的掩码文本；不需要翻译时返回 None。"""
    key = bare_key(text)
    if key in EXACT:
        return None
    if is_identifier_cell(text):
        return None
    masked, _slots = mask(text)
    masked = apply_phrases(masked)
    if not needs_translation(masked):
        return None
    return masked


def restore_exact_or_original(text: str) -> str:
    key = bare_key(text)
    if key in EXACT:
        return text.replace(key, EXACT[key], 1)
    masked, slots = mask(text)
    masked = apply_phrases(masked)
    if not needs_translation(masked):
        return unmask(masked, slots)
    return text


class Bing:
    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.lock = threading.Lock()
        self.sfx = 0
        self.refresh()

    def refresh(self) -> None:
        page_url = "https://cn.bing.com/translator?from=en&to=zh-Hans"
        req = urllib.request.Request(page_url, headers={"User-Agent": UA})
        html = self.opener.open(req, timeout=30).read().decode("utf-8", "replace")
        helper = re.search(r'params_AbusePreventionHelper\s*=\s*\[(\d+),"([^"]+)"', html)
        if not helper:
            raise RuntimeError("未拿到必应翻译 token")
        self.key = helper.group(1)
        self.token = helper.group(2)
        ig = re.search(r'IG:"([A-F0-9]+)"', html)
        if not ig:
            raise RuntimeError("未拿到必应 IG")
        self.ig = ig.group(1)

    def translate(self, text: str) -> str:
        last_error = ""
        for attempt in range(3):
            with self.lock:
                self.sfx += 1
                sfx = self.sfx
                token, key, ig = self.token, self.key, self.ig
            form = urllib.parse.urlencode(
                {
                    "fromLang": "en",
                    "to": "zh-Hans",
                    "tone": "Casual",
                    "text": text,
                    "token": token,
                    "key": key,
                }
            ).encode()
            url = (
                "https://cn.bing.com/ttranslatev3?isVertical=1&&IG="
                f"{ig}&IID=translator.5023&SFX={sfx}"
            )
            req = urllib.request.Request(
                url,
                data=form,
                headers={
                    "User-Agent": UA,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": "https://cn.bing.com/translator?from=en&to=zh-Hans",
                },
            )
            try:
                raw = self.opener.open(req, timeout=40).read().decode()
                data = json.loads(raw)
                return data[0]["translations"][0]["text"]
            except Exception as exc:
                last_error = str(exc)
                time.sleep(0.8 * (attempt + 1))
                try:
                    with self.lock:
                        self.refresh()
                except Exception as refresh_exc:
                    last_error = f"{last_error} / refresh {refresh_exc}"
        raise RuntimeError(last_error)


def load_cache() -> dict[str, str]:
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def save_cache(cache: dict[str, str]) -> None:
    tmp = CACHE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CACHE_PATH)


def pack(items: list[str]) -> list[list[str]]:
    groups: list[list[str]] = []
    current: list[str] = []
    size = 0
    for item in items:
        extra = len(item) + len(SEP) + 2
        if extra > MAX_PACK:
            if current:
                groups.append(current)
                current = []
                size = 0
            groups.append([item])
            continue
        if current and size + extra > MAX_PACK:
            groups.append(current)
            current = []
            size = 0
        current.append(item)
        size += extra
    if current:
        groups.append(current)
    return groups


def translate_group(bing: Bing, group: list[str]) -> dict[str, str]:
    if len(group) == 1:
        try:
            return {group[0]: bing.translate(group[0])}
        except Exception as exc:
            print(f"  fail one: {exc}")
            return {group[0]: group[0]}
    joined = f"\n{SEP}\n".join(group)
    try:
        out = bing.translate(joined)
    except Exception as exc:
        print(f"  fail pack: {exc}")
        return {item: item for item in group}
    parts = [part.strip("\n") for part in out.split(SEP)]
    if len(parts) != len(group):
        found: dict[str, str] = {}
        for item in group:
            try:
                found[item] = bing.translate(item)
            except Exception:
                found[item] = item
        return found
    return dict(zip(group, parts, strict=True))


def fill_cache(pending: list[str], cache: dict[str, str]) -> None:
    groups = pack(pending)
    print(f"translate packs={len(groups)} strings={len(pending)}")
    bings = [Bing() for _ in range(3)]
    lock = threading.Lock()
    done = 0

    def job(index: int, group: list[str]) -> dict[str, str]:
        return translate_group(bings[index % len(bings)], group)

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(job, i, group) for i, group in enumerate(groups)]
        for future in as_completed(futures):
            found = future.result()
            with lock:
                cache.update(found)
                done += 1
                if done % 20 == 0 or done == len(groups):
                    save_cache(cache)
                    print(f"  packs {done}/{len(groups)} cache={len(cache)}")
    save_cache(cache)


def iter_chunks(masked: str) -> list[str]:
    if len(masked) <= MAX_PACK:
        return [masked]
    groups: list[str] = []
    current: list[str] = []
    size = 0
    for part in masked.split("\n"):
        if len(part) > MAX_PACK:
            if current:
                groups.append("\n".join(current))
                current = []
                size = 0
            for index in range(0, len(part), MAX_PACK):
                groups.append(part[index : index + MAX_PACK])
            continue
        extra = len(part) + 1
        if current and size + extra > MAX_PACK:
            groups.append("\n".join(current))
            current = []
            size = 0
        current.append(part)
        size += extra
    if current:
        groups.append("\n".join(current))
    return groups


def convert_visible(text: str, cache: dict[str, str] | None) -> str:
    key = bare_key(text)
    if key in EXACT:
        return text.replace(key, EXACT[key], 1)
    if is_identifier_cell(text):
        return text
    masked, slots = mask(text)
    masked = apply_phrases(masked)
    if not needs_translation(masked):
        return unmask(masked, slots)
    pieces = iter_chunks(masked)
    if cache is None:
        COLLECT.update(pieces)
        return text
    out: list[str] = []
    for piece in pieces:
        translated = cache.get(piece, piece)
        if translated.count("§") != piece.count("§"):
            translated = piece
        out.append(translated)
    return unmask("\n".join(out), slots)


COLLECT: set[str] = set()


def convert_line(line: str, cache: dict[str, str] | None) -> str:
    heading = HEADING_RE.match(line)
    if heading:
        marks, title, anchor = heading.group(1), heading.group(2), heading.group(3) or ""
        return f"{marks} {convert_visible(title, cache).strip()}{anchor}"
    cells = split_table_row(line)
    if cells is not None:
        converted = [convert_visible(cell, cache) for cell in cells]
        return "| " + " | ".join(cell.strip() for cell in converted) + " |"
    return convert_visible(line, cache)


def convert_prose(text: str, cache: dict[str, str] | None) -> str:
    lines = text.split("\n")
    out: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if not buf:
            return
        block = "\n".join(buf)
        out.append(convert_visible(block, cache))
        buf.clear()

    for line in lines:
        if (
            HEADING_RE.match(line)
            or is_table_separator(line)
            or split_table_row(line) is not None
            or not line.strip()
        ):
            flush()
            if not line.strip() or is_table_separator(line):
                out.append(line if line.strip() else "")
            else:
                out.append(convert_line(line, cache))
        else:
            buf.append(line)
    flush()
    return "\n".join(out)


def convert_document(text: str, cache: dict[str, str] | None) -> str:
    parts: list[str] = []
    pos = 0
    for match in FENCE_RE.finditer(text):
        parts.append(convert_prose(text[pos : match.start()], cache))
        parts.append(match.group(0))
        pos = match.end()
    parts.append(convert_prose(text[pos:], cache))
    return "".join(parts)


def main() -> None:
    source = SRC.read_text(encoding="utf-8")
    COLLECT.clear()
    convert_document(source, None)
    pending = sorted(item for item in COLLECT if item not in load_cache())
    cache = load_cache()
    print(f"unique={len(COLLECT)} cached={len(COLLECT) - len(pending)} pending={len(pending)}")
    if "--count" in sys.argv:
        return
    if pending:
        fill_cache(pending, cache)
    cache = load_cache()
    rendered = convert_document(source, cache)
    note = (
        "> 本文是 `tts_API.md` 的中文译本。字段名、枚举值、路径、代码和 URL 保持原文；"
        "说明文字由机器翻译，联调时以官网英文原文为准。\n\n"
    )
    if not rendered.startswith(note):
        rendered = note + rendered
    DST.write_text(rendered, encoding="utf-8")
    print(f"wrote {DST}")


if __name__ == "__main__":
    main()
