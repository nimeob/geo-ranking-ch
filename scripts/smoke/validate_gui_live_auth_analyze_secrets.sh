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

BASE_URL_RAW="$(trim "${DEV_UI_BASE_URL:-${BASE_URL:-https://www.dev.georanking.ch}}")"
if [[ -z "${BASE_URL_RAW}" ]]; then
  BASE_URL_RAW="https://www.dev.georanking.ch"
fi

FALLBACK_ENV_NAME="dev"
if [[ "${BASE_URL_RAW,,}" == *"staging"* ]]; then
  FALLBACK_ENV_NAME="staging"
fi

FALLBACK_LOGIN_START_SMOKE_COMMAND="./scripts/smoke/run_login_start_smoke_bundle.sh --base-url ${BASE_URL_RAW} --env-name ${FALLBACK_ENV_NAME}"

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

  python3 - "${OUT}" "${RUN_ID}" "${WORKFLOW_NAME}" "${BASE_URL_RAW}" "${FALLBACK_ENV_NAME}" "${FALLBACK_LOGIN_START_SMOKE_COMMAND}" "${MISSING[@]}" <<'PY'
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1])
run_id = sys.argv[2]
workflow_name = sys.argv[3]
fallback_base_url = sys.argv[4]
fallback_env_name = sys.argv[5]
fallback_command = sys.argv[6]
missing = sys.argv[7:]
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
    "fallback_login_start_smoke": {
        "base_url": fallback_base_url,
        "env_name": fallback_env_name,
        "command": fallback_command,
    },
}
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

  echo "::error::Missing required secrets for real UI login smoke: ${MISSING[*]}" >&2
  echo "[gui-live-smoke-preflight] blocker_evidence=${OUT}" >&2
  echo "[gui-live-smoke-preflight] fallback_login_start_smoke=${FALLBACK_LOGIN_START_SMOKE_COMMAND}" >&2
  exit 1
fi

echo "[gui-live-smoke-preflight] required secrets present"
