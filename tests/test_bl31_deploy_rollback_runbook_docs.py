from pathlib import Path


def test_bl31_deploy_rollback_runbook_contains_required_sections_and_evidence_template():
    doc = Path("docs/BL31_DEPLOY_ROLLBACK_RUNBOOK.md")
    assert doc.exists(), "Runbook fehlt: docs/BL31_DEPLOY_ROLLBACK_RUNBOOK.md"

    text = doc.read_text(encoding="utf-8")

    required_snippets = [
        "# BL-31 Deploy-/Rollback-Runbook (API + UI getrennt) — Issue #330",
        "## 2) API-only Deployment (service-lokal)",
        "## 3) UI-only Deployment (service-lokal)",
        "## 4) Kombiniertes Deployment (API + UI)",
        "## 5) Service-lokaler Rollback",
        "/health",
        "/healthz",
        "./scripts/run_bl31_routing_tls_smoke.sh",
        "## 6) Evidenzformat (Issue-/PR-Kommentar, verbindlich)",
        "Type: <deploy-api|deploy-ui|deploy-combined|rollback-api|rollback-ui>",
        "Smoke artifact: `artifacts/bl31/<timestamp>-<run-type>.json`",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in text]
    assert not missing, f"BL-31 Deploy-/Rollback-Runbook unvollständig, fehlend: {missing}"
