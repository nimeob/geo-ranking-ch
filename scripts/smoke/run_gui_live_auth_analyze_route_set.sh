#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/smoke/run_gui_live_auth_analyze_route_set.sh [options]

Führt den gemeinsamen GUI-Route-Satz seriell aus und startet mit einem Secrets-Preflight.

Options:
  --base-url <url>        BASE_URL override (z. B. https://www.dev.georanking.ch)
  --output-dir <dir>      Evidence/Blocker-Ausgabeordner (default: reports/evidence)
  --timeout-ms <ms>       Timeout pro UI-Run (default: DEV_UI_SMOKE_TIMEOUT_MS bzw. 60000)
  --address-file <path>   Adressliste für Analyze-Smoke (default: scripts/smoke/ch_live_addresses.txt)
  --login-reason <text>   reason-Parameter für /login (default: manual_login)
  --run-id-base <token>   Basis für DEV_UI_SMOKE_RUN_ID je Route
  --allow-login-start-fallback
                          Bei fehlenden Live-Secrets automatisch login-start Bundle statt Fehler ausführen
  --headless              Erzwingt headless mode
  --headful               Erzwingt headful mode
  -h, --help              Diese Hilfe anzeigen
EOF
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/smoke/gui_smoke_routes.sh
source "${REPO_ROOT}/scripts/smoke/gui_smoke_routes.sh"

if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: node command not found" >&2
  exit 2
fi

base_url_override=""
output_dir_override=""
timeout_ms_override=""
address_file_override=""
login_reason_override=""
run_id_base_override=""
headful_override=""
allow_login_start_fallback_override="${DEV_UI_SMOKE_ALLOW_LOGIN_START_FALLBACK:-0}"

is_truthy() {
  local raw="${1:-}"
  raw="$(printf '%s' "${raw}" | tr '[:upper:]' '[:lower:]')"
  case "${raw}" in
    1|true|yes|on)
      return 0
      ;;
  esac
  return 1
}

require_option_value() {
  local option_name="$1"
  local option_value="${2:-}"

  if [[ -z "${option_value}" || "${option_value}" == --* ]]; then
    echo "ERROR: Missing value for ${option_name}" >&2
    usage >&2
    exit 2
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      require_option_value "--base-url" "${2:-}"
      base_url_override="$2"
      shift 2
      ;;
    --output-dir)
      require_option_value "--output-dir" "${2:-}"
      output_dir_override="$2"
      shift 2
      ;;
    --timeout-ms)
      require_option_value "--timeout-ms" "${2:-}"
      timeout_ms_override="$2"
      shift 2
      ;;
    --address-file)
      require_option_value "--address-file" "${2:-}"
      address_file_override="$2"
      shift 2
      ;;
    --login-reason)
      require_option_value "--login-reason" "${2:-}"
      login_reason_override="$2"
      shift 2
      ;;
    --run-id-base)
      require_option_value "--run-id-base" "${2:-}"
      run_id_base_override="$2"
      shift 2
      ;;
    --allow-login-start-fallback)
      allow_login_start_fallback_override="1"
      shift
      ;;
    --headless)
      headful_override="0"
      shift
      ;;
    --headful)
      headful_override="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -n "${base_url_override}" ]]; then
  export BASE_URL="${base_url_override}"
fi
if [[ -n "${output_dir_override}" ]]; then
  export DEV_UI_SMOKE_EVIDENCE_DIR="${output_dir_override}"
  export DEV_UI_SMOKE_BLOCKER_DIR="${output_dir_override}"
fi
if [[ -n "${timeout_ms_override}" ]]; then
  export DEV_UI_SMOKE_TIMEOUT_MS="${timeout_ms_override}"
fi
if [[ -n "${address_file_override}" ]]; then
  export DEV_UI_SMOKE_ADDRESS_FILE="${address_file_override}"
fi
if [[ -n "${login_reason_override}" ]]; then
  export DEV_UI_SMOKE_LOGIN_REASON="${login_reason_override}"
fi
if [[ -n "${headful_override}" ]]; then
  export DEV_UI_SMOKE_HEADFUL="${headful_override}"
fi

base_run_id="${run_id_base_override:-${DEV_UI_SMOKE_RUN_ID_BASE:-}}"
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
  fallback_base_url="${BASE_URL:-https://www.dev.georanking.ch}"
  fallback_env_name="dev"
  if [[ "${fallback_base_url}" == *"staging"* ]]; then
    fallback_env_name="staging"
  fi
  fallback_command_override="${DEV_UI_SMOKE_LOGIN_START_FALLBACK_COMMAND:-}"

  if is_truthy "${allow_login_start_fallback_override}"; then
    echo "[gui-live-smoke-preflight] running login-start fallback due to missing live secrets" >&2

    if [[ -n "${fallback_command_override}" ]]; then
      if bash -lc "${fallback_command_override}"; then
        echo "✅ gui-dev-live-auth-analyze-smoke fallback login-start bundle passed"
        exit 0
      fi
      fallback_status=$?
    else
      if (
        cd "${REPO_ROOT}"
        ./scripts/smoke/run_login_start_smoke_bundle.sh --base-url "${fallback_base_url}" --env-name "${fallback_env_name}"
      ); then
        echo "✅ gui-dev-live-auth-analyze-smoke fallback login-start bundle passed"
        exit 0
      fi
      fallback_status=$?
    fi

    echo "ERROR: login-start fallback failed (exit=${fallback_status})" >&2
    exit "${fallback_status}"
  fi

  echo "ERROR: live-auth route-set preflight failed; aborting route fan-out." >&2
  echo "HINT: If live credentials are unavailable, run login-start coverage instead:" >&2
  echo "  ./scripts/smoke/run_login_start_smoke_bundle.sh --base-url ${fallback_base_url} --env-name ${fallback_env_name}" >&2
  exit 1
fi

if (( ${#GUI_SMOKE_ROUTES[@]} == 0 )); then
  echo "ERROR: GUI_SMOKE_ROUTES ist leer" >&2
  exit 2
fi

failures=0
for idx in "${!GUI_SMOKE_ROUTES[@]}"; do
  ordinal="$((idx + 1))"
  route="${GUI_SMOKE_ROUTES[$idx]}"
  run_id="${base_run_id}-${ordinal}"

  echo "[gui-dev-live-auth-analyze-smoke] route ${ordinal}/${#GUI_SMOKE_ROUTES[@]}: ${route} (run_id=${run_id})"

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
