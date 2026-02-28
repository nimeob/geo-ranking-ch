from pathlib import Path


def test_bl335_frontdoor_redeploy_acceptance_runbook_contains_required_checks():
    doc = Path("docs/testing/bl335-frontdoor-redeploy-acceptance-runbook.md")
    assert doc.exists(), "Runbook fehlt: docs/testing/bl335-frontdoor-redeploy-acceptance-runbook.md"

    text = doc.read_text(encoding="utf-8")

    required_snippets = [
        "# BL-335 Frontdoor Redeploy-Abnahme (WP3 / Issue #379)",
        "## 1) HTTPS-Health über Frontdoor verifizieren",
        "## 2) Runtime-Guardrail (UI_API_BASE_URL + CORS) prüfen",
        "scripts/check_bl335_frontdoor_runtime.py",
        "--expected-api-base-url",
        "## 3) API-only Redeploy mit expliziten Smoke-URLs",
        "--mode api",
        "--smoke-api-base-url",
        "--smoke-app-base-url",
        "## 4) UI-only Redeploy mit expliziten Smoke-URLs",
        "--mode ui",
        "## 6) Parent-Abschluss-Checkliste (#376)",
        "### BL-335 Abschlussnachweis (WP3)",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in text]
    assert not missing, f"BL-335 Redeploy-Abnahme-Runbook unvollständig, fehlend: {missing}"
