#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DEFAULT_PYTHON="python3"
if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  DEFAULT_PYTHON="${REPO_ROOT}/.venv/bin/python"
fi

PYTHON_BIN="${PYTHON_BIN:-${DEFAULT_PYTHON}}"
MATRIX_PATH="${BL337_MATRIX_PATH:-artifacts/bl337/latest-internet-e2e-matrix.json}"
API_BASE_URL="${BL337_API_BASE_URL:-}"
APP_BASE_URL="${BL337_APP_BASE_URL:-}"
TIMEOUT_SECONDS="${BL337_TIMEOUT_SECONDS:-20}"
API_EVIDENCE_JSON="${BL337_API_EVIDENCE_JSON:-}"
UI_EVIDENCE_JSON="${BL337_UI_EVIDENCE_JSON:-}"
AUTH_MODE="${BL337_AUTH_MODE:-auto}"

case "${AUTH_MODE}" in
  auto|allow|strict)
    ;;
  *)
    echo "ERROR: BL337_AUTH_MODE muss auto|allow|strict sein (ist: ${AUTH_MODE})" >&2
    exit 2
    ;;
esac

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "ERROR: required command not found: ${PYTHON_BIN}" >&2
  exit 2
fi

cd "${REPO_ROOT}"

matrix_cmd=("${PYTHON_BIN}" scripts/manage_bl337_internet_e2e_matrix.py --output "${MATRIX_PATH}")
if [[ -n "${API_BASE_URL}" ]]; then
  matrix_cmd+=(--api-base-url "${API_BASE_URL}")
fi
if [[ -n "${APP_BASE_URL}" ]]; then
  matrix_cmd+=(--app-base-url "${APP_BASE_URL}")
fi

api_cmd=("${PYTHON_BIN}" scripts/run_bl337_api_frontdoor_e2e.py --matrix "${MATRIX_PATH}" --timeout-seconds "${TIMEOUT_SECONDS}")
if [[ -n "${API_BASE_URL}" ]]; then
  api_cmd+=(--api-base-url "${API_BASE_URL}")
fi
if [[ -n "${API_EVIDENCE_JSON}" ]]; then
  api_cmd+=(--evidence-json "${API_EVIDENCE_JSON}")
fi

allow_auth_blocked=false
case "${AUTH_MODE}" in
  allow)
    allow_auth_blocked=true
    ;;
  strict)
    allow_auth_blocked=false
    ;;
  auto)
    if [[ -z "${BL337_API_AUTH_TOKEN:-}" ]]; then
      allow_auth_blocked=true
    fi
    ;;
esac
if [[ "${allow_auth_blocked}" == "true" ]]; then
  api_cmd+=(--allow-auth-blocked)
fi

ui_cmd=("${PYTHON_BIN}" scripts/run_bl337_ui_frontdoor_e2e.py --matrix "${MATRIX_PATH}" --timeout-seconds "${TIMEOUT_SECONDS}")
if [[ -n "${APP_BASE_URL}" ]]; then
  ui_cmd+=(--app-base-url "${APP_BASE_URL}")
fi
if [[ -n "${API_BASE_URL}" ]]; then
  ui_cmd+=(--api-base-url "${API_BASE_URL}")
fi
if [[ -n "${UI_EVIDENCE_JSON}" ]]; then
  ui_cmd+=(--evidence-json "${UI_EVIDENCE_JSON}")
fi

validate_cmd=("${PYTHON_BIN}" scripts/manage_bl337_internet_e2e_matrix.py --validate "${MATRIX_PATH}" --require-actual)

echo "[BL-337.frontdoor] Matrix aktualisieren: ${MATRIX_PATH}"
"${matrix_cmd[@]}"

echo "[BL-337.frontdoor] API-E2E (auth_mode=${AUTH_MODE}, allow_auth_blocked=${allow_auth_blocked})"
"${api_cmd[@]}"

echo "[BL-337.frontdoor] UI-E2E"
"${ui_cmd[@]}"

echo "[BL-337.frontdoor] Matrix validieren (--require-actual)"
"${validate_cmd[@]}"

echo "[BL-337.frontdoor] ✅ complete"
