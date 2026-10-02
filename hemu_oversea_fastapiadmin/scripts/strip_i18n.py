#!/usr/bin/env python3
"""Replace intl.formatMessage / getIntl().formatMessage with Chinese defaultMessage literals."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(r"E:\personal\projects\HeMuOversea\code\hemu_oversea_fastapiadmin\src")

# intl.formatMessage({ ... }) or getIntl().formatMessage({ ... })
# with optional second values argument
CALL_RE = re.compile(
    r"""(?P<prefix>(?:intl|getIntl\(\))\.formatMessage)\(\s*\{(?P<body>.*?)\}\s*(?:,\s*(?P<values>\{.*?\}))?\s*\)""",
    re.DOTALL,
)

ID_RE = re.compile(r"""id\s*:\s*(?P<q>['"`])(?P<id>.*?)(?P=q)""", re.DOTALL)
DEFAULT_RE = re.compile(
    r"""defaultMessage\s*:\s*(?P<q>['"`])(?P<msg>.*?)(?P=q)""",
    re.DOTALL,
)
# values object like { max: ITEM_NAME_MAX_LENGTH, name: foo }
VALUE_PAIR_RE = re.compile(
    r"""(?P<key>[A-Za-z_][\w]*)\s*:\s*(?P<expr>[^,}\n]+?)(?=\s*[,}])"""
)


def unescape_js_string(s: str, quote: str) -> str:
    if quote == "`":
        # keep as-is for content, we'll decide quoting later
        return s
    return (
        s.replace(r"\\", "\\")
        .replace(r"\'", "'")
        .replace(r'\"', '"')
        .replace(r"\n", "\n")
    )


def to_js_string(s: str) -> str:
    """Emit a JS string literal; prefer single quotes unless content has them."""
    if "'" in s and '"' not in s:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if "`" in s or "${" in s or "\n" in s:
        # escape backticks and ${ for template if needed; for plain, use double
        return (
            '"'
            + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            + '"'
        )
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def apply_values(msg: str, values_src: str | None) -> str:
    """Convert ICU-like '{key}' placeholders using values object into JS expression."""
    if not values_src:
        if "{" in msg and "}" in msg:
            # leave as plain string if no values provided (static braces rare)
            return to_js_string(msg)
        return to_js_string(msg)

    pairs = list(VALUE_PAIR_RE.finditer(values_src))
    mapping: dict[str, str] = {}
    for m in pairs:
        mapping[m.group("key")] = m.group("expr").strip()

    # If message has placeholders, build template literal
    placeholders = re.findall(r"\{([A-Za-z_][\w]*)\}", msg)
    if not placeholders:
        return to_js_string(msg)

    # Build template
    out = []
    last = 0
    for m in re.finditer(r"\{([A-Za-z_][\w]*)\}", msg):
        out.append(msg[last : m.start()].replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${"))
        key = m.group(1)
        expr = mapping.get(key, key)
        out.append("${" + expr + "}")
        last = m.end()
    out.append(msg[last:].replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${"))
    return "`" + "".join(out) + "`"


def replace_calls(content: str) -> tuple[str, int]:
    count = 0

    def repl(match: re.Match) -> str:
        nonlocal count
        body = match.group("body")
        values = match.group("values")
        default_m = DEFAULT_RE.search(body)
        if not default_m:
            return match.group(0)  # keep as-is if no defaultMessage
        quote = default_m.group("q")
        msg = default_m.group("msg")
        # For template defaultMessage (rare), treat content literally
        if quote == "`":
            # already a template in source; just use it if no values
            if values:
                # too complex — leave unchanged
                return match.group(0)
            count += 1
            return f"`{msg}`"
        count += 1
        return apply_values(msg, values)

    new_content = CALL_RE.sub(repl, content)
    return new_content, count


def clean_unused_intl(content: str) -> str:
    # Remove `const intl = useIntl();` if intl no longer used
    if "intl." in content or "intl?" in content:
        return content
    content = re.sub(
        r"^\s*const\s+intl\s*=\s*useIntl\(\)\s*;\s*\n",
        "",
        content,
        flags=re.MULTILINE,
    )
    # Clean useIntl from imports
    def clean_import(m: re.Match) -> str:
        inner = m.group(1)
        parts = [p.strip() for p in inner.split(",")]
        parts = [p for p in parts if p and p != "useIntl" and p != "getIntl" and p != "FormattedMessage"]
        # Also remove getIntl/FormattedMessage if unused
        return m.group(0) if False else (
            m.group(0).split("{")[0] + "{ " + ", ".join(parts) + " }" + m.group(0)[m.end(1) + m.start(1) + 1 - m.start(1):]
        )

    # Simpler import cleanup
    def fix_umi_import(m: re.Match) -> str:
        names = [n.strip() for n in m.group(1).split(",")]
        kept = []
        for n in names:
            if n in {"useIntl", "getIntl", "FormattedMessage"}:
                # drop if not used in file
                if n == "useIntl" and "useIntl" not in content.replace(m.group(0), ""):
                    continue
                if n == "getIntl" and "getIntl" not in content.replace(m.group(0), ""):
                    continue
                if n == "FormattedMessage" and "FormattedMessage" not in content.replace(m.group(0), ""):
                    continue
                # after removing formatMessage, check remaining
                rest = content
                continue
            kept.append(n)
        # recompute based on final content needs — do second pass later
        return m.group(0)

    return content


def clean_imports(content: str) -> str:
    needs_use_intl = "useIntl(" in content
    needs_get_intl = "getIntl(" in content
    needs_fm = "FormattedMessage" in content

    def fix(m: re.Match) -> str:
        names = [n.strip() for n in m.group(1).split(",") if n.strip()]
        kept = []
        for n in names:
            if n == "useIntl" and not needs_use_intl:
                continue
            if n == "getIntl" and not needs_get_intl:
                continue
            if n == "FormattedMessage" and not needs_fm:
                continue
            kept.append(n)
        if not kept:
            return ""  # drop whole import
        return f"import {{ {', '.join(kept)} }} from '@umijs/max';"

    content = re.sub(
        r"""import\s*\{\s*([^}]+)\s*\}\s*from\s*['"]@umijs/max['"];?\s*\n""",
        fix,
        content,
    )
    # Remove empty leftover blank issues from dropped import
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content


def process_file(path: Path) -> int:
    original = path.read_text(encoding="utf-8")
    content, count = replace_calls(original)
    if count == 0 and "formatMessage" not in original:
        return 0
    # remove unused intl const
    if "intl." not in content:
        content = re.sub(
            r"^\s*const\s+intl\s*=\s*useIntl\(\)\s*;\s*\n",
            "",
            content,
            flags=re.MULTILINE,
        )
    content = clean_imports(content)
    if content != original:
        path.write_text(content, encoding="utf-8", newline="\n")
    return count


def main() -> None:
    total = 0
    files = 0
    for path in ROOT.rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        if "locales" in path.parts:
            continue
        n = process_file(path)
        if n:
            files += 1
            total += n
            print(f"{path.relative_to(ROOT)}: {n}")
    print(f"Done. {total} replacements in {files} files")


if __name__ == "__main__":
    main()
