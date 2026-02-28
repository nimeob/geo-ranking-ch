#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CURL_BIN="${CURL_BIN:-curl}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${REPO_ROOT}/artifacts/bl334"
OUT_JSON="${OUT_DIR}/${STAMP}-bl334-split-smokes.json"

API_PID=""
UI_PID=""
API_PORT=""
UI_PORT=""
API_LOG="${OUT_DIR}/${STAMP}-api-smoke.log"
UI_LOG="${OUT_DIR}/${STAMP}-ui-smoke.log"

mkdir -p "${OUT_DIR}"

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "ERROR: required command not found: ${cmd}" >&2
    exit 1
  fi
}

require_cmd "${PYTHON_BIN}"
require_cmd "${CURL_BIN}"

cleanup() {
  for pid in "${UI_PID}" "${API_PID}"; do
    if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
      kill "${pid}" >/dev/null 2>&1 || true
      wait "${pid}" >/dev/null 2>&1 || true
    fi
  done
}

trap cleanup EXIT

find_free_port() {
  "${PYTHON_BIN}" - <<'PY'
import socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

wait_http_200() {
  local url="$1"
  local timeout_seconds="${2:-20}"
  local start_ts
  start_ts="$(date +%s)"

  while true; do
    local http_code
    http_code="$(${CURL_BIN} -sS -o /dev/null -w "%{http_code}" "${url}" || true)"
    if [[ "${http_code}" == "200" ]]; then
      return 0
    fi

    if (( $(date +%s) - start_ts >= timeout_seconds )); then
      echo "ERROR: timeout waiting for ${url} (last HTTP ${http_code})" >&2
      return 1
    fi

    sleep 0.2
  done
}

validate_json_bool_true() {
  local json_payload="$1"
  local path_expr="$2"

  "${PYTHON_BIN}" - "$path_expr" "$json_payload" <<'PY'
import json
import sys

path = sys.argv[1].split(".")
payload = json.loads(sys.argv[2])

cursor = payload
for token in path:
    if isinstance(cursor, dict) and token in cursor:
        cursor = cursor[token]
    else:
        raise SystemExit(f"missing JSON path: {'.'.join(path)}")

if cursor is not True:
    raise SystemExit(f"expected JSON path {'.'.join(path)} to be true, got: {cursor!r}")
PY
}

validate_json_equals() {
  local json_payload="$1"
  local path_expr="$2"
  local expected="$3"

  "${PYTHON_BIN}" - "$path_expr" "$expected" "$json_payload" <<'PY'
import json
import sys

path = sys.argv[1].split(".")
expected = sys.argv[2]
payload = json.loads(sys.argv[3])

cursor = payload
for token in path:
    if isinstance(cursor, dict) and token in cursor:
        cursor = cursor[token]
    else:
        raise SystemExit(f"missing JSON path: {'.'.join(path)}")

if str(cursor) != expected:
    raise SystemExit(
        f"expected JSON path {'.'.join(path)} to equal {expected!r}, got: {cursor!r}"
    )
PY
}

echo "[BL-334.5] API-only smoke (src.api.web_service)"
API_PORT="$(find_free_port)"
HOST="127.0.0.1" \
PORT="${API_PORT}" \
PYTHONPATH="${REPO_ROOT}" \
ENABLE_E2E_FAULT_INJECTION="1" \
"${PYTHON_BIN}" -m src.api.web_service >"${API_LOG}" 2>&1 &
API_PID="$!"

wait_http_200 "http://127.0.0.1:${API_PORT}/health"

API_ANALYZE_PAYLOAD='{"query":"__ok__","intelligence_mode":"basic"}'
API_ANALYZE_RESPONSE="$(${CURL_BIN} -sS \
  -X POST "http://127.0.0.1:${API_PORT}/analyze" \
  -H 'Content-Type: application/json' \
  --data "${API_ANALYZE_PAYLOAD}")"

validate_json_bool_true "${API_ANALYZE_RESPONSE}" "ok"


echo "[BL-334.5] UI-only smoke (src.ui.service)"
UI_PORT="$(find_free_port)"
HOST="127.0.0.1" \
PORT="${UI_PORT}" \
APP_VERSION="bl334-split-smoke" \
UI_API_BASE_URL="http://127.0.0.1:${API_PORT}" \
PYTHONPATH="${REPO_ROOT}" \
"${PYTHON_BIN}" -m src.ui.service >"${UI_LOG}" 2>&1 &
UI_PID="$!"

wait_http_200 "http://127.0.0.1:${UI_PORT}/healthz"

UI_HEALTH_RESPONSE="$(${CURL_BIN} -sS "http://127.0.0.1:${UI_PORT}/healthz")"
validate_json_bool_true "${UI_HEALTH_RESPONSE}" "ok"
validate_json_equals "${UI_HEALTH_RESPONSE}" "service" "geo-ranking-ch-ui"

UI_GUI_HTML="$(${CURL_BIN} -sS "http://127.0.0.1:${UI_PORT}/gui")"
if ! grep -q "geo-ranking.ch GUI MVP" <<<"${UI_GUI_HTML}"; then
  echo "ERROR: UI smoke failed, expected GUI marker not found" >&2
  exit 1
fi

cat >"${OUT_JSON}" <<EOF
{
  "timestampUtc": "${STAMP}",
  "api": {
    "entrypoint": "python -m src.api.web_service",
    "healthUrl": "http://127.0.0.1:${API_PORT}/health",
    "analyzeUrl": "http://127.0.0.1:${API_PORT}/analyze",
    "result": "pass",
    "log": "${API_LOG}"
  },
  "ui": {
    "entrypoint": "python -m src.ui.service",
    "healthUrl": "http://127.0.0.1:${UI_PORT}/healthz",
    "guiUrl": "http://127.0.0.1:${UI_PORT}/gui",
    "result": "pass",
    "log": "${UI_LOG}"
  },
  "result": "pass"
}
EOF

echo "✅ BL-334.5 split smokes passed"
echo "- evidence: ${OUT_JSON}"
echo "- api log:  ${API_LOG}"
echo "- ui log:   ${UI_LOG}"
