from pathlib import Path


def test_gtm_validation_template_contains_required_sections():
    doc = Path("docs/testing/GTM_VALIDATION_SPRINT_TEMPLATE.md")
    assert doc.exists(), "Template fehlt: docs/testing/GTM_VALIDATION_SPRINT_TEMPLATE.md"

    text = doc.read_text(encoding="utf-8")
    required_snippets = [
        "## Interview-/Discovery-Template (pro Gespräch)",
        "## Rollen & Verantwortlichkeiten",
        "## Sprint-Synthese-Format",
        "## Entscheidungslog für BL-30-Priorisierung (verbindlich)",
        "## DoD für einen abgeschlossenen GTM-Sprint",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in text]
    assert not missing, f"GTM-Template unvollständig, fehlend: {missing}"


def test_gtm_decision_log_has_seed_decision_with_bl30_mapping():
    doc = Path("docs/testing/GTM_VALIDATION_DECISION_LOG.md")
    assert doc.exists(), "Decision Log fehlt: docs/testing/GTM_VALIDATION_DECISION_LOG.md"

    text = doc.read_text(encoding="utf-8")
    assert "GTM-DEC-001" in text, "Seed-Entscheidung GTM-DEC-001 fehlt"
    assert "BL-30.1" in text and "BL-30.2" in text, "BL-30-Ableitung fehlt im Decision Log"


def test_gtm_validation_template_references_wp3_cards_and_followup_template():
    doc = Path("docs/testing/GTM_VALIDATION_SPRINT_TEMPLATE.md")
    text = doc.read_text(encoding="utf-8")

    assert "docs/PRICING_VALIDATION_EXPERIMENT_CARDS_V1.md" in text
    assert "docs/testing/BL30_FOLLOWUP_ISSUE_TEMPLATE.md" in text


def test_packaging_hypotheses_reference_template_decision_log_and_wp3_artifacts():
    doc = Path("docs/PACKAGING_PRICING_HYPOTHESES.md")
    text = doc.read_text(encoding="utf-8")

    assert "docs/testing/GTM_VALIDATION_SPRINT_TEMPLATE.md" in text
    assert "docs/testing/GTM_VALIDATION_DECISION_LOG.md" in text
    assert "docs/PRICING_VALIDATION_EXPERIMENT_CARDS_V1.md" in text
    assert "docs/testing/BL30_FOLLOWUP_ISSUE_TEMPLATE.md" in text
