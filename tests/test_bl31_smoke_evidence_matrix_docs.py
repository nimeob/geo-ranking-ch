from pathlib import Path


def test_bl31_smoke_evidence_matrix_runbook_contains_required_commands_and_fields():
    doc = Path("docs/testing/bl31-smoke-evidence-matrix.md")
    assert doc.exists(), "Runbook fehlt: docs/testing/bl31-smoke-evidence-matrix.md"

    text = doc.read_text(encoding="utf-8")

    required_snippets = [
        "scripts/run_bl31_split_deploy.py --mode api",
        "scripts/run_bl31_split_deploy.py --mode ui",
        "scripts/run_bl31_split_deploy.py --mode both",
        "scripts/check_bl31_smoke_evidence_matrix.py",
        "taskDefinitionBefore",
        "taskDefinitionAfter",
        "timestampUtc",
        "result",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in text]
    assert not missing, f"BL-31 Smoke-/Evidence-Matrix-Runbook unvollständig, fehlend: {missing}"
