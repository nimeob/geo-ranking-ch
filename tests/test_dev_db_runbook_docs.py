from pathlib import Path


DOC = Path("docs/DEV_DB_RUNBOOK.md")


def test_dev_db_runbook_exists() -> None:
    assert DOC.exists(), "Runbook fehlt: docs/DEV_DB_RUNBOOK.md"


def test_dev_db_runbook_has_required_sections() -> None:
    text = DOC.read_text(encoding="utf-8")
    required = [
        "# Dev DB Runbook",
        "[#859](https://github.com/nimeob/geo-ranking-ch/issues/859)",
        "## Überblick",
        "## Verbindung herstellen",
        "## Credentials",
        "## Migrationen",
        "## Passwort-Rotation",
        "## Backup & Restore",
        "## Troubleshooting",
        "## Cleanup",
    ]
    missing = [marker for marker in required if marker not in text]
    assert not missing, f"DEV_DB_RUNBOOK unvollständig, fehlend: {missing}"


def test_dev_db_runbook_contains_key_commands() -> None:
    text = DOC.read_text(encoding="utf-8")
    required_cmds = [
        "aws secretsmanager get-secret-value",
        "aws ecs describe-task-definition",
        "aws ssm start-session",
        "psql",
        "terraform plan -destroy",
    ]
    missing = [cmd for cmd in required_cmds if cmd not in text]
    assert not missing, f"Wichtige Runbook-Kommandos fehlen: {missing}"
