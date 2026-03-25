from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "gui-webkit-smoke.yml"


def test_gui_webkit_workflow_requires_native_webkit_runtime() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")

    assert "npx playwright install --with-deps webkit" in content
    assert "REQUIRE_NATIVE_WEBKIT: \"1\"" in content
    assert 'BASE_URL="http://127.0.0.1:8877/gui" npm run smoke:gui:webkit' in content
