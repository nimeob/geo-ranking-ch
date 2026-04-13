from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_issue_1016_mobile_ux_smoke.mjs"


def test_issue_1016_mobile_ux_smoke_has_base_url_reachability_preflight_and_structured_failure_payload() -> (
    None
):
    content = SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        "BASE_URL_PROBE_TIMEOUT_MS",
        "class BaseUrlReachabilityError extends Error",
        "function classifyConnectivityReason(error)",
        "async function assertBaseUrlReachable(targetUrl, timeoutMs)",
        "await assertBaseUrlReachable(targetUrl, baseUrlProbeTimeoutMs);",
        "tls_cert_has_expired",
        "tls_hostname_mismatch",
        "tls_untrusted_ca",
        "TLS-Zertifikat ist abgelaufen",
        "runError = normalizeError(error);",
        "issue-${issueNumber}-mobile-ux-smoke-${stamp}.json",
        "runError",
        "ok: false",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert (
        not missing
    ), f"run_issue_1016_mobile_ux_smoke.mjs fehlt Preflight/Failure-Snippets: {missing}"


def test_issue_1016_mobile_ux_smoke_accepts_legacy_cli_overrides() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        "case '--base-url':",
        "case '--evidence-json':",
        "case '--json-out':",
        "case '--headless':",
        "const baseUrl = String(cli.baseUrl || process.env.BASE_URL || DEFAULT_BASE_URL).trim() || DEFAULT_BASE_URL;",
        "const outputJsonPath = (() => {",
        "const outJson = outputJsonPath || path.join(outDir, `issue-${issueNumber}-mobile-ux-smoke-${stamp}.json`);",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert not missing, f"run_issue_1016_mobile_ux_smoke.mjs fehlt CLI-Override-Kompatibilität: {missing}"


def test_issue_1016_mobile_ux_smoke_canonicalizes_legacy_dev_hosts() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        "const LEGACY_DEV_UI_HOSTS = new Set(['dev.georanking.ch', 'dev.geo-ranking.ch']);",
        "function normalizeUiBaseUrl(rawBaseUrl)",
        "legacy_dev_non_www",
        "const targetUrl = baseUrlNormalization.value || baseUrl;",
        "targetUrlRequested: baseUrl",
        "baseUrlCanonicalizationReasons: baseUrlNormalization.reasons",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert not missing, f"run_issue_1016_mobile_ux_smoke.mjs fehlt BASE_URL-Kanonisierung: {missing}"
