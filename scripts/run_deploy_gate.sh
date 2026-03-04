#!/usr/bin/env bash
set -euo pipefail

API_HEALTH_URL="${DEPLOY_GATE_API_HEALTH_URL:-}"
GUI_READY_URL="${DEPLOY_GATE_GUI_READY_URL:-}"
MAX_WAIT_SECONDS="${DEPLOY_GATE_MAX_WAIT_SECONDS:-90}"
RETRY_DELAY_SECONDS="${DEPLOY_GATE_RETRY_DELAY_SECONDS:-5}"
OUTPUT_JSON="${DEPLOY_GATE_OUTPUT_JSON:-artifacts/deploy/deploy-gate-report.json}"
ROLLBACK_MODE="${DEPLOY_GATE_ROLLBACK_MODE:-mark-required}"
PREVIOUS_API_TASKDEF="${DEPLOY_GATE_PREVIOUS_API_TASKDEF:-}"
PREVIOUS_UI_TASKDEF="${DEPLOY_GATE_PREVIOUS_UI_TASKDEF:-}"

if [ -z "$API_HEALTH_URL" ]; then
  echo "::error::DEPLOY_GATE_API_HEALTH_URL is required"
  exit 1
fi
if [ -z "$GUI_READY_URL" ]; then
  echo "::error::DEPLOY_GATE_GUI_READY_URL is required"
  exit 1
fi

if ! [[ "$MAX_WAIT_SECONDS" =~ ^[0-9]+$ ]] || [ "$MAX_WAIT_SECONDS" -lt 1 ]; then
  echo "::error::DEPLOY_GATE_MAX_WAIT_SECONDS must be an integer >= 1 (got '$MAX_WAIT_SECONDS')."
  exit 1
fi
if ! [[ "$RETRY_DELAY_SECONDS" =~ ^[0-9]+$ ]] || [ "$RETRY_DELAY_SECONDS" -lt 1 ]; then
  echo "::error::DEPLOY_GATE_RETRY_DELAY_SECONDS must be an integer >= 1 (got '$RETRY_DELAY_SECONDS')."
  exit 1
fi

if [ "$ROLLBACK_MODE" != "mark-required" ]; then
  echo "::error::Unsupported DEPLOY_GATE_ROLLBACK_MODE '$ROLLBACK_MODE' (supported: mark-required)."
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_JSON")"

