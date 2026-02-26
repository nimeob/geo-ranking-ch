import re
import subprocess
import unittest
from pathlib import Path
from urllib.parse import unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def _iter_tracked_markdown_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "ls-files", "*.md"],
        text=True,
    )
    return [REPO_ROOT / line.strip() for line in output.splitlines() if line.strip()]


def _strip_optional_title(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()

    if " " in target:
        target = target.split(" ", 1)[0]

    return target.strip()


def _is_external_or_ignored_target(target: str) -> bool:
    parsed = urlparse(target)
    if parsed.scheme in {"http", "https", "mailto", "tel", "data"}:
        return True
    if target.startswith("javascript:"):
        return True
    return False


def _slugify_heading(text: str) -> str:
    value = text.strip().lower().replace("`", "")
    value = re.sub(r"[^\w\-\s\u0080-\uffff]", "", value)
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value


def _build_anchor_index(markdown_path: Path) -> set[str]:
    anchors: set[str] = set()
    seen: dict[str, int] = {}

    for line in markdown_path.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if not heading:
            continue
        base = _slugify_heading(heading.group(1))
        if not base:
            continue

        count = seen.get(base, 0)
        seen[base] = count + 1
        anchor = f"{base}-{count}" if count > 0 else base
        anchors.add(anchor)

    return anchors


def _iter_markdown_links(markdown_path: Path):
    in_fenced_block = False

    for line_number, line in enumerate(
        markdown_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if re.match(r"^\s*```", line):
            in_fenced_block = not in_fenced_block
            continue

        if in_fenced_block:
            continue

        for match in MARKDOWN_LINK_RE.finditer(line):
            yield line_number, match.group(1)


class TestMarkdownLinks(unittest.TestCase):
    def test_tracked_markdown_links_resolve(self):
        files = _iter_tracked_markdown_files()
        self.assertGreater(len(files), 0, msg="Keine Markdown-Dateien im Repo gefunden")

        anchor_cache: dict[Path, set[str]] = {}
        broken: list[str] = []

        for markdown_path in files:
            for line_number, raw_target in _iter_markdown_links(markdown_path):
                target = _strip_optional_title(raw_target)
                if not target:
                    continue

                if _is_external_or_ignored_target(target):
                    continue

                path_part, _, fragment = target.partition("#")
                path_part = unquote(path_part)
                fragment = unquote(fragment).strip().lower()

                if not path_part:
                    target_path = markdown_path
                elif path_part.startswith("/"):
                    target_path = (REPO_ROOT / path_part.lstrip("/")).resolve()
                else:
                    target_path = (markdown_path.parent / path_part).resolve()

                try:
                    target_path.relative_to(REPO_ROOT)
                except ValueError:
                    broken.append(
                        f"{markdown_path.relative_to(REPO_ROOT)}:{line_number} -> {target} "
                        f"(Ziel außerhalb des Repos)"
                    )
                    continue

                if not target_path.exists():
                    broken.append(
                        f"{markdown_path.relative_to(REPO_ROOT)}:{line_number} -> {target} "
                        f"(Datei fehlt: {target_path.relative_to(REPO_ROOT)})"
                    )
                    continue

                if target_path.is_dir():
                    broken.append(
                        f"{markdown_path.relative_to(REPO_ROOT)}:{line_number} -> {target} "
                        f"(Verweis auf Verzeichnis statt Datei)"
                    )
                    continue

                if fragment and target_path.suffix.lower() == ".md":
                    anchors = anchor_cache.setdefault(
                        target_path, _build_anchor_index(target_path)
                    )
                    if fragment not in anchors:
                        broken.append(
                            f"{markdown_path.relative_to(REPO_ROOT)}:{line_number} -> {target} "
                            f"(Anker '#{fragment}' fehlt in {target_path.relative_to(REPO_ROOT)})"
                        )

        if broken:
            self.fail("Defekte Markdown-Links gefunden:\n" + "\n".join(sorted(broken)))


if __name__ == "__main__":
    unittest.main()
