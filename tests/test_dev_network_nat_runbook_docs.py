from pathlib import Path


DOC = Path("docs/DEV_NETWORK_NAT_ROLLOUT_RUNBOOK.md")


def test_nat_runbook_exists() -> None:
    assert DOC.exists(), "Runbook fehlt: docs/DEV_NETWORK_NAT_ROLLOUT_RUNBOOK.md"


def test_nat_runbook_has_required_sections() -> None:
    text = DOC.read_text(encoding="utf-8")
    required = [
        "# Dev Network NAT Rollout Runbook",
        "[#885](https://github.com/nimeob/geo-ranking-ch/issues/885)",
        "## Preflight",
        "## Import-Pfad (wenn Ressourcen bereits existieren)",
        "## Plan",
        "## Apply",
        "## Post-Checks",
        "## Rollback / Safety",
    ]
    missing = [marker for marker in required if marker not in text]
    assert not missing, f"NAT-Runbook unvollständig, fehlend: {missing}"


def test_nat_runbook_contains_key_commands() -> None:
    text = DOC.read_text(encoding="utf-8")
    required_cmds = [
        "terraform -chdir=\"${TF_DIR}\" import aws_nat_gateway.dev[0]",
        "terraform -chdir=\"${TF_DIR}\" plan",
        "terraform -chdir=\"${TF_DIR}\" apply",
        "aws ec2 describe-route-tables",
    ]
    missing = [cmd for cmd in required_cmds if cmd not in text]
    assert not missing, f"Wichtige NAT-Runbook-Befehle fehlen: {missing}"
