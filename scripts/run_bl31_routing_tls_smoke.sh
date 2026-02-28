#!/usr/bin/env bash
set -euo pipefail

# BL-31 Routing/TLS Smoke-Catch-up (Issue #336)
# Prüft in einer reproduzierbaren Sequenz:
#  1) API-Health (`/health`)
#  2) UI-Reachability (`/healthz`)
#  3) CORS-Baseline auf API `/analyze` via OPTIONS-Preflight
#
# Nutzung (lokal):
#   BL31_API_BASE_URL="http://127.0.0.1:8080" \
#   BL31_APP_BASE_URL="http://127.0.0.1:8081" \
#   ./scripts/run_bl31_routing_tls_smoke.sh
#
# Optional:
#   BL31_CORS_ORIGIN="https://app.geo-ranking.ch"   # default: Origin aus BL31_APP_BASE_URL
#   BL31_STRICT_CORS="1"                            # 1 => fehlende/falsche CORS-Header sind Hard-Fail
#   BL31_CURL_MAX_TIME="10"
#   BL31_OUTPUT_JSON="artifacts/bl31-routing-tls-smoke.json"

trim() {
  python3 - "$1" <<'PY'
import sys
print(sys.argv[1].strip())
PY
}

validate_base_url() {
  local label="$1"
  local value="$2"
  if [[ -z "${value}" ]]; then
    echo "[BL-31] ${label} ist leer." >&2
    exit 2
  fi

  if ! python3 - "$value" <<'PY'
import sys
from urllib.parse import urlsplit

raw = sys.argv[1]
if any(ch.isspace() for ch in raw):
    raise SystemExit(1)
parts = urlsplit(raw)
if parts.scheme.lower() not in {"http", "https"}:
    raise SystemExit(1)
if not parts.netloc:
    raise SystemExit(1)
if parts.query or parts.fragment:
    raise SystemExit(1)
PY
  then
    echo "[BL-31] ${label} muss eine gültige http(s)-Base-URL ohne Query/Fragment sein (aktuell: ${value})." >&2
    exit 2
  fi
}

read_json_field() {
  local file_path="$1"
  local field_name="$2"
  python3 - "$file_path" "$field_name" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
value = payload
for part in sys.argv[2].split("."):
    if isinstance(value, dict) and part in value:
        value = value[part]
    else:
        print("")
        raise SystemExit(0)
print(value)
PY
}

read_header_value() {
  local headers_file="$1"
  local header_name="$2"
  python3 - "$headers_file" "$header_name" <<'PY'
import sys
from pathlib import Path

needle = sys.argv[2].strip().lower()
value = ""
for raw_line in Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines():
    if ":" not in raw_line:
        continue
    key, raw_val = raw_line.split(":", 1)
    if key.strip().lower() == needle:
        value = raw_val.strip()
print(value)
PY
}

BL31_API_BASE_URL="${BL31_API_BASE_URL:-http://127.0.0.1:8080}"
BL31_APP_BASE_URL="${BL31_APP_BASE_URL:-http://127.0.0.1:8081}"
BL31_CORS_ORIGIN="${BL31_CORS_ORIGIN:-}"
BL31_STRICT_CORS="${BL31_STRICT_CORS:-0}"
BL31_CURL_MAX_TIME="${BL31_CURL_MAX_TIME:-10}"
BL31_OUTPUT_JSON="${BL31_OUTPUT_JSON:-}"

BL31_API_BASE_URL="$(trim "${BL31_API_BASE_URL}")"
BL31_APP_BASE_URL="$(trim "${BL31_APP_BASE_URL}")"
BL31_CORS_ORIGIN="$(trim "${BL31_CORS_ORIGIN}")"
BL31_STRICT_CORS="$(trim "${BL31_STRICT_CORS}")"
BL31_CURL_MAX_TIME="$(trim "${BL31_CURL_MAX_TIME}")"
BL31_OUTPUT_JSON="$(trim "${BL31_OUTPUT_JSON}")"

validate_base_url "BL31_API_BASE_URL" "${BL31_API_BASE_URL}"
validate_base_url "BL31_APP_BASE_URL" "${BL31_APP_BASE_URL}"

