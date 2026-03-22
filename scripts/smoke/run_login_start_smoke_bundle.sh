#!/usr/bin/env bash
set -euo pipefail

BASE_URL=""
ENV_NAME=""
OUTPUT_DIR="artifacts"
REASON="manual_login"
TIMEOUT_SECONDS="20"
MAX_ATTEMPTS="8"
RETRY_DELAY_SECONDS="5"

usage() {
  cat <<'EOF'
Usage: scripts/smoke/run_login_start_smoke_bundle.sh --base-url <url> --env-name <dev|staging> [options]

Options:
  --base-url <url>              Base URL der GUI (z. B. https://www.dev.georanking.ch)
  --env-name <name>             Präfix für Artefakte (z. B. dev, staging)
  --output-dir <dir>            Ausgabeordner für JSON-Artefakte (default: artifacts)
  --reason <reason>             login-start reason (default: manual_login)
  --timeout <seconds>           Request-Timeout je Probe (default: 20)
  --max-attempts <count>        Retry-Versuche je Route (default: 8)
  --retry-delay <seconds>       Delay zwischen Retries (default: 5)
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --base-url)
      BASE_URL="${2:-}"
      shift 2
      ;;
    --env-name)
      ENV_NAME="${2:-}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    --reason)
      REASON="${2:-}"
      shift 2
      ;;
    --timeout)
      TIMEOUT_SECONDS="${2:-}"
      shift 2
      ;;
    --max-attempts)
      MAX_ATTEMPTS="${2:-}"
      shift 2
      ;;
    --retry-delay)
      RETRY_DELAY_SECONDS="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$BASE_URL" ]; then
  echo "::error::Missing required --base-url" >&2
  usage >&2
  exit 2
fi

if [ -z "$ENV_NAME" ]; then
  echo "::error::Missing required --env-name" >&2
  usage >&2
  exit 2
fi

mkdir -p "$OUTPUT_DIR"

run_probe() {
  local route="$1"
  local output_json="$2"

  python3 scripts/smoke/check_ui_login_start.py \
    --base-url "$BASE_URL" \
    --next "$route" \
    --reason "$REASON" \
    --timeout "$TIMEOUT_SECONDS" \
    --max-attempts "$MAX_ATTEMPTS" \
    --retry-delay "$RETRY_DELAY_SECONDS" \
    --output-json "$output_json"
}

LOGIN_GUI_RC=0
LOGIN_HISTORY_RC=0
LOGIN_JOBS_RC=0
LOGIN_GUI_JOBS_LEGACY_RC=0
LOGIN_GUI_JOBS_LEGACY_DETAIL_RC=0

set +e
run_probe "/gui" "${OUTPUT_DIR}/${ENV_NAME}-login-start-smoke.json"
LOGIN_GUI_RC=$?

run_probe "/gui/history" "${OUTPUT_DIR}/${ENV_NAME}-login-start-smoke-gui-history.json"
LOGIN_HISTORY_RC=$?

run_probe "/jobs" "${OUTPUT_DIR}/${ENV_NAME}-login-start-smoke-jobs.json"
LOGIN_JOBS_RC=$?

run_probe "/gui/jobs" "${OUTPUT_DIR}/${ENV_NAME}-login-start-smoke-gui-jobs-legacy.json"
LOGIN_GUI_JOBS_LEGACY_RC=$?

run_probe "/gui/jobs/demo-job" "${OUTPUT_DIR}/${ENV_NAME}-login-start-smoke-gui-jobs-legacy-detail.json"
LOGIN_GUI_JOBS_LEGACY_DETAIL_RC=$?
set -e

if [ "$LOGIN_GUI_RC" -ne 0 ] || [ "$LOGIN_HISTORY_RC" -ne 0 ] || [ "$LOGIN_JOBS_RC" -ne 0 ] || [ "$LOGIN_GUI_JOBS_LEGACY_RC" -ne 0 ] || [ "$LOGIN_GUI_JOBS_LEGACY_DETAIL_RC" -ne 0 ]; then
  echo "::error::UI login-start smoke failed (gui_rc=${LOGIN_GUI_RC}, gui_history_rc=${LOGIN_HISTORY_RC}, jobs_rc=${LOGIN_JOBS_RC}, gui_jobs_legacy_rc=${LOGIN_GUI_JOBS_LEGACY_RC}, gui_jobs_legacy_detail_rc=${LOGIN_GUI_JOBS_LEGACY_DETAIL_RC}). See ${OUTPUT_DIR}/${ENV_NAME}-login-start-smoke*.json"
  exit 1
fi

echo "UI login-start smoke bundle passed for env='${ENV_NAME}' (base_url=${BASE_URL})"
