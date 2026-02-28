from pathlib import Path


def test_bl337_internet_e2e_matrix_runbook_contains_required_sections_and_commands():
    doc = Path("docs/testing/bl337-internet-e2e-matrix.md")
    assert doc.exists(), "Runbook fehlt: docs/testing/bl337-internet-e2e-matrix.md"

    text = doc.read_text(encoding="utf-8")

    required_snippets = [
        "# BL-337 Internet-E2E Matrix (WP1 / Issue #396)",
        "## 1) Matrix erzeugen (Initialkatalog)",
        "scripts/manage_bl337_internet_e2e_matrix.py",
        "--output artifacts/bl337/latest-internet-e2e-matrix.json",
        "## 2) Matrix validieren (Schema + Summary)",
        "--validate artifacts/bl337/latest-internet-e2e-matrix.json",
        "--require-actual",
        "## 3) Pflichtfelder pro Testfall",
        "expectedResult",
        "actualResult",
        "status",
        "## 4) Einbettung in BL-337",
        "#397",
        "#398",
        "#399",
        "## 5) WP2 API-Frontdoor-Ausführung (Issue #397)",
        "scripts/run_bl337_api_frontdoor_e2e.py",
        "BL337_API_AUTH_TOKEN",
        "## 6) WP3 UI-Frontdoor-Ausführung (Issue #398)",
        "scripts/run_bl337_ui_frontdoor_e2e.py",
        "*-wp3-ui-frontdoor-e2e.json",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in text]
    assert not missing, f"BL-337 Matrix-Runbook unvollständig, fehlend: {missing}"
