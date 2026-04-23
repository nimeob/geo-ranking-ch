from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_issue_986_webkit_smoke.mjs"


def test_webkit_smoke_script_extracts_missing_libraries_from_launch_error() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        "function extractMissingWebkitLibraries(message)",
        "Missing libraries:",
        "const installHint = buildWebkitInstallHint();",
        "webkitMissingLibraries = extractMissingWebkitLibraries(normalized.message)",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert not missing, f"run_issue_986_webkit_smoke.mjs fehlt Snippets: {missing}"


def test_webkit_smoke_script_emits_structured_runtime_dependency_hints() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        "function buildWebkitInstallHint()",
        "function hasAptPackageManager()",
        "WEBKIT_INSTALL_WITH_DEPS_HINT",
        "WEBKIT_INSTALL_BASE_HINT",
        "playwright.dev/docs/browsers#install-system-dependencies",
        "webkitMissingLibraries: Array.isArray(launch.webkitMissingLibraries) ? launch.webkitMissingLibraries : []",
        "webkitInstallHint: launch.webkitInstallHint || buildWebkitInstallHint()",
        "hint=${installHint}",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert not missing, f"Runtime-Hints fehlen im Script: {missing}"


def test_webkit_smoke_script_handles_missing_playwright_dependency_with_actionable_hint() -> (
    None
):
    content = SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        "class PlaywrightDependencyError extends Error",
        "async function loadPlaywrightBindings()",
        "await import('playwright')",
        "Playwright dependency fehlt oder ist nicht ladbar",
        "buildWebkitInstallHint()",
        "const { chromium, webkit, devices } = await loadPlaywrightBindings();",
        "playwrightDependencyMissing: false",
        "browser: playwrightDependencyMissing ? 'playwright-dependency-missing' : 'unknown'",
        "limitations: playwrightDependencyMissing",
        "Playwright dependency fehlt. hint=${playwrightInstallHint}",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert (
        not missing
    ), f"Playwright-Missing-Dependency-Hints fehlen im Script: {missing}"
    assert "import { chromium, devices, webkit } from 'playwright';" not in content


def test_webkit_smoke_script_has_base_url_reachability_preflight() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        "BASE_URL_PROBE_TIMEOUT_MS",
        "class BaseUrlReachabilityError extends Error",
        "function classifyConnectivityReason(error)",
        "function buildBaseUrlReachabilityHint(targetUrl, reasonCode)",
        "async function assertBaseUrlReachable(targetUrl, timeoutMs)",
        "await assertBaseUrlReachable(targetUrl, baseUrlProbeTimeoutMs);",
        "tls_cert_has_expired",
        "tls_hostname_mismatch",
        "tls_untrusted_ca",
        "TLS-Zertifikat ist abgelaufen",
        "BASE_URL nicht erreichbar",
        "hint=${hint}",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert not missing, f"BASE_URL-Preflight fehlt im WebKit-Smoke-Script: {missing}"


def test_webkit_smoke_script_accepts_legacy_cli_overrides_for_base_url_and_output() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        "case '--base-url':",
        "case '--evidence-json':",
        "case '--json-out':",
        "case '--headless':",
        "const baseUrl = String(cli.baseUrl || process.env.BASE_URL || DEFAULT_BASE_URL).trim() || DEFAULT_BASE_URL;",
        "const outputJsonPath = (() => {",
        "const outJson = outputJsonPath || path.join(outDir, `issue-986-webkit-smoke-${stamp}.json`);",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert not missing, f"CLI-Override-Kompatibilität fehlt im WebKit-Smoke-Script: {missing}"


def test_webkit_smoke_script_canonicalizes_legacy_dev_hosts() -> None:
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
    assert not missing, f"BASE_URL-Kanonisierung fehlt im WebKit-Smoke-Script: {missing}"


def test_webkit_smoke_script_resolves_repo_root_from_script_location() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    required_snippets = [
        "import { fileURLToPath } from 'node:url';",
        "const scriptPath = fileURLToPath(import.meta.url);",
        "const scriptDir = path.dirname(scriptPath);",
        "const repoRoot = path.resolve(scriptDir, '..');",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in content]
    assert not missing, f"repoRoot-Resolution fehlt im WebKit-Smoke-Script: {missing}"
