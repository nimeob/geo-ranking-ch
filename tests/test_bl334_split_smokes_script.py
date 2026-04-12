from pathlib import Path


def test_bl334_split_smokes_script_contains_api_ui_entrypoints_and_health_checks() -> (
    None
):
    script = Path("scripts/check_bl334_split_smokes.sh")
    assert script.exists(), "Smoke-Script fehlt: scripts/check_bl334_split_smokes.sh"

    text = script.read_text(encoding="utf-8")

    required_snippets = [
        "python -m src.api.web_service",
        "python -m src.ui.service",
        "SMOKE_UI_APP_VERSION",
        "SMOKE_EXPECT_HEALTH_VERSION",
        'SMOKE_EXPECT_HEALTH_VERSION="${SMOKE_EXPECT_HEALTH_VERSION:-${SMOKE_UI_APP_VERSION}}"',
        'APP_VERSION="${SMOKE_UI_APP_VERSION}"',
        "assert_health_version",
        "health version mismatch: expected=",
        "/health",
        "/healthz",
        '"appVersionConfigured"',
        '"healthVersionExpected"',
        '"healthVersionObserved"',
        '"result": "pass"',
        "login -> protected route -> logout -> relogin (+ failure modes/no-api-host guard)",
        "core-flow-failure-trace.md",
        "core-flow-failure-gui.png",
    ]

    missing = [snippet for snippet in required_snippets if snippet not in text]
    assert not missing, f"BL-334 Split-Smoke-Script unvollständig, fehlend: {missing}"

    assert (
        'APP_VERSION="bl334-split-smoke"' not in text
    ), "UI APP_VERSION darf nicht hart verdrahtet sein"
