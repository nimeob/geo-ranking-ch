#!/usr/bin/env bash
# BL-31.6.c: Kombinierter Nachweislauf für App/API Smoke + UI-Monitoring-Baseline.
set -euo pipefail

require_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "ERROR: required binary not found: ${bin}" >&2
    exit 2
  fi
}

require_bin python3

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SMOKE_SCRIPT="${SMOKE_SCRIPT:-${SCRIPT_DIR}/run_bl31_routing_tls_smoke.sh}"
MONITORING_SCRIPT="${MONITORING_SCRIPT:-${SCRIPT_DIR}/check_bl31_ui_monitoring_baseline.sh}"
OUT_DIR="${OUT_DIR:-artifacts/bl31}"
BL31_STRICT_CORS="${BL31_STRICT_CORS:-0}"
AWS_REGION="${AWS_REGION:-eu-central-1}"

mkdir -p "${OUT_DIR}"

if [[ ! -x "${SMOKE_SCRIPT}" ]]; then
  echo "ERROR: smoke script missing or not executable: ${SMOKE_SCRIPT}" >&2
  exit 2
fi

if [[ ! -x "${MONITORING_SCRIPT}" ]]; then
  echo "ERROR: monitoring script missing or not executable: ${MONITORING_SCRIPT}" >&2
  exit 2
fi

ROLLOUT_EVIDENCE="${BL31_ROLLOUT_EVIDENCE:-}"
if [[ -z "${ROLLOUT_EVIDENCE}" ]]; then
  latest_rollout="$(ls -1t "${OUT_DIR}"/*-bl31-ui-ecs-rollout.json 2>/dev/null | head -n 1 || true)"
  ROLLOUT_EVIDENCE="${latest_rollout}"
fi

if [[ -z "${ROLLOUT_EVIDENCE}" || ! -f "${ROLLOUT_EVIDENCE}" ]]; then
  echo "ERROR: rollout evidence not found. Set BL31_ROLLOUT_EVIDENCE or run setup_bl31_ui_service_rollout.sh first." >&2
  exit 3
fi

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
SMOKE_JSON="${OUT_DIR}/${stamp}-bl31-routing-tls-smoke.json"
SMOKE_LOG="${OUT_DIR}/${stamp}-bl31-routing-tls-smoke.log"
MONITORING_LOG="${OUT_DIR}/${stamp}-bl31-ui-monitoring-baseline.log"
SUMMARY_JSON="${OUT_DIR}/${stamp}-bl31-app-api-monitoring-evidence.json"

mapfile -t derived < <(python3 - "${ROLLOUT_EVIDENCE}" <<'PY'
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))

api_health = payload.get("apiService", {}).get("healthUrl", "")
app_health = payload.get("uiService", {}).get("healthUrl", "")


def base_from_health(url: str, expected_path: str) -> str:
    if not url:
        return ""
    parts = urlsplit(url)
    path = parts.path or ""
    if path.endswith(expected_path):
        base_path = path[: -len(expected_path)]
    else:
        base_path = path
    if not base_path:
        base_path = ""
    return urlunsplit((parts.scheme, parts.netloc, base_path.rstrip("/"), "", ""))

api_base = base_from_health(api_health, "/health")
app_base = base_from_health(app_health, "/healthz")
if app_base:
    app_parts = urlsplit(app_base)
    cors_origin = urlunsplit((app_parts.scheme, app_parts.netloc, "", "", ""))
else:
    cors_origin = ""

print(api_base)
print(app_base)
print(cors_origin)
PY
)

BL31_API_BASE_URL="${BL31_API_BASE_URL:-${derived[0]:-}}"
BL31_APP_BASE_URL="${BL31_APP_BASE_URL:-${derived[1]:-}}"
BL31_CORS_ORIGIN="${BL31_CORS_ORIGIN:-${derived[2]:-}}"

if [[ -z "${BL31_API_BASE_URL}" || -z "${BL31_APP_BASE_URL}" ]]; then
  echo "ERROR: Could not derive BL31_API_BASE_URL/BL31_APP_BASE_URL from ${ROLLOUT_EVIDENCE}." >&2
  echo "Set BL31_API_BASE_URL and BL31_APP_BASE_URL explicitly." >&2
  exit 4
fi

if [[ "${BL31_STRICT_CORS}" != "0" && "${BL31_STRICT_CORS}" != "1" ]]; then
  echo "ERROR: BL31_STRICT_CORS must be 0 or 1 (got ${BL31_STRICT_CORS})." >&2
  exit 2
fi

