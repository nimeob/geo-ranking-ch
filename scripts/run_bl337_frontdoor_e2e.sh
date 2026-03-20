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
AUTH_PREFLIGHT_SCRIPT="${BL337_AUTH_PREFLIGHT_SCRIPT:-${REPO_ROOT}/scripts/smoke/auth_preflight.sh}"

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

API_AUTH_TOKEN="${BL337_API_AUTH_TOKEN:-}"
if [[ "${AUTH_MODE}" == "auto" && -z "${API_AUTH_TOKEN}" ]]; then
  has_oidc_hint=false
  if [[ -n "${OIDC_TOKEN_URL:-}" && -n "${OIDC_CLIENT_ID:-}" ]]; then
    has_oidc_hint=true
  fi

  if [[ "${has_oidc_hint}" == "true" ]]; then
    if [[ ! -x "${AUTH_PREFLIGHT_SCRIPT}" ]]; then
      echo "[BL-337.frontdoor] WARN: auth preflight script nicht ausführbar (${AUTH_PREFLIGHT_SCRIPT}); fallback auf allow-auth-blocked" >&2
    else
      auth_contract_file="$(mktemp)"
      cleanup_contract() { rm -f "${auth_contract_file}"; }
      trap cleanup_contract EXIT

      if SMOKE_AUTH_MODE=oidc_client_credentials SMOKE_AUTH_OUTPUT_FILE="${auth_contract_file}" "${AUTH_PREFLIGHT_SCRIPT}" >/dev/null; then
        minted_token="$(grep -E '^SMOKE_BEARER_TOKEN=' "${auth_contract_file}" | head -n1 | cut -d'=' -f2-)"
        if [[ -n "${minted_token}" ]]; then
          API_AUTH_TOKEN="${minted_token}"
          echo "[BL-337.frontdoor] Auth preflight erfolgreich; API-WP2 läuft mit Bearer-Token (auto mode)."
        else
          echo "[BL-337.frontdoor] WARN: auth preflight lieferte keinen Token; fallback auf allow-auth-blocked" >&2
        fi
      else
        echo "[BL-337.frontdoor] WARN: auth preflight fehlgeschlagen; fallback auf allow-auth-blocked" >&2
      fi

      trap - EXIT
      cleanup_contract
      unset -f cleanup_contract
    fi
  fi
fi

api_cmd=("${PYTHON_BIN}" scripts/run_bl337_api_frontdoor_e2e.py --matrix "${MATRIX_PATH}" --timeout-seconds "${TIMEOUT_SECONDS}")
if [[ -n "${API_BASE_URL}" ]]; then
  api_cmd+=(--api-base-url "${API_BASE_URL}")
fi
if [[ -n "${API_EVIDENCE_JSON}" ]]; then
  api_cmd+=(--evidence-json "${API_EVIDENCE_JSON}")
fi
if [[ -n "${API_AUTH_TOKEN}" ]]; then
  api_cmd+=(--auth-token "${API_AUTH_TOKEN}")
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
    if [[ -z "${API_AUTH_TOKEN}" ]]; then
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
