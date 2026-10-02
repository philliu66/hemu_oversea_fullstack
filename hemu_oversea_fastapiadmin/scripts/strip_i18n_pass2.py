#!/usr/bin/env python3
"""Second pass: remaining formatMessage / FormattedMessage → Chinese."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(r"E:\personal\projects\HeMuOversea\code\hemu_oversea_fastapiadmin")
SRC = ROOT / "src"

# Load zh-CN locale maps
locale: dict[str, str] = {}
for rel in ["src/locales/zh-CN/pages.ts", "src/locales/zh-CN/common.ts"]:
    text = (ROOT / rel).read_text(encoding="utf-8")
    for m in re.finditer(
        r"""['"]([^'"]+)['"]\s*:\s*(['"])(.*?)\2""",
        text,
        re.DOTALL,
    ):
        key, _, val = m.group(1), m.group(2), m.group(3)
        # unescape simple
        val = val.replace(r"\'", "'").replace(r"\"", '"').replace(r"\n", "\n")
        locale[key] = val


def js_str(s: str) -> str:
    if "'" in s and '"' not in s:
        return '"' + s.replace("\\", "\\\\").replace("\n", "\\n") + '"'
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n") + "'"


# FormattedMessage with id + defaultMessage (self-closing or with children ignored)
FM_RE = re.compile(
    r"""<FormattedMessage\s+([^>]*?)\s*(?:\/>|>\s*</FormattedMessage>)""",
    re.DOTALL,
)


def replace_formatted_message(content: str) -> tuple[str, int]:
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        attrs = m.group(1)
        dm = re.search(r"""defaultMessage\s*=\s*(['"`])(.*?)\1""", attrs, re.DOTALL)
        idm = re.search(r"""id\s*=\s*(['"`])(.*?)\1""", attrs, re.DOTALL)
        if dm:
            count += 1
            return "{" + js_str(dm.group(2)) + "}"
        if idm and idm.group(2) in locale:
            count += 1
            return "{" + js_str(locale[idm.group(2)]) + "}"
        return m.group(0)

    return FM_RE.sub(repl, content), count


# formatMessage({ id: 'x' }) without defaultMessage
ID_ONLY_RE = re.compile(
    r"""(?P<prefix>(?:intl|getIntl\(\))\.formatMessage)\(\s*\{\s*id\s*:\s*(?P<q>['"`])(?P<id>.*?)(?P=q)\s*\}\s*(?:,\s*(?P<values>\{.*?\}))?\s*\)""",
    re.DOTALL,
)


def replace_id_only(content: str) -> tuple[str, int]:
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        key = m.group("id")
        values = m.group("values")
        msg = locale.get(key)
        if msg is None:
            return m.group(0)
        count += 1
        if values and re.search(r"\{[A-Za-z_]", msg):
            # build template
            mapping = {
                p.group(1): p.group(2).strip()
                for p in re.finditer(
                    r"""([A-Za-z_][\w]*)\s*:\s*([^,}\n]+)""", values
                )
            }
            out = []
            last = 0
            for ph in re.finditer(r"\{([A-Za-z_][\w]*)\}", msg):
                out.append(
                    msg[last : ph.start()]
                    .replace("\\", "\\\\")
                    .replace("`", "\\`")
                    .replace("${", "\\${")
                )
                out.append("${" + mapping.get(ph.group(1), ph.group(1)) + "}")
                last = ph.end()
            out.append(
                msg[last:]
                .replace("\\", "\\\\")
                .replace("`", "\\`")
                .replace("${", "\\${")
            )
            return "`" + "".join(out) + "`"
        return js_str(msg)

    return ID_ONLY_RE.sub(repl, content), count


# Remaining with defaultMessage that first script missed (e.g. trailing commas / odd spacing)
CALL_RE = re.compile(
    r"""(?P<prefix>(?:intl|getIntl\(\))\.formatMessage)\(\s*\{(?P<body>.*?)\}\s*(?:,\s*(?P<values>\{.*?\}))?\s*\)""",
    re.DOTALL,
)
DEFAULT_RE = re.compile(
    r"""defaultMessage\s*:\s*(?P<q>['"`])(?P<msg>.*?)(?P=q)""",
    re.DOTALL,
)


def replace_with_default(content: str) -> tuple[str, int]:
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        body = m.group("body")
        values = m.group("values")
        dm = DEFAULT_RE.search(body)
        if not dm:
            # shorthand { id, defaultMessage }
            if re.search(r"\bdefaultMessage\b", body) and re.search(
                r"\bid\b", body
            ):
                # dynamic — leave for manual
                return m.group(0)
            return m.group(0)
        if dm.group("q") == "`":
            count += 1
            return f"`{dm.group('msg')}`"
        msg = dm.group("msg")
        count += 1
        if values and re.search(r"\{[A-Za-z_]", msg):
            mapping = {
                p.group(1): p.group(2).strip()
                for p in re.finditer(
                    r"""([A-Za-z_][\w]*)\s*:\s*([^,}\n]+)""", values
                )
            }
            out = []
            last = 0
            for ph in re.finditer(r"\{([A-Za-z_][\w]*)\}", msg):
                out.append(
                    msg[last : ph.start()]
                    .replace("\\", "\\\\")
                    .replace("`", "\\`")
                    .replace("${", "\\${")
                )
                out.append("${" + mapping.get(ph.group(1), ph.group(1)) + "}")
                last = ph.end()
            out.append(
                msg[last:]
                .replace("\\", "\\\\")
                .replace("`", "\\`")
                .replace("${", "\\${")
            )
            return "`" + "".join(out) + "`"
        return js_str(msg)

    return CALL_RE.sub(repl, content), count


def clean_imports(content: str) -> str:
    needs = {
        "useIntl": "useIntl(" in content,
        "getIntl": "getIntl(" in content,
        "FormattedMessage": "FormattedMessage" in content,
        "SelectLang": "SelectLang" in content,
    }

    def fix(m: re.Match) -> str:
        names = [n.strip() for n in m.group(1).split(",") if n.strip()]
        kept = []
        for n in names:
            if n in needs and not needs[n]:
                continue
            kept.append(n)
        if not kept:
            return ""
        return f"import {{ {', '.join(kept)} }} from '@umijs/max';\n"

    content = re.sub(
        r"""import\s*\{\s*([^}]+)\s*\}\s*from\s*['"]@umijs/max['"];?\s*\n""",
        fix,
        content,
    )
    if "intl." not in content and "intl?" not in content:
        content = re.sub(
            r"^\s*const\s+intl\s*=\s*(?:useIntl|getIntl)\(\)\s*;\s*\n",
            "",
            content,
            flags=re.MULTILINE,
        )
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content


def process(path: Path) -> int:
    original = path.read_text(encoding="utf-8")
    content = original
    total = 0
    content, n = replace_with_default(content)
    total += n
    content, n = replace_id_only(content)
    total += n
    content, n = replace_formatted_message(content)
    total += n
    content = clean_imports(content)
    if content != original:
        path.write_text(content, encoding="utf-8", newline="\n")
    return total


def main() -> None:
    total = 0
    for path in SRC.rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        if "locales" in path.parts:
            continue
        n = process(path)
        if n:
            print(f"{path.relative_to(SRC)}: {n}")
            total += n
    print(f"Done second pass: {total}")


if __name__ == "__main__":
    main()
