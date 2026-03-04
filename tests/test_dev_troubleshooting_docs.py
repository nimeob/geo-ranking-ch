from pathlib import Path
import re


def _extract_entry_sections(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"^##\s+(\d+)\)\s+(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    sections: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections.append((match.group(1), text[start:end]))
    return sections


def test_dev_troubleshooting_has_exactly_10_template_entries() -> None:
    doc = Path("docs/troubleshooting.md")
    assert doc.exists(), "Dev-Troubleshooting fehlt: docs/troubleshooting.md"

    text = doc.read_text(encoding="utf-8")
    entries = _extract_entry_sections(text)

    assert len(entries) == 10, f"Erwartet 10 Fehlerbilder, gefunden: {len(entries)}"

    expected_numbers = [str(i) for i in range(1, 11)]
    assert [n for n, _ in entries] == expected_numbers, "Fehlerbilder müssen 1..10 nummeriert sein."

    for number, body in entries:
        for marker in ("**Symptom**", "**Probable Cause**", "**Check**", "**Fix**"):
            assert marker in body, f"Eintrag #{number} fehlt Template-Baustein: {marker}"

        assert "```bash" in body or "```" in body, (
            f"Eintrag #{number} benötigt mindestens einen prüfbaren Kommando-/Log-Hinweis."
        )


def test_readme_links_dev_troubleshooting_doc() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "[docs/troubleshooting.md](docs/troubleshooting.md)" in readme