if [[ -z "${BL31_CORS_ORIGIN}" ]]; then
  BL31_CORS_ORIGIN="$(python3 - "${BL31_APP_BASE_URL}" <<'PY'
import sys
from urllib.parse import urlsplit

parts = urlsplit(sys.argv[1])
print(f"{parts.scheme}://{parts.netloc}")
PY
)"
fi

if [[ "${BL31_STRICT_CORS}" != "0" && "${BL31_STRICT_CORS}" != "1" ]]; then
  echo "[BL-31] BL31_STRICT_CORS muss 0 oder 1 sein (aktuell: ${BL31_STRICT_CORS})." >&2
  exit 2
fi

if ! python3 - "${BL31_CURL_MAX_TIME}" <<'PY'
import math
import sys

value = float(sys.argv[1])
if not math.isfinite(value) or value <= 0:
    raise SystemExit(1)
PY
then
  echo "[BL-31] BL31_CURL_MAX_TIME muss eine endliche Zahl > 0 sein (aktuell: ${BL31_CURL_MAX_TIME})." >&2
  exit 2
fi

if [[ -n "${BL31_OUTPUT_JSON}" ]]; then
  if [[ -d "${BL31_OUTPUT_JSON}" ]]; then
    echo "[BL-31] BL31_OUTPUT_JSON darf kein Verzeichnis sein: ${BL31_OUTPUT_JSON}" >&2
    exit 2
  fi
  output_parent="$(dirname -- "${BL31_OUTPUT_JSON}")"
  mkdir -p -- "${output_parent}"
fi

api_health_url="${BL31_API_BASE_URL%/}/health"
app_healthz_url="${BL31_APP_BASE_URL%/}/healthz"
api_analyze_url="${BL31_API_BASE_URL%/}/analyze"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT

api_body="${tmp_dir}/api_health.body"
api_headers="${tmp_dir}/api_health.headers"
app_body="${tmp_dir}/app_health.body"
app_headers="${tmp_dir}/app_health.headers"
cors_body="${tmp_dir}/cors.body"
cors_headers="${tmp_dir}/cors.headers"

api_status=""
api_reason=""
api_http_status=""
api_service=""
api_ok_field=""

app_status=""
app_reason=""
app_http_status=""
app_service=""
app_ok_field=""

cors_status=""
cors_reason=""
cors_http_status=""
cors_allow_origin=""

set +e
api_http_status="$(curl -sS -o "${api_body}" -D "${api_headers}" -w "%{http_code}" --max-time "${BL31_CURL_MAX_TIME}" "${api_health_url}")"
api_curl_rc=$?
set -e

if [[ ${api_curl_rc} -ne 0 ]]; then
  api_status="fail"
  api_reason="curl_error"
else
  api_ok_field="$(read_json_field "${api_body}" "ok")"
  api_service="$(read_json_field "${api_body}" "service")"
  if [[ "${api_http_status}" == "200" && "${api_ok_field}" == "True" ]]; then
    api_status="pass"
    api_reason="ok"
  else
    api_status="fail"
    api_reason="unexpected_response"
  fi
fi

set +e
app_http_status="$(curl -sS -o "${app_body}" -D "${app_headers}" -w "%{http_code}" --max-time "${BL31_CURL_MAX_TIME}" "${app_healthz_url}")"
app_curl_rc=$?
set -e

if [[ ${app_curl_rc} -ne 0 ]]; then
  app_status="fail"
  app_reason="curl_error"
else
  app_ok_field="$(read_json_field "${app_body}" "ok")"
  app_service="$(read_json_field "${app_body}" "service")"
  if [[ "${app_http_status}" == "200" && "${app_ok_field}" == "True" ]]; then
    app_status="pass"
    app_reason="ok"
  else
    app_status="fail"
    app_reason="unexpected_response"
  fi
fi

set +e
cors_http_status="$(curl -sS -X OPTIONS -o "${cors_body}" -D "${cors_headers}" -w "%{http_code}" \
  --max-time "${BL31_CURL_MAX_TIME}" \
  -H "Origin: ${BL31_CORS_ORIGIN}" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,authorization,x-request-id" \
  "${api_analyze_url}")"
cors_curl_rc=$?
set -e

if [[ ${cors_curl_rc} -ne 0 ]]; then
  cors_status="fail"
  cors_reason="curl_error"
