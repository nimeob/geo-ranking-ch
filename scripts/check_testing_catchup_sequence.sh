#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

PYTHON_BIN="${TESTING_CATCHUP_PYTHON:-python3.12}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "Kein passender Python-Interpreter gefunden (versucht: python3.12, python3)." >&2
    exit 1
  fi
fi

cd "$REPO_ROOT"

PYTEST_SEQUENCE=(
  "tests/test_github_repo_crawler.py::TestGithubRepoCrawlerWorkstreamBalance::test_build_workstream_catchup_plan_returns_minimal_delta_per_category"
  "tests/test_github_repo_crawler.py::TestGithubRepoCrawlerWorkstreamBalance::test_print_workstream_balance_report_json_renders_machine_readable_payload"
  "tests/test_bl31_routing_tls_smoke_script.py::TestBl31RoutingTlsSmokeScript::test_smoke_baseline_mode_is_reproducible_with_structured_output"
  "tests/test_bl31_routing_tls_smoke_script.py::TestBl31RoutingTlsSmokeScript::test_strict_mode_matches_cors_baseline_result"
)

step=1
for target in "${PYTEST_SEQUENCE[@]}"; do
  echo "[testing-catchup] Step ${step}/${#PYTEST_SEQUENCE[@]}: ${target}"
  "$PYTHON_BIN" -m pytest -q "$target"
  step=$((step + 1))
done

echo "testing catch-up sequence: PASS"
