from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_bl337_frontdoor_e2e.sh"


def _make_fake_python(tmp_path: Path, log_path: Path) -> Path:
    fake_python = tmp_path / "fake-python.sh"
    fake_python.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf '%s\\n' \"$*\" >> \"${FAKE_PYTHON_LOG}\"\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_python.chmod(fake_python.stat().st_mode | stat.S_IXUSR)
    return fake_python


def _make_fake_auth_preflight_success(tmp_path: Path, token: str = "minted-token") -> Path:
    fake_preflight = tmp_path / "fake-auth-preflight-success.sh"
    fake_preflight.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "cat > \"${SMOKE_AUTH_OUTPUT_FILE}\" <<'EOF'\n"
        "SMOKE_AUTH_MODE=oidc_client_credentials\n"
        f"SMOKE_BEARER_TOKEN={token}\n"
        "EOF\n",
        encoding="utf-8",
    )
    fake_preflight.chmod(fake_preflight.stat().st_mode | stat.S_IXUSR)
    return fake_preflight


def _make_fake_auth_preflight_failure(tmp_path: Path) -> Path:
    fake_preflight = tmp_path / "fake-auth-preflight-failure.sh"
    fake_preflight.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "exit 42\n",
        encoding="utf-8",
    )
    fake_preflight.chmod(fake_preflight.stat().st_mode | stat.S_IXUSR)
    return fake_preflight


def test_wrapper_exists_and_is_executable() -> None:
    assert SCRIPT_PATH.exists(), f"missing: {SCRIPT_PATH}"
    mode = SCRIPT_PATH.stat().st_mode
    assert (mode & stat.S_IXUSR) != 0, f"not executable: {SCRIPT_PATH}"

    first_line = SCRIPT_PATH.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("#!/usr/bin/env bash")


def test_wrapper_rejects_invalid_auth_mode() -> None:
    proc = subprocess.run(
        [str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        env={
            "PATH": os.environ.get("PATH", ""),
            "BL337_AUTH_MODE": "invalid-mode",
        },
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 2
    combined = (proc.stdout + proc.stderr).strip()
    assert "BL337_AUTH_MODE" in combined
    assert "auto|allow|strict" in combined


def test_wrapper_auto_mode_adds_allow_auth_blocked_when_token_missing(tmp_path: Path) -> None:
    log_path = tmp_path / "fake-python.log"
    fake_python = _make_fake_python(tmp_path, log_path)

    proc = subprocess.run(
        [str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        env={
            "PATH": os.environ.get("PATH", ""),
            "PYTHON_BIN": str(fake_python),
            "FAKE_PYTHON_LOG": str(log_path),
            "BL337_AUTH_MODE": "auto",
        },
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4

    api_call = next(line for line in lines if "run_bl337_api_frontdoor_e2e.py" in line)
    assert "--allow-auth-blocked" in api_call


def test_wrapper_auto_mode_skips_allow_auth_blocked_when_token_present(tmp_path: Path) -> None:
    log_path = tmp_path / "fake-python.log"
    fake_python = _make_fake_python(tmp_path, log_path)

    proc = subprocess.run(
        [str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        env={
            "PATH": os.environ.get("PATH", ""),
            "PYTHON_BIN": str(fake_python),
            "FAKE_PYTHON_LOG": str(log_path),
            "BL337_AUTH_MODE": "auto",
            "BL337_API_AUTH_TOKEN": "dummy-token",
        },
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    lines = log_path.read_text(encoding="utf-8").splitlines()
    api_call = next(line for line in lines if "run_bl337_api_frontdoor_e2e.py" in line)
    assert "--allow-auth-blocked" not in api_call
    assert "--auth-token dummy-token" in api_call


def test_wrapper_auto_mode_skips_default_preflight_when_oidc_secret_hint_missing(tmp_path: Path) -> None:
    log_path = tmp_path / "fake-python.log"
    fake_python = _make_fake_python(tmp_path, log_path)

    proc = subprocess.run(
        [str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        env={
            "PATH": os.environ.get("PATH", ""),
            "PYTHON_BIN": str(fake_python),
            "FAKE_PYTHON_LOG": str(log_path),
            "BL337_AUTH_MODE": "auto",
            "OIDC_TOKEN_URL": "https://idp.example.test/oauth/token",
            "OIDC_CLIENT_ID": "smoke-client",
        },
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    combined = proc.stdout + proc.stderr
    assert "OIDC_CLIENT_SECRET(_FILE) fehlt" in combined
    assert "[auth-preflight-failed]" not in combined

    lines = log_path.read_text(encoding="utf-8").splitlines()
    api_call = next(line for line in lines if "run_bl337_api_frontdoor_e2e.py" in line)
    assert "--allow-auth-blocked" in api_call
    assert "--auth-token" not in api_call


def test_wrapper_auto_mode_uses_preflight_token_when_oidc_hints_present(tmp_path: Path) -> None:
    log_path = tmp_path / "fake-python.log"
    fake_python = _make_fake_python(tmp_path, log_path)
    fake_preflight = _make_fake_auth_preflight_success(tmp_path, token="oidc-minted")

    proc = subprocess.run(
        [str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        env={
            "PATH": os.environ.get("PATH", ""),
            "PYTHON_BIN": str(fake_python),
            "FAKE_PYTHON_LOG": str(log_path),
            "BL337_AUTH_MODE": "auto",
            "BL337_AUTH_PREFLIGHT_SCRIPT": str(fake_preflight),
            "OIDC_TOKEN_URL": "https://idp.example.test/oauth/token",
            "OIDC_CLIENT_ID": "smoke-client",
        },
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    lines = log_path.read_text(encoding="utf-8").splitlines()
    api_call = next(line for line in lines if "run_bl337_api_frontdoor_e2e.py" in line)
    assert "--allow-auth-blocked" not in api_call
    assert "--auth-token oidc-minted" in api_call


def test_wrapper_auto_mode_falls_back_to_allow_auth_blocked_when_preflight_fails(tmp_path: Path) -> None:
    log_path = tmp_path / "fake-python.log"
    fake_python = _make_fake_python(tmp_path, log_path)
    fake_preflight = _make_fake_auth_preflight_failure(tmp_path)

    proc = subprocess.run(
        [str(SCRIPT_PATH)],
        cwd=str(REPO_ROOT),
        env={
            "PATH": os.environ.get("PATH", ""),
            "PYTHON_BIN": str(fake_python),
            "FAKE_PYTHON_LOG": str(log_path),
            "BL337_AUTH_MODE": "auto",
            "BL337_AUTH_PREFLIGHT_SCRIPT": str(fake_preflight),
            "OIDC_TOKEN_URL": "https://idp.example.test/oauth/token",
            "OIDC_CLIENT_ID": "smoke-client",
        },
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    lines = log_path.read_text(encoding="utf-8").splitlines()
    api_call = next(line for line in lines if "run_bl337_api_frontdoor_e2e.py" in line)
    assert "--allow-auth-blocked" in api_call
    assert "--auth-token" not in api_call