write_report() {
  local status="$1"
  local now_utc="$2"
  local elapsed="$3"
  local attempts="$4"
  local last_api_http="$5"
  local last_api_exit="$6"
  local last_gui_http="$7"
  local last_gui_exit="$8"

  DEPLOY_GATE_REPORT_STATUS="$status" \
  DEPLOY_GATE_REPORT_TIME_UTC="$now_utc" \
  DEPLOY_GATE_REPORT_ELAPSED_SECONDS="$elapsed" \
  DEPLOY_GATE_REPORT_ATTEMPTS="$attempts" \
  DEPLOY_GATE_REPORT_LAST_API_HTTP="$last_api_http" \
  DEPLOY_GATE_REPORT_LAST_API_EXIT="$last_api_exit" \
  DEPLOY_GATE_REPORT_LAST_GUI_HTTP="$last_gui_http" \
  DEPLOY_GATE_REPORT_LAST_GUI_EXIT="$last_gui_exit" \
  DEPLOY_GATE_OUTPUT_JSON_PATH="$OUTPUT_JSON" \
  API_HEALTH_URL="$API_HEALTH_URL" \
  GUI_READY_URL="$GUI_READY_URL" \
  MAX_WAIT_SECONDS="$MAX_WAIT_SECONDS" \
  RETRY_DELAY_SECONDS="$RETRY_DELAY_SECONDS" \
  ROLLBACK_MODE="$ROLLBACK_MODE" \
  PREVIOUS_API_TASKDEF="$PREVIOUS_API_TASKDEF" \
  PREVIOUS_UI_TASKDEF="$PREVIOUS_UI_TASKDEF" \
  python3 - <<'PY'
import json
import os
from pathlib import Path

out = Path(os.environ["DEPLOY_GATE_OUTPUT_JSON_PATH"])
status = os.environ["DEPLOY_GATE_REPORT_STATUS"]
report = {
    "schema_version": "deploy-gate-report/v1",
    "status": status,
    "rollback_required": status != "success",
    "rollback_mode": os.environ.get("ROLLBACK_MODE", "mark-required"),
    "checked_at_utc": os.environ["DEPLOY_GATE_REPORT_TIME_UTC"],
    "attempts": int(os.environ["DEPLOY_GATE_REPORT_ATTEMPTS"]),
    "elapsed_seconds": int(os.environ["DEPLOY_GATE_REPORT_ELAPSED_SECONDS"]),
    "config": {
        "max_wait_seconds": int(os.environ.get("MAX_WAIT_SECONDS", "90")),
        "retry_delay_seconds": int(os.environ.get("RETRY_DELAY_SECONDS", "5")),
        "api_health_url": os.environ.get("API_HEALTH_URL", ""),
        "gui_ready_url": os.environ.get("GUI_READY_URL", ""),
    },
    "last_probe": {
        "api": {
            "url": os.environ.get("API_HEALTH_URL", ""),
            "http_status": os.environ["DEPLOY_GATE_REPORT_LAST_API_HTTP"],
            "curl_exit": int(os.environ["DEPLOY_GATE_REPORT_LAST_API_EXIT"]),
        },
        "gui": {
            "url": os.environ.get("GUI_READY_URL", ""),
            "http_status": os.environ["DEPLOY_GATE_REPORT_LAST_GUI_HTTP"],
            "curl_exit": int(os.environ["DEPLOY_GATE_REPORT_LAST_GUI_EXIT"]),
        },
    },
    "rollback_hint": {
        "api_previous_taskdef": os.environ.get("PREVIOUS_API_TASKDEF", ""),
        "ui_previous_taskdef": os.environ.get("PREVIOUS_UI_TASKDEF", ""),
        "required": status != "success",
    },
}
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

START_TS="$(date +%s)"
DEADLINE_TS=$((START_TS + MAX_WAIT_SECONDS))
ATTEMPT=1
LAST_API_HTTP="000"
LAST_GUI_HTTP="000"
LAST_API_EXIT=0
LAST_GUI_EXIT=0

while :; do
  set +e
  LAST_API_HTTP=$(curl -sS -L \
    --max-time 10 \
    --retry 1 \
    --retry-delay 2 \
    --retry-connrefused \
    -o /tmp/deploy-gate-api-response.txt \
    -w "%{http_code}" \
    "$API_HEALTH_URL")
  LAST_API_EXIT=$?
  set -e
  LAST_API_HTTP="${LAST_API_HTTP:-000}"

  set +e
  LAST_GUI_HTTP=$(curl -sS -L \
    --max-time 10 \
    --retry 1 \
    --retry-delay 2 \
    --retry-connrefused \
    -o /tmp/deploy-gate-gui-response.txt \
    -w "%{http_code}" \
    "$GUI_READY_URL")
  LAST_GUI_EXIT=$?
  set -e
  LAST_GUI_HTTP="${LAST_GUI_HTTP:-000}"

  NOW_TS="$(date +%s)"
  ELAPSED_SECONDS=$((NOW_TS - START_TS))
  echo "deploy-gate status attempt=${ATTEMPT} elapsed_seconds=${ELAPSED_SECONDS} check=api-health url=${API_HEALTH_URL} http=${LAST_API_HTTP} curl_exit=${LAST_API_EXIT}"
  echo "deploy-gate status attempt=${ATTEMPT} elapsed_seconds=${ELAPSED_SECONDS} check=gui-readiness url=${GUI_READY_URL} http=${LAST_GUI_HTTP} curl_exit=${LAST_GUI_EXIT}"

  if [ "$LAST_API_EXIT" -eq 0 ] && [ "$LAST_API_HTTP" = "200" ] && [ "$LAST_GUI_EXIT" -eq 0 ] && [ "$LAST_GUI_HTTP" = "200" ]; then
    NOW_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    write_report "success" "$NOW_UTC" "$ELAPSED_SECONDS" "$ATTEMPT" "$LAST_API_HTTP" "$LAST_API_EXIT" "$LAST_GUI_HTTP" "$LAST_GUI_EXIT"
    echo "deploy-gate success: API + GUI readiness checks are green"
    exit 0
  fi

  if [ "$NOW_TS" -ge "$DEADLINE_TS" ]; then
    NOW_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    write_report "failed" "$NOW_UTC" "$ELAPSED_SECONDS" "$ATTEMPT" "$LAST_API_HTTP" "$LAST_API_EXIT" "$LAST_GUI_HTTP" "$LAST_GUI_EXIT"

    echo "::error::Deploy gate timed out after ${MAX_WAIT_SECONDS}s"
    echo "::error::Final API status: ${API_HEALTH_URL} -> curl_exit=${LAST_API_EXIT}, http=${LAST_API_HTTP}"
    echo "::error::Final GUI status: ${GUI_READY_URL} -> curl_exit=${LAST_GUI_EXIT}, http=${LAST_GUI_HTTP}"

    if [ -n "$PREVIOUS_API_TASKDEF" ] || [ -n "$PREVIOUS_UI_TASKDEF" ]; then
      echo "::error::ROLLBACK_REQUIRED mode=${ROLLBACK_MODE} previous_api_taskdef=${PREVIOUS_API_TASKDEF:-n/a} previous_ui_taskdef=${PREVIOUS_UI_TASKDEF:-n/a}"
    else
      echo "::error::ROLLBACK_REQUIRED mode=${ROLLBACK_MODE} previous_taskdef=unknown"
    fi

    if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
      {
        echo "## Deploy gate timeout (rollback required)"
        echo ""
        echo "- API: \\`${API_HEALTH_URL}\\` => http=${LAST_API_HTTP}, curl_exit=${LAST_API_EXIT}"
        echo "- GUI: \\`${GUI_READY_URL}\\` => http=${LAST_GUI_HTTP}, curl_exit=${LAST_GUI_EXIT}"
        echo "- Config: max_wait=${MAX_WAIT_SECONDS}s, retry_delay=${RETRY_DELAY_SECONDS}s"
        echo "- Rollback mode: \\`${ROLLBACK_MODE}\\`"
        echo "- Previous API taskdef: \\`${PREVIOUS_API_TASKDEF:-unknown}\\`"
        echo "- Previous UI taskdef: \\`${PREVIOUS_UI_TASKDEF:-unknown}\\`"
        echo "- Report: \\`${OUTPUT_JSON}\\`"
      } >> "$GITHUB_STEP_SUMMARY"
    fi

    head -c 600 /tmp/deploy-gate-api-response.txt || true
    head -c 600 /tmp/deploy-gate-gui-response.txt || true
    exit 1
  fi

  sleep "$RETRY_DELAY_SECONDS"
  ATTEMPT=$((ATTEMPT + 1))
done
