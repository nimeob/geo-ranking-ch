#!/usr/bin/env bash
set -euo pipefail

trim() {
  python3 - "$1" <<'PY'
import sys
print(sys.argv[1].strip())
PY
}

RUN_ID="$(trim "${DEV_UI_SMOKE_RUN_ID:-}")"
RUN_ATTEMPT="$(trim "${GITHUB_RUN_ATTEMPT:-1}")"
if [[ -z "${RUN_ATTEMPT}" ]]; then
  RUN_ATTEMPT="1"
fi

if [[ -z "${RUN_ID}" ]]; then
  RUN_NUMBER="$(trim "${GITHUB_RUN_NUMBER:-}")"
  if [[ -n "${RUN_NUMBER}" ]]; then
    RUN_ID="${RUN_NUMBER}-${RUN_ATTEMPT}"
  else
    RUN_BASE="$(trim "${GITHUB_RUN_ID:-}")"
    if [[ -n "${RUN_BASE}" ]]; then
      RUN_ID="${RUN_BASE}-${RUN_ATTEMPT}"
    else
      RUN_ID="$(date +%s)"
    fi
  fi
fi

USERNAME="$(trim "${DEV_UI_SMOKE_USERNAME:-}")"
PASSWORD="$(trim "${DEV_UI_SMOKE_PASSWORD:-}")"
WORKFLOW_NAME="$(trim "${DEV_UI_SMOKE_WORKFLOW_NAME:-gui-dev-live-auth-analyze-smoke}")"
BLOCKER_PREFIX="$(trim "${DEV_UI_SMOKE_BLOCKER_PREFIX:-dev-ui-auth-analyze-smoke-blocked}")"
BLOCKER_DIR="$(trim "${DEV_UI_SMOKE_BLOCKER_DIR:-reports/evidence}")"
if [[ -z "${BLOCKER_DIR}" ]]; then
  BLOCKER_DIR="reports/evidence"
fi

MISSING=()
if [[ -z "${USERNAME}" ]]; then
  MISSING+=("DEV_UI_SMOKE_USERNAME")
fi
if [[ -z "${PASSWORD}" ]]; then
  MISSING+=("DEV_UI_SMOKE_PASSWORD")
fi

if (( ${#MISSING[@]} > 0 )); then
  mkdir -p "${BLOCKER_DIR}"
  OUT="${BLOCKER_DIR}/${BLOCKER_PREFIX}-${RUN_ID}.json"

  python3 - "${OUT}" "${RUN_ID}" "${WORKFLOW_NAME}" "${MISSING[@]}" <<'PY'
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
run_id = sys.argv[2]
workflow_name = sys.argv[3]
missing = sys.argv[4:]
required = ["DEV_UI_SMOKE_USERNAME", "DEV_UI_SMOKE_PASSWORD"]

next_step = "Set both repository secrets and re-run the workflow."
if workflow_name:
    next_step = f"Set both repository secrets and re-run {workflow_name} workflow."

payload = {
    "ok": False,
    "blocked": True,
    "reason": "missing_required_github_secrets",
    "run_id": run_id,
    "workflow": workflow_name,
    "required": required,
    "missing": missing,
    "next_step": next_step,
}
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

  echo "::error::Missing required secrets for real UI login smoke: ${MISSING[*]}" >&2
  echo "[gui-live-smoke-preflight] blocker_evidence=${OUT}" >&2
  exit 1
fi

echo "[gui-live-smoke-preflight] required secrets present"
