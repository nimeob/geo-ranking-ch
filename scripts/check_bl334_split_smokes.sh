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
CORE_FLOW_SMOKE_MAX_SECONDS="${CORE_FLOW_SMOKE_MAX_SECONDS:-300}"
CORE_FLOW_TEST_TARGET="${CORE_FLOW_TEST_TARGET:-tests.test_auth_regression_smoke_issue_1019}"
CORE_FLOW_LOG="${OUT_DIR}/${STAMP}-core-flow-smoke.log"
CORE_FLOW_FAILURE_EVIDENCE_DIR="${REPO_ROOT}/reports/evidence/core-flow-smoke/${STAMP}"
CHROMIUM_BIN="${CHROMIUM_BIN:-chromium}"
SMOKE_EXPECT_HEALTH_VERSION="${SMOKE_EXPECT_HEALTH_VERSION:-bl334-split-smoke}"

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

assert_health_version() {
  local service_name="$1"
  local json_payload="$2"
  local expected_version="$3"

  "${PYTHON_BIN}" - "$service_name" "$expected_version" "$json_payload" <<'PY'
import json
import sys

service_name = sys.argv[1]
expected_version = sys.argv[2]
payload = json.loads(sys.argv[3])

observed_version = payload.get("version")
if not observed_version and isinstance(payload.get("build"), dict):
    observed_version = payload["build"].get("version")

if str(observed_version or "") != expected_version:
    raise SystemExit(
        f"{service_name} health version mismatch: expected={expected_version!r}, observed={observed_version!r}"
    )
PY
}

capture_core_flow_failure_artifacts() {
  local core_flow_exit="$1"

  mkdir -p "${CORE_FLOW_FAILURE_EVIDENCE_DIR}"

  cp "${CORE_FLOW_LOG}" "${CORE_FLOW_FAILURE_EVIDENCE_DIR}/core-flow-unittest.log" || true
  cp "${API_LOG}" "${CORE_FLOW_FAILURE_EVIDENCE_DIR}/api-smoke.log" || true
  cp "${UI_LOG}" "${CORE_FLOW_FAILURE_EVIDENCE_DIR}/ui-smoke.log" || true

  if command -v "${CHROMIUM_BIN}" >/dev/null 2>&1; then
    "${CHROMIUM_BIN}" \
      --headless \
      --disable-gpu \
      --no-sandbox \
      --window-size=1440,1800 \
      "--screenshot=${CORE_FLOW_FAILURE_EVIDENCE_DIR}/core-flow-failure-gui.png" \
      "http://127.0.0.1:${UI_PORT}/gui" \
      >"${CORE_FLOW_FAILURE_EVIDENCE_DIR}/chromium-screenshot.log" 2>&1 || true
  fi

  {
    echo "# Core flow smoke failure trace"
    echo
    echo "- Timestamp (UTC): ${STAMP}"
    echo "- Command: ${PYTHON_BIN} -m unittest -q ${CORE_FLOW_TEST_TARGET}"
    echo "- Exit code: ${core_flow_exit}"
    echo "- Scenario: login -> search -> ranking list -> detail"
    echo "- API log: ${API_LOG}"
    echo "- UI log: ${UI_LOG}"
    echo
    echo "## Unittest output (tail -n 200)"
    echo '```text'
    tail -n 200 "${CORE_FLOW_LOG}" || true
    echo '```'
    echo
    echo "## API smoke log (tail -n 80)"
    echo '```text'
    tail -n 80 "${API_LOG}" || true
    echo '```'
    echo
    echo "## UI smoke log (tail -n 80)"
    echo '```text'
    tail -n 80 "${UI_LOG}" || true
    echo '```'
  } >"${CORE_FLOW_FAILURE_EVIDENCE_DIR}/core-flow-failure-trace.md"
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

API_HEALTH_RESPONSE="$(${CURL_BIN} -sS "http://127.0.0.1:${API_PORT}/health")"
validate_json_bool_true "${API_HEALTH_RESPONSE}" "ok"

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
assert_health_version "ui" "${UI_HEALTH_RESPONSE}" "${SMOKE_EXPECT_HEALTH_VERSION}"

UI_HEALTH_VERSION="$(${PYTHON_BIN} - "${UI_HEALTH_RESPONSE}" <<'PY'
import json
import sys
payload = json.loads(sys.argv[1])
value = payload.get("version")
if not value and isinstance(payload.get("build"), dict):
    value = payload["build"].get("version")
print(value or "")
PY
)"

UI_GUI_HTML="$(${CURL_BIN} -sS "http://127.0.0.1:${UI_PORT}/gui")"
if ! grep -q "geo-ranking.ch GUI MVP" <<<"${UI_GUI_HTML}"; then
  echo "ERROR: UI smoke failed, expected GUI marker not found" >&2
  exit 1
fi

echo "[BL-334.6] Core flow auth smoke (login -> search -> ranking list -> detail)"
CORE_FLOW_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
CORE_FLOW_START_TS="$(date +%s)"
set +e
"${PYTHON_BIN}" -m unittest -q "${CORE_FLOW_TEST_TARGET}" >"${CORE_FLOW_LOG}" 2>&1
CORE_FLOW_EXIT_CODE="$?"
set -e
CORE_FLOW_DURATION_SECONDS="$(( $(date +%s) - CORE_FLOW_START_TS ))"

if (( CORE_FLOW_EXIT_CODE != 0 )); then
  capture_core_flow_failure_artifacts "${CORE_FLOW_EXIT_CODE}"
  echo "ERROR: core flow smoke failed. Evidence: ${CORE_FLOW_FAILURE_EVIDENCE_DIR}" >&2
  exit 1
fi

if (( CORE_FLOW_DURATION_SECONDS > CORE_FLOW_SMOKE_MAX_SECONDS )); then
  echo "ERROR: core flow smoke exceeded budget (${CORE_FLOW_DURATION_SECONDS}s > ${CORE_FLOW_SMOKE_MAX_SECONDS}s)" >&2
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
    "healthVersionExpected": "${SMOKE_EXPECT_HEALTH_VERSION}",
    "healthVersionObserved": "${UI_HEALTH_VERSION}",
    "guiUrl": "http://127.0.0.1:${UI_PORT}/gui",
    "result": "pass",
    "log": "${UI_LOG}"
  },
  "core_flow": {
    "entrypoint": "python -m unittest -q ${CORE_FLOW_TEST_TARGET}",
    "scenario": "login -> search -> ranking list -> detail",
    "started_at_utc": "${CORE_FLOW_STARTED_AT}",
    "duration_seconds": ${CORE_FLOW_DURATION_SECONDS},
    "budget_seconds": ${CORE_FLOW_SMOKE_MAX_SECONDS},
    "result": "pass",
    "log": "${CORE_FLOW_LOG}"
  },
  "result": "pass"
}
EOF

echo "✅ BL-334.5 split smokes passed"
echo "- evidence: ${OUT_JSON}"
echo "- api log:  ${API_LOG}"
echo "- ui log:   ${UI_LOG}"
echo "- ui health version: observed=${UI_HEALTH_VERSION}, expected=${SMOKE_EXPECT_HEALTH_VERSION}"
echo "- core-flow log: ${CORE_FLOW_LOG}"
echo "- core-flow duration: ${CORE_FLOW_DURATION_SECONDS}s (budget ${CORE_FLOW_SMOKE_MAX_SECONDS}s)"
