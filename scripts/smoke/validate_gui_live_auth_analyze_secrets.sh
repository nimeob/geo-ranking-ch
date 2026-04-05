#!/usr/bin/env bash
set -euo pipefail

trim() {
  python3 - "$1" <<'PY'
import sys
print(sys.argv[1].strip())
PY
}

canonicalize_ui_base_url() {
  python3 - "$1" <<'PY'
from __future__ import annotations

import sys
from urllib.parse import urlsplit, urlunsplit


LEGACY_DEV_UI_HOSTS = {"dev.georanking.ch", "dev.geo-ranking.ch"}


raw_value = str(sys.argv[1]).strip()
if not raw_value:
    print("")
    raise SystemExit(0)

try:
    parsed = urlsplit(raw_value)
except ValueError:
    print(raw_value)
    raise SystemExit(0)

if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
    print(raw_value)
    raise SystemExit(0)

hostname = parsed.hostname.rstrip(".").lower()
if hostname in LEGACY_DEV_UI_HOSTS:
    hostname = f"www.{hostname}"

credentials = ""
if parsed.username:
    credentials = parsed.username
    if parsed.password:
        credentials += f":{parsed.password}"
    credentials += "@"

port_segment = f":{parsed.port}" if parsed.port is not None else ""
normalized = urlunsplit(
    (
        parsed.scheme.lower(),
        f"{credentials}{hostname}{port_segment}",
        parsed.path,
        parsed.query,
        parsed.fragment,
    )
)
print(normalized)
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

BASE_URL_EFFECTIVE="$(canonicalize_ui_base_url "${BASE_URL_RAW}")"
if [[ -z "${BASE_URL_EFFECTIVE}" ]]; then
  BASE_URL_EFFECTIVE="${BASE_URL_RAW}"
fi

FALLBACK_ENV_NAME="dev"
if [[ "${BASE_URL_EFFECTIVE,,}" == *"staging"* ]]; then
  FALLBACK_ENV_NAME="staging"
fi

FALLBACK_LOGIN_START_SMOKE_COMMAND="./scripts/smoke/run_login_start_smoke_bundle.sh --base-url ${BASE_URL_EFFECTIVE} --env-name ${FALLBACK_ENV_NAME}"

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

  python3 - "${OUT}" "${RUN_ID}" "${WORKFLOW_NAME}" "${BASE_URL_EFFECTIVE}" "${FALLBACK_ENV_NAME}" "${FALLBACK_LOGIN_START_SMOKE_COMMAND}" "${MISSING[@]}" <<'PY'
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
