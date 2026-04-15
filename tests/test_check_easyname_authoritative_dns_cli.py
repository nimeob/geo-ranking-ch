from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_easyname_authoritative_dns.js"


def test_help_exits_zero_and_prints_usage() -> None:
    result = subprocess.run(
        ["node", str(SCRIPT), "--help"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Usage: node scripts/check_easyname_authoritative_dns.js [options]" in result.stdout
    assert result.stderr == ""


def test_unknown_option_exits_with_usage_and_code_2() -> None:
    result = subprocess.run(
        ["node", str(SCRIPT), "--nope"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "[easyname-dns] ERROR Unknown option: --nope" in result.stderr
    assert "Usage: node scripts/check_easyname_authoritative_dns.js [options]" in result.stderr


def test_missing_value_rejects_flag_token() -> None:
    result = subprocess.run(
        ["node", str(SCRIPT), "--host", "-h"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "[easyname-dns] ERROR Missing value for --host" in result.stderr
    assert "Usage: node scripts/check_easyname_authoritative_dns.js [options]" in result.stderr


def test_parse_args_supports_inline_assignment() -> None:
    snippet = f"""
const mod = require({json.dumps(str(SCRIPT))});
const parsed = mod.parseArgs(['--host=api.dev.georanking.ch', '--zone', 'georanking.ch', '--expect-cname', 'alb.example']);
process.stdout.write(JSON.stringify(parsed));
"""
    result = subprocess.run(
        ["node", "-e", snippet],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "host": "api.dev.georanking.ch",
        "zone": "georanking.ch",
        "expect-cname": "alb.example",
    }


def test_parse_args_rejects_positional_tokens() -> None:
    snippet = f"""
const mod = require({json.dumps(str(SCRIPT))});
try {{
  mod.parseArgs(['oops']);
  process.exit(1);
}} catch (err) {{
  process.stdout.write(err.message);
}}
"""
    result = subprocess.run(
        ["node", "-e", snippet],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "Unknown positional argument: oops"
