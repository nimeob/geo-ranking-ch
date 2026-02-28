from pathlib import Path


def test_bl334_split_smokes_script_contains_api_ui_entrypoints_and_health_checks() -> None:
    script = Path("scripts/check_bl334_split_smokes.sh")
    assert script.exists(), "Smoke-Script fehlt: scripts/check_bl334_split_smokes.sh"

    text = script.read_text(encoding="utf-8")

    required_snippets = [
        "python -m src.api.web_service",
        "python -m src.ui.service",
        "/health",
        "/healthz",
        '"result": "pass"',
    ]

    missing = [snippet for snippet in required_snippets if snippet not in text]
    assert not missing, f"BL-334 Split-Smoke-Script unvollständig, fehlend: {missing}"
