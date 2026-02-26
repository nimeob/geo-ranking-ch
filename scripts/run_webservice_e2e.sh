#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[BL-18] Starte lokale E2E-Tests ..."
"$PYTHON_BIN" -m pytest -q tests/test_web_e2e.py tests/test_remote_smoke_script.py tests/test_remote_stability_script.py

if [[ -n "${DEV_BASE_URL:-}" ]]; then
  echo "[BL-18] Starte dev E2E-Tests gegen ${DEV_BASE_URL} ..."
  "$PYTHON_BIN" -m pytest -q tests/test_web_e2e_dev.py
else
  echo "[BL-18] DEV_BASE_URL nicht gesetzt -> dev E2E-Tests übersprungen"
fi
