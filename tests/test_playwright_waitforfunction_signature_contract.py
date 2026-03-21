from __future__ import annotations

from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
SCRIPT_SUFFIXES = (".js", ".mjs", ".cjs")


def _iter_wait_for_function_calls(source: str):
    token = "waitForFunction("
    cursor = 0

    while True:
        start = source.find(token, cursor)
        if start < 0:
            return

        open_paren = source.find("(", start)
        i = open_paren + 1
        depth = 1
        quote: str | None = None
        escaped = False

        while i < len(source):
            ch = source[i]

            if quote is not None:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == quote:
                    quote = None
                i += 1
                continue

            if ch in {'"', "'", "`"}:
                quote = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    yield source[open_paren + 1 : i]
                    cursor = i + 1
                    break
            i += 1
        else:
            return


def _split_top_level_args(call_args: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    paren = bracket = brace = 0
    quote: str | None = None
    escaped = False

    for ch in call_args:
        if quote is not None:
            buf.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue

        if ch in {'"', "'", "`"}:
            quote = ch
            buf.append(ch)
            continue

        if ch == "(":
            paren += 1
        elif ch == ")":
            paren -= 1
        elif ch == "[":
            bracket += 1
        elif ch == "]":
            bracket -= 1
        elif ch == "{":
            brace += 1
        elif ch == "}":
            brace -= 1

        if ch == "," and paren == 0 and bracket == 0 and brace == 0:
            parts.append("".join(buf).strip())
            buf = []
            continue

        buf.append(ch)

    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def test_wait_for_function_timeout_options_are_not_passed_as_second_argument() -> None:
    bad_calls: list[str] = []

    for script in sorted(SCRIPTS_DIR.rglob("*")):
        if script.suffix not in SCRIPT_SUFFIXES:
            continue

        content = script.read_text(encoding="utf-8")
        for call in _iter_wait_for_function_calls(content):
            args = _split_top_level_args(call)
            if len(args) < 2:
                continue

            second = args[1].strip()
            if not second.startswith("{"):
                continue
            if not re.search(r"\btimeout\s*:", second):
                continue

            bad_calls.append(f"{script.relative_to(REPO_ROOT)} :: waitForFunction(..., {{timeout: ...}}, ...)")

    assert not bad_calls, "Playwright waitForFunction timeout options must be 3rd arg. Violations:\n" + "\n".join(bad_calls)
