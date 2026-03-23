#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: node command not found" >&2
  exit 2
fi

base_run_id="${DEV_UI_SMOKE_RUN_ID_BASE:-}"
if [[ -z "${base_run_id}" ]]; then
  if [[ -n "${GITHUB_RUN_NUMBER:-}" ]]; then
    base_run_id="${GITHUB_RUN_NUMBER}-${GITHUB_RUN_ATTEMPT:-1}"
  elif [[ -n "${GITHUB_RUN_ID:-}" ]]; then
    base_run_id="${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT:-1}"
  else
    base_run_id="manual-$(date -u +%Y%m%dT%H%M%SZ)"
  fi
fi

if ! (
  cd "${REPO_ROOT}"
  DEV_UI_SMOKE_RUN_ID="${base_run_id}" \
    ./scripts/smoke/validate_gui_live_auth_analyze_secrets.sh
); then
  echo "ERROR: live-auth route-set preflight failed; aborting route fan-out." >&2
  exit 1
fi

routes=(
  "/gui"
  "/gui/history"
  "/gui/jobs"
  "/jobs"
  "/jobs?source=smoke"
  "/gui/jobs/demo-job"
  "/jobs/demo-job"
  "/results/demo-result"
)

failures=0
for idx in "${!routes[@]}"; do
  ordinal="$((idx + 1))"
  route="${routes[$idx]}"
  run_id="${base_run_id}-${ordinal}"

  echo "[gui-dev-live-auth-analyze-smoke] route ${ordinal}/${#routes[@]}: ${route} (run_id=${run_id})"

  if (
    cd "${REPO_ROOT}"
    DEV_UI_SMOKE_GUI_PATH="${route}" \
      DEV_UI_SMOKE_RUN_ID="${run_id}" \
      node scripts/run_dev_ui_auth_analyze_smoke.mjs
  ); then
    echo "[gui-dev-live-auth-analyze-smoke] PASS ${route}"
  else
    failures="$((failures + 1))"
    echo "[gui-dev-live-auth-analyze-smoke] FAIL ${route}" >&2
  fi
done

if (( failures > 0 )); then
  echo "ERROR: ${failures} route check(s) failed" >&2
  exit 1
fi

echo "✅ gui-dev-live-auth-analyze-smoke route set passed"
