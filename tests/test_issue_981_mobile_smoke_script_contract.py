from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_issue_981_mobile_smoke.mjs"


def test_issue_981_mobile_smoke_has_base_url_reachability_preflight() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        "BASE_URL_PROBE_TIMEOUT_MS",
        "class BaseUrlReachabilityError extends Error",
        "function classifyConnectivityReason(error)",
        "function buildBaseUrlReachabilityHint(targetUrl, reasonCode)",
        "async function assertBaseUrlReachable(targetUrl, timeoutMs)",
        "await assertBaseUrlReachable(baseUrl, baseUrlProbeTimeoutMs);",
        "tls_cert_has_expired",
        "tls_hostname_mismatch",
        "tls_untrusted_ca",
        "TLS-Zertifikat ist abgelaufen",
        "BASE_URL nicht erreichbar",
        "hint=${hint}",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert (
        not missing
    ), f"run_issue_981_mobile_smoke.mjs fehlt Preflight-Snippets: {missing}"


def test_issue_981_mobile_smoke_accepts_legacy_cli_overrides() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        "case '--base-url':",
        "case '--evidence-json':",
        "case '--json-out':",
        "case '--headless':",
        "const baseUrl = String(cli.baseUrl || process.env.BASE_URL || DEFAULT_BASE_URL).trim() || DEFAULT_BASE_URL;",
        "const outputJsonPath = (() => {",
        "const outJson = outputJsonPath || path.join(outDir, `issue-981-mobile-e2e-smoke-${stamp}.json`);",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert not missing, f"run_issue_981_mobile_smoke.mjs fehlt CLI-Override-Kompatibilität: {missing}"