else
  cors_allow_origin="$(read_header_value "${cors_headers}" "Access-Control-Allow-Origin")"
  if [[ "${cors_allow_origin}" == "*" ]]; then
    cors_status="fail"
    cors_reason="wildcard_origin_not_allowed"
  elif [[ -z "${cors_allow_origin}" ]]; then
    cors_status="warn"
    cors_reason="missing_allow_origin"
  elif [[ "${cors_allow_origin}" != "${BL31_CORS_ORIGIN}" ]]; then
    cors_status="warn"
    cors_reason="allow_origin_mismatch"
  elif [[ "${cors_http_status}" =~ ^2[0-9][0-9]$ ]]; then
    cors_status="pass"
    cors_reason="ok"
  else
    cors_status="warn"
    cors_reason="non_2xx_preflight"
  fi
fi

overall_status="pass"
overall_reason="ok"

if [[ "${api_status}" != "pass" || "${app_status}" != "pass" ]]; then
  overall_status="fail"
  overall_reason="health_or_reachability_failed"
fi

if [[ "${BL31_STRICT_CORS}" == "1" && "${cors_status}" != "pass" ]]; then
  overall_status="fail"
  overall_reason="cors_baseline_failed"
fi

echo "[BL-31] API health (${api_health_url}): ${api_status} (http=${api_http_status:-n/a}, reason=${api_reason}, service=${api_service:-n/a})"
echo "[BL-31] APP reachability (${app_healthz_url}): ${app_status} (http=${app_http_status:-n/a}, reason=${app_reason}, service=${app_service:-n/a})"
echo "[BL-31] CORS baseline (${api_analyze_url}, origin=${BL31_CORS_ORIGIN}): ${cors_status} (http=${cors_http_status:-n/a}, reason=${cors_reason}, allow-origin=${cors_allow_origin:-<missing>})"
echo "[BL-31] OVERALL: ${overall_status} (${overall_reason})"

if [[ -n "${BL31_OUTPUT_JSON}" ]]; then
  python3 - \
    "${BL31_OUTPUT_JSON}" \
    "${overall_status}" "${overall_reason}" \
    "${api_status}" "${api_reason}" "${api_http_status}" "${api_service}" "${api_ok_field}" \
    "${app_status}" "${app_reason}" "${app_http_status}" "${app_service}" "${app_ok_field}" \
    "${cors_status}" "${cors_reason}" "${cors_http_status}" "${cors_allow_origin}" "${BL31_CORS_ORIGIN}" \
    "${BL31_STRICT_CORS}" "${api_health_url}" "${app_healthz_url}" "${api_analyze_url}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

(
    out_path,
    overall_status,
    overall_reason,
    api_status,
    api_reason,
    api_http_status,
    api_service,
    api_ok,
    app_status,
    app_reason,
    app_http_status,
    app_service,
    app_ok,
    cors_status,
    cors_reason,
    cors_http_status,
    cors_allow_origin,
    cors_expected_origin,
    strict_cors,
    api_health_url,
    app_healthz_url,
    api_analyze_url,
) = sys.argv[1:]

payload = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "overall": {
        "status": overall_status,
        "reason": overall_reason,
        "strict_cors": strict_cors == "1",
    },
    "checks": {
        "api_health": {
            "status": api_status,
            "reason": api_reason,
            "http_status": int(api_http_status) if api_http_status.isdigit() else api_http_status,
            "service": api_service or None,
            "ok": api_ok == "True",
            "url": api_health_url,
        },
        "app_reachability": {
            "status": app_status,
            "reason": app_reason,
            "http_status": int(app_http_status) if app_http_status.isdigit() else app_http_status,
            "service": app_service or None,
            "ok": app_ok == "True",
            "url": app_healthz_url,
        },
        "cors_baseline": {
            "status": cors_status,
            "reason": cors_reason,
            "http_status": int(cors_http_status) if cors_http_status.isdigit() else cors_http_status,
            "allow_origin": cors_allow_origin or None,
            "expected_origin": cors_expected_origin,
            "url": api_analyze_url,
        },
    },
}

path = Path(out_path)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
fi

if [[ "${overall_status}" != "pass" ]]; then
  exit 1
fi
