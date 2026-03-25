from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_issue_986_webkit_smoke.mjs"


def test_webkit_smoke_script_extracts_missing_libraries_from_launch_error() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        "function extractMissingWebkitLibraries(message)",
        "Missing libraries:",
        "const installHint = 'npx playwright install --with-deps webkit';",
        "webkitMissingLibraries = extractMissingWebkitLibraries(normalized.message)",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert not missing, f"run_issue_986_webkit_smoke.mjs fehlt Snippets: {missing}"


def test_webkit_smoke_script_emits_structured_runtime_dependency_hints() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        "webkitMissingLibraries: Array.isArray(launch.webkitMissingLibraries) ? launch.webkitMissingLibraries : []",
        "webkitInstallHint: launch.webkitInstallHint || 'npx playwright install --with-deps webkit'",
        "hint=${installHint}",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert not missing, f"Runtime-Hints fehlen im Script: {missing}"
