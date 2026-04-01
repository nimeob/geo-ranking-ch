from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTE_HELPER = REPO_ROOT / "scripts" / "smoke" / "gui_smoke_routes.sh"


def _parse_routes(csv_value: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CSV_INPUT"] = csv_value

    return subprocess.run(
        [
            "bash",
            "-lc",
            (
                f'source "{ROUTE_HELPER}" && '
                'gui_smoke_parse_route_csv "${CSV_INPUT}" && '
                'printf "%s\\n" "${GUI_SMOKE_SELECTED_ROUTES[@]}"'
            ),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_parse_route_csv_empty_selects_full_matrix() -> None:
    proc = _parse_routes("")

    assert proc.returncode == 0
    routes = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    assert len(routes) == 17
    assert routes[0] == "/"
    assert routes[-1] == "/gui/jobs/demo-job"


def test_parse_route_csv_supports_presets_and_dedupes() -> None:
    proc = _parse_routes("core,jobs,/jobs?source=smoke,/")

    assert proc.returncode == 0
    routes = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    assert routes == [
        "/",
        "/gui",
        "/gui/history",
        "/gui?view=trace&request_id=req-smoke",
        "/jobs",
        "/jobs?source=smoke",
        "/jobs/demo-job",
        "/gui/jobs",
        "/gui/jobs?source=smoke",
        "/gui/jobs/demo-job",
    ]


def test_parse_route_csv_rejects_unknown_preset_token() -> None:
    proc = _parse_routes("core,foobar")

    assert proc.returncode != 0
    assert "Invalid route token: foobar" in proc.stderr
    assert "match presets: all,core,jobs,results,legacy" in proc.stderr


def test_parse_route_csv_rejects_unsupported_absolute_route() -> None:
    proc = _parse_routes("/gui,/not-in-matrix")

    assert proc.returncode != 0
    assert "Unsupported route token: /not-in-matrix" in proc.stderr
