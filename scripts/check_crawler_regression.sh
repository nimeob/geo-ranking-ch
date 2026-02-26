#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

PYTHON_BIN="${CRAWLER_TEST_PYTHON:-python3.12}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "Kein passender Python-Interpreter gefunden (versucht: python3.12, python3)." >&2
    exit 1
  fi
fi

cd "$REPO_ROOT"
"$PYTHON_BIN" -m pytest -q tests/test_github_repo_crawler.py

echo "crawler regression check: PASS"
