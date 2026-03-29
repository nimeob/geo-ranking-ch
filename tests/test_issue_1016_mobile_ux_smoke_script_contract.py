from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_issue_1016_mobile_ux_smoke.mjs"


def test_issue_1016_mobile_ux_smoke_has_base_url_reachability_preflight_and_structured_failure_payload() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        "BASE_URL_PROBE_TIMEOUT_MS",
        "class BaseUrlReachabilityError extends Error",
        "async function assertBaseUrlReachable(targetUrl, timeoutMs)",
        "await assertBaseUrlReachable(baseUrl, baseUrlProbeTimeoutMs);",
        "runError = normalizeError(error);",
        "issue-${issueNumber}-mobile-ux-smoke-${stamp}.json",
        "runError",
        "ok: false",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert not missing, f"run_issue_1016_mobile_ux_smoke.mjs fehlt Preflight/Failure-Snippets: {missing}"
