#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

PYTHON_BIN="${QUALITY_GATE_PYTHON:-python3.12}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "Kein passender Python-Interpreter gefunden (versucht: python3.12, python3)." >&2
    exit 1
  fi
fi

VENV_DIR="$(mktemp -d "${TMPDIR:-/tmp}/docs-gate-XXXXXX")"
cleanup() {
  rm -rf "$VENV_DIR"
}
trap cleanup EXIT

VENV_ERR_FILE="$VENV_DIR/venv.err"

if "$PYTHON_BIN" -m venv "$VENV_DIR/.venv" >"$VENV_ERR_FILE" 2>&1; then
  # shellcheck source=/dev/null
  source "$VENV_DIR/.venv/bin/activate"

  python -m pip install --upgrade pip >/dev/null
  python -m pip install -r "$REPO_ROOT/requirements-dev.txt" >/dev/null

  cd "$REPO_ROOT"
  python -m pytest -q tests/test_user_docs.py tests/test_markdown_links.py

  echo "docs quality gate: PASS"
else
  echo "ERROR: venv-Erstellung fehlgeschlagen (fail-closed, kein degraded fallback erlaubt)." >&2
  cat "$VENV_ERR_FILE" >&2 || true
  exit 1
fi
