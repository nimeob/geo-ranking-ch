from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "smoke" / "run_auth_perimeter_smoke_bundle.sh"


def _write_stub_script(
    path: Path,
    *,
    output_flag: str,
    status: str,
    rc: int,
    ok: bool | None = None,
    required_tokens: list[str] | None = None,
    stdout_line: str = "",
) -> None:
    ok_snippet = ""
    if ok is not None:
        ok_snippet = f"payload['ok'] = {str(ok)}\n"

    path.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "import os\n"
        "import sys\n"
        "\n"
        "args = sys.argv[1:]\n"
        f"required_tokens = {required_tokens or []!r}\n"
        "missing = [token for token in required_tokens if token not in args]\n"
        "if missing:\n"
        "    print(f'missing required args: {missing}', file=sys.stderr)\n"
        "    sys.exit(9)\n"
        f"stdout_line = {stdout_line!r}\n"
        "if stdout_line:\n"
        "    print(stdout_line)\n"
        "\n"
        "out_path = ''\n"
        f"flag = {output_flag!r}\n"
        "for idx, token in enumerate(args):\n"
        "    if token == flag and idx + 1 < len(args):\n"
        "        out_path = args[idx + 1]\n"
        "        break\n"
        "\n"
        "if not out_path:\n"
        "    print(f'missing required {flag}', file=sys.stderr)\n"
        "    sys.exit(3)\n"
        "\n"
        f"payload = {{'status': {status!r}}}\n"
        f"{ok_snippet}"
        "os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)\n"
        "with open(out_path, 'w', encoding='utf-8') as fp:\n"
        "    json.dump(payload, fp, ensure_ascii=False, indent=2)\n"
        "    fp.write('\\n')\n"
        f"sys.exit({rc})\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_auth_perimeter_bundle_requires_base_url() -> None:
    proc = subprocess.run(
        [str(SCRIPT)],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Missing required --base-url" in proc.stderr
    assert "Usage:" in proc.stderr


def test_auth_perimeter_bundle_rejects_missing_option_value_for_output_dir() -> None:
    proc = subprocess.run(
        [str(SCRIPT), "--base-url", "https://www.dev.georanking.ch", "--output-dir"],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Missing value for --output-dir" in proc.stderr
    assert "Usage:" in proc.stderr


def test_auth_perimeter_bundle_rejects_short_flag_as_missing_option_value() -> None:
    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--summary-json",
            "-h",
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "Missing value for --summary-json" in proc.stderr
    assert "Usage:" in proc.stderr


def test_auth_perimeter_bundle_rejects_routes_and_presets_combination() -> None:
    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--routes",
            "/gui",
            "--route-presets",
            "core",
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "--routes und --route-presets dürfen nicht gleichzeitig gesetzt werden" in proc.stderr


def test_auth_perimeter_bundle_rejects_expected_authorize_host_when_it_collapses_to_empty() -> None:
    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--expected-authorize-host",
            " , , https:// , :// ,",
        ],
        cwd=str(REPO_ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 2
    assert "--expected-authorize-host enthält keine gültigen Hostnamen" in proc.stderr
    assert "Usage:" in proc.stderr


def test_auth_perimeter_bundle_runs_with_stubbed_steps_and_writes_repo_relative_summary(
    tmp_path: Path,
) -> None:
    stubs_dir = tmp_path / "stubs"
    stubs_dir.mkdir(parents=True, exist_ok=True)

    login_stub = stubs_dir / "login_stub.py"
    canonical_stub = stubs_dir / "canonical_stub.py"
    bff_stub = stubs_dir / "bff_stub.py"

    _write_stub_script(login_stub, output_flag="--summary-json", status="passed", rc=0)
    _write_stub_script(
        canonical_stub,
        output_flag="--summary-json",
        status="passed",
        rc=0,
    )
    _write_stub_script(bff_stub, output_flag="--output-json", status="passed", rc=0, ok=True)

    caller_cwd = tmp_path / "caller"
    caller_cwd.mkdir(parents=True, exist_ok=True)

    relative_root = Path(".tmp") / f"auth-perimeter-relative-{tmp_path.name}"
    output_dir_rel = str(relative_root / "evidence")
    summary_rel = str(relative_root / "summary" / "bundle-summary.json")

    expected_output_dir = REPO_ROOT / output_dir_rel
    expected_summary_path = REPO_ROOT / summary_rel

    shutil.rmtree(REPO_ROOT / relative_root, ignore_errors=True)

    env = os.environ.copy()
    env["AUTH_PERIMETER_LOGIN_START_BUNDLE_SCRIPT"] = str(login_stub)
    env["AUTH_PERIMETER_CANONICAL_BUNDLE_SCRIPT"] = str(canonical_stub)
    env["AUTH_PERIMETER_BFF_GUARD_SCRIPT"] = str(bff_stub)

    try:
        proc = subprocess.run(
            [
                str(SCRIPT),
                "--ui-base-url",
                "https://www.dev.georanking.ch",
                "--env-name",
                "stub-auth-perimeter",
                "--output-dir",
                output_dir_rel,
                "--summary-json",
                summary_rel,
                "--route-presets",
                "core",
                "--quiet",
            ],
            cwd=str(caller_cwd),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        assert proc.returncode == 0, proc.stderr
        assert expected_summary_path.exists()

        summary = json.loads(expected_summary_path.read_text(encoding="utf-8"))
        assert summary["status"] == "passed"
        assert summary["env_name"] == "stub-auth-perimeter"
        assert summary["route_presets_csv"] == "core"
        assert len(summary["steps"]) == 3

        names = [row["name"] for row in summary["steps"]]
        assert names == [
            "login_start_bundle",
            "canonical_redirect_bundle",
            "bff_auth_proxy_guard",
        ]

        assert all(row["status"] == "passed" for row in summary["steps"])
        assert all(row["reported_status"] == "passed" for row in summary["steps"])

        assert (expected_output_dir / "stub-auth-perimeter-login-start-smoke-bundle-summary.json").exists()
        assert (expected_output_dir / "stub-auth-perimeter-canonical-host-redirect-smoke-bundle-summary.json").exists()
        assert (expected_output_dir / "stub-auth-perimeter-auth-proxy-guard-smoke.json").exists()
        assert summary["bff_output_json"] == str(
            expected_output_dir / "stub-auth-perimeter-auth-proxy-guard-smoke.json"
        )
    finally:
        shutil.rmtree(REPO_ROOT / relative_root, ignore_errors=True)


def test_auth_perimeter_bundle_forwards_canonical_overrides_and_bff_output_override(
    tmp_path: Path,
) -> None:
    stubs_dir = tmp_path / "stubs"
    stubs_dir.mkdir(parents=True, exist_ok=True)

    login_stub = stubs_dir / "login_stub.py"
    canonical_stub = stubs_dir / "canonical_stub.py"
    bff_stub = stubs_dir / "bff_stub.py"

    _write_stub_script(login_stub, output_flag="--summary-json", status="passed", rc=0)
    _write_stub_script(
        canonical_stub,
        output_flag="--summary-json",
        status="passed",
        rc=0,
        required_tokens=[
            "--canonical-origin",
            "https://www.dev.georanking.ch",
            "--canonical-hosts",
            "www.dev.georanking.ch,dev.geo-ranking.ch",
            "--alias-host",
            "dev.geo-ranking.ch",
        ],
    )
    _write_stub_script(bff_stub, output_flag="--output-json", status="passed", rc=0, ok=True)

    output_dir = tmp_path / "evidence"
    summary_path = tmp_path / "bundle-summary.json"
    bff_output_override = tmp_path / "custom" / "bff-guard.json"

    env = os.environ.copy()
    env["AUTH_PERIMETER_LOGIN_START_BUNDLE_SCRIPT"] = str(login_stub)
    env["AUTH_PERIMETER_CANONICAL_BUNDLE_SCRIPT"] = str(canonical_stub)
    env["AUTH_PERIMETER_BFF_GUARD_SCRIPT"] = str(bff_stub)

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--env-name",
            "stub-overrides",
            "--output-dir",
            str(output_dir),
            "--summary-json",
            str(summary_path),
            "--canonical-origin",
            "https://www.dev.georanking.ch",
            "--canonical-hosts",
            "www.dev.georanking.ch,dev.geo-ranking.ch",
            "--alias-host",
            "dev.geo-ranking.ch",
            "--bff-output-json",
            str(bff_output_override),
            "--quiet",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "passed"
    assert summary["canonical_origin"] == "https://www.dev.georanking.ch"
    assert summary["canonical_hosts"] == "www.dev.georanking.ch,dev.geo-ranking.ch"
    assert summary["alias_host"] == "dev.geo-ranking.ch"
    assert summary["bff_output_json"] == str(bff_output_override)
    assert bff_output_override.exists()


def test_auth_perimeter_bundle_normalizes_expected_authorize_host_before_forwarding(
    tmp_path: Path,
) -> None:
    stubs_dir = tmp_path / "stubs"
    stubs_dir.mkdir(parents=True, exist_ok=True)

    login_stub = stubs_dir / "login_stub.py"
    canonical_stub = stubs_dir / "canonical_stub.py"
    bff_stub = stubs_dir / "bff_stub.py"

    normalized_expected = "auth.dev.georanking.ch,auth.dev.geo-ranking.ch"

    _write_stub_script(
        login_stub,
        output_flag="--summary-json",
        status="passed",
        rc=0,
        required_tokens=["--expected-authorize-host", normalized_expected],
    )
    _write_stub_script(
        canonical_stub,
        output_flag="--summary-json",
        status="passed",
        rc=0,
    )
    _write_stub_script(
        bff_stub,
        output_flag="--output-json",
        status="passed",
        rc=0,
        ok=True,
        required_tokens=["--expected-authorize-host", normalized_expected],
    )

    output_dir = tmp_path / "evidence"
    summary_path = tmp_path / "bundle-summary.json"

    env = os.environ.copy()
    env["AUTH_PERIMETER_LOGIN_START_BUNDLE_SCRIPT"] = str(login_stub)
    env["AUTH_PERIMETER_CANONICAL_BUNDLE_SCRIPT"] = str(canonical_stub)
    env["AUTH_PERIMETER_BFF_GUARD_SCRIPT"] = str(bff_stub)

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--env-name",
            "stub-expected-host-normalized",
            "--output-dir",
            str(output_dir),
            "--summary-json",
            str(summary_path),
            "--expected-authorize-host",
            " AUTH.DEV.GEORANKING.CH.,https://auth.dev.geo-ranking.ch./oauth2/authorize,auth.dev.georanking.ch ",
            "--quiet",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "passed"
    assert summary["expected_authorize_host"] == normalized_expected


def test_auth_perimeter_bundle_reports_failed_step_and_returns_nonzero(
    tmp_path: Path,
) -> None:
    stubs_dir = tmp_path / "stubs"
    stubs_dir.mkdir(parents=True, exist_ok=True)

    login_stub = stubs_dir / "login_stub.py"
    canonical_stub = stubs_dir / "canonical_stub.py"
    bff_stub = stubs_dir / "bff_stub.py"

    _write_stub_script(login_stub, output_flag="--summary-json", status="passed", rc=0)
    _write_stub_script(
        canonical_stub,
        output_flag="--summary-json",
        status="failed",
        rc=7,
    )
    _write_stub_script(bff_stub, output_flag="--output-json", status="passed", rc=0, ok=True)

    output_dir = tmp_path / "evidence"
    summary_path = tmp_path / "bundle-summary.json"

    env = os.environ.copy()
    env["AUTH_PERIMETER_LOGIN_START_BUNDLE_SCRIPT"] = str(login_stub)
    env["AUTH_PERIMETER_CANONICAL_BUNDLE_SCRIPT"] = str(canonical_stub)
    env["AUTH_PERIMETER_BFF_GUARD_SCRIPT"] = str(bff_stub)

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--env-name",
            "stub-failure",
            "--output-dir",
            str(output_dir),
            "--summary-json",
            str(summary_path),
            "--quiet",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1
    assert summary_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "failed"

    by_name = {row["name"]: row for row in summary["steps"]}
    assert by_name["login_start_bundle"]["status"] == "passed"
    assert by_name["canonical_redirect_bundle"]["status"] == "failed"
    assert by_name["canonical_redirect_bundle"]["rc"] == 7
    assert by_name["canonical_redirect_bundle"]["reported_status"] == "failed"
    assert by_name["bff_auth_proxy_guard"]["status"] == "passed"


def test_auth_perimeter_bundle_quiet_suppresses_success_stdout_noise(tmp_path: Path) -> None:
    stubs_dir = tmp_path / "stubs"
    stubs_dir.mkdir(parents=True, exist_ok=True)

    login_stub = stubs_dir / "login_stub.py"
    canonical_stub = stubs_dir / "canonical_stub.py"
    bff_stub = stubs_dir / "bff_stub.py"

    _write_stub_script(
        login_stub,
        output_flag="--summary-json",
        status="passed",
        rc=0,
        stdout_line="login-noise",
    )
    _write_stub_script(
        canonical_stub,
        output_flag="--summary-json",
        status="passed",
        rc=0,
        stdout_line="canonical-noise",
    )
    _write_stub_script(
        bff_stub,
        output_flag="--output-json",
        status="passed",
        rc=0,
        ok=True,
        stdout_line="bff-noise",
    )

    output_dir = tmp_path / "evidence"
    summary_path = tmp_path / "bundle-summary.json"

    env = os.environ.copy()
    env["AUTH_PERIMETER_LOGIN_START_BUNDLE_SCRIPT"] = str(login_stub)
    env["AUTH_PERIMETER_CANONICAL_BUNDLE_SCRIPT"] = str(canonical_stub)
    env["AUTH_PERIMETER_BFF_GUARD_SCRIPT"] = str(bff_stub)

    proc = subprocess.run(
        [
            str(SCRIPT),
            "--base-url",
            "https://www.dev.georanking.ch",
            "--env-name",
            "stub-quiet-noise",
            "--output-dir",
            str(output_dir),
            "--summary-json",
            str(summary_path),
            "--quiet",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == ""
    assert proc.stderr.strip() == ""
    assert summary_path.exists()
