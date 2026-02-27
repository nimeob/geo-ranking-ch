from pathlib import Path


def test_tls_migration_runbook_contains_required_sections_and_baseline():
    doc = Path("docs/TLS_CERTIFICATE_MIGRATION_RUNBOOK.md")
    assert doc.exists(), "Runbook fehlt: docs/TLS_CERTIFICATE_MIGRATION_RUNBOOK.md"

    text = doc.read_text(encoding="utf-8")

    required_snippets = [
        "Dev (self-signed)",
        "Prod/Stage (official cert)",
        "TLS 1.2",
        "TLS 1.3",
        "HSTS",
        "Rotation",
        "Rollback",
        "Incident",
        "AWS ACM",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in text]
    assert not missing, f"TLS-Migrations-Runbook unvollständig, fehlend: {missing}"
