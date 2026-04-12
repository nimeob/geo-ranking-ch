from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_dev_ui_live_full_regression.mjs"


def test_full_regression_script_uses_hostname_guard_instead_of_origin_suffix_match() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "function normalizeHostname(value)" in content
    assert "function isSameHostname(urlObj, expectedHostname)" in content
    assert "if (!isSameHostname(url, base.hostname)) return;" in content
    assert "url.origin.endsWith(base.hostname)" not in content