echo "[BL-31.6.c] Running smoke checks"
echo "  - API: ${BL31_API_BASE_URL}"
echo "  - APP: ${BL31_APP_BASE_URL}"
set +e
BL31_API_BASE_URL="${BL31_API_BASE_URL}" \
BL31_APP_BASE_URL="${BL31_APP_BASE_URL}" \
BL31_CORS_ORIGIN="${BL31_CORS_ORIGIN}" \
BL31_STRICT_CORS="${BL31_STRICT_CORS}" \
BL31_OUTPUT_JSON="${SMOKE_JSON}" \
"${SMOKE_SCRIPT}" >"${SMOKE_LOG}" 2>&1
smoke_rc=$?
set -e

echo "[BL-31.6.c] Running UI monitoring baseline check"
set +e
AWS_REGION="${AWS_REGION}" "${MONITORING_SCRIPT}" >"${MONITORING_LOG}" 2>&1
monitoring_rc=$?
set -e

python3 - <<'PY' \
  "${SUMMARY_JSON}" \
  "${stamp}" \
  "${ROLLOUT_EVIDENCE}" \
  "${BL31_API_BASE_URL}" \
  "${BL31_APP_BASE_URL}" \
  "${BL31_CORS_ORIGIN}" \
  "${BL31_STRICT_CORS}" \
  "${SMOKE_JSON}" \
  "${SMOKE_LOG}" \
  "${smoke_rc}" \
  "${MONITORING_LOG}" \
  "${monitoring_rc}" \
  "${AWS_REGION}"
import json
import pathlib
import sys

(
    out_path,
    stamp,
    rollout_evidence,
    api_base_url,
    app_base_url,
    cors_origin,
    strict_cors,
    smoke_json,
    smoke_log,
    smoke_rc,
    monitoring_log,
    monitoring_rc,
    aws_region,
) = sys.argv[1:]

smoke_payload = {}
smoke_json_path = pathlib.Path(smoke_json)
if smoke_json_path.exists():
    try:
        smoke_payload = json.loads(smoke_json_path.read_text(encoding="utf-8"))
    except Exception:
        smoke_payload = {"parseError": True}

smoke_log_text = pathlib.Path(smoke_log).read_text(encoding="utf-8", errors="replace") if pathlib.Path(smoke_log).exists() else ""
monitoring_log_text = pathlib.Path(monitoring_log).read_text(encoding="utf-8", errors="replace") if pathlib.Path(monitoring_log).exists() else ""

smoke_rc_i = int(smoke_rc)
monitoring_rc_i = int(monitoring_rc)

if smoke_rc_i != 0 or (monitoring_rc_i not in (0, 10) and monitoring_rc_i > 0):
    overall_status = "fail"
elif monitoring_rc_i == 10:
    overall_status = "warn"
else:
    overall_status = "pass"

payload = {
    "timestampUtc": stamp,
    "issue": "#347",
    "overall": {
        "status": overall_status,
        "smokeExitCode": smoke_rc_i,
        "monitoringExitCode": monitoring_rc_i,
    },
    "inputs": {
        "rolloutEvidence": rollout_evidence,
        "apiBaseUrl": api_base_url,
        "appBaseUrl": app_base_url,
        "corsOrigin": cors_origin,
        "strictCors": strict_cors == "1",
        "awsRegion": aws_region,
    },
    "smoke": {
        "script": "scripts/run_bl31_routing_tls_smoke.sh",
        "outputJson": smoke_json,
        "outputLog": smoke_log,
        "result": smoke_payload,
        "stdout": smoke_log_text,
    },
    "monitoring": {
        "script": "scripts/check_bl31_ui_monitoring_baseline.sh",
        "outputLog": monitoring_log,
        "stdout": monitoring_log_text,
    },
}

out = pathlib.Path(out_path)
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(out)
PY

if [[ ${smoke_rc} -ne 0 ]]; then
  echo "ERROR: smoke script failed (rc=${smoke_rc}). See ${SMOKE_LOG}" >&2
  exit ${smoke_rc}
fi

if [[ ${monitoring_rc} -ne 0 && ${monitoring_rc} -ne 10 ]]; then
  echo "ERROR: monitoring baseline check failed (rc=${monitoring_rc}). See ${MONITORING_LOG}" >&2
  exit ${monitoring_rc}
fi

if [[ ${monitoring_rc} -eq 10 ]]; then
  echo "WARN: monitoring baseline returned warnings (rc=10). See ${MONITORING_LOG}" >&2
fi

echo "Done. Combined evidence: ${SUMMARY_JSON}"