#!/usr/bin/env bash
set -euo pipefail

# BL-18.1: reproduzierbarer Remote-Smoke-Test für POST /analyze.
# Erwartung: HTTP 200 + ok=true + result-Objekt.
#
# Nutzung:
#   DEV_BASE_URL="https://<endpoint>" ./scripts/run_remote_api_smoketest.sh
#   DEV_BASE_URL="https://<endpoint>/health" ./scripts/run_remote_api_smoketest.sh
#   DEV_BASE_URL="https://<endpoint>" DEV_API_AUTH_TOKEN="<token>" ./scripts/run_remote_api_smoketest.sh
#
# Optionale Env-Variablen:
#   SMOKE_QUERY="St. Leonhard-Strasse 40, St. Gallen"
#   SMOKE_MODE="basic"                    # basic|extended|risk (wird kleingeschrieben)
#   SMOKE_TIMEOUT_SECONDS="20"
#   CURL_MAX_TIME="30"
#   SMOKE_REQUEST_ID="bl18-..."
#   SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke.json"

trim() {
  python3 - "$1" <<'PY'
import sys
print(sys.argv[1].strip())
PY
}

if [[ -z "${DEV_BASE_URL:-}" ]]; then
  echo "[BL-18.1] DEV_BASE_URL ist nicht gesetzt. Beispiel: DEV_BASE_URL=https://<endpoint> ./scripts/run_remote_api_smoketest.sh" >&2
  exit 2
fi

DEV_BASE_URL_TRIMMED="$(trim "${DEV_BASE_URL}")"
if [[ -z "${DEV_BASE_URL_TRIMMED}" ]]; then
  echo "[BL-18.1] DEV_BASE_URL ist leer nach Whitespace-Normalisierung." >&2
  exit 2
fi

if [[ ! "${DEV_BASE_URL_TRIMMED}" =~ ^[Hh][Tt][Tt][Pp]([Ss])?:// ]]; then
  echo "[BL-18.1] DEV_BASE_URL muss mit http:// oder https:// beginnen (aktuell: ${DEV_BASE_URL})." >&2
  exit 2
fi

strip_trailing_slashes() {
  local value="$1"
  while [[ "$value" == */ ]]; do
    value="${value%/}"
  done
  printf '%s' "$value"
}

BASE_URL="$(strip_trailing_slashes "${DEV_BASE_URL_TRIMMED}")"
while true; do
  lower="${BASE_URL,,}"
  if [[ "${lower}" == */health ]]; then
    BASE_URL="$(strip_trailing_slashes "${BASE_URL:0:${#BASE_URL}-7}")"
    continue
  fi
  if [[ "${lower}" == */analyze ]]; then
    BASE_URL="$(strip_trailing_slashes "${BASE_URL:0:${#BASE_URL}-8}")"
    continue
  fi
  break
done

if [[ -z "${BASE_URL}" ]]; then
  echo "[BL-18.1] DEV_BASE_URL ist nach Normalisierung leer/ungültig." >&2
  exit 2
fi

ANALYZE_URL="${BASE_URL}/analyze"

SMOKE_QUERY="$(trim "${SMOKE_QUERY:-St. Leonhard-Strasse 40, St. Gallen}")"
SMOKE_MODE="$(trim "${SMOKE_MODE:-basic}")"
SMOKE_MODE="${SMOKE_MODE,,}"
SMOKE_TIMEOUT_SECONDS="$(trim "${SMOKE_TIMEOUT_SECONDS:-20}")"
CURL_MAX_TIME="$(trim "${CURL_MAX_TIME:-30}")"
SMOKE_OUTPUT_JSON="$(trim "${SMOKE_OUTPUT_JSON:-}")"
SMOKE_REQUEST_ID="$(trim "${SMOKE_REQUEST_ID:-bl18-$(date +%s)}")"

if [[ -z "${SMOKE_QUERY}" ]]; then
  echo "[BL-18.1] SMOKE_QUERY ist leer nach Whitespace-Normalisierung." >&2
  exit 2
fi

if [[ -z "${SMOKE_REQUEST_ID}" ]]; then
  echo "[BL-18.1] SMOKE_REQUEST_ID ist leer nach Whitespace-Normalisierung." >&2
  exit 2
fi

if ! python3 - "${SMOKE_TIMEOUT_SECONDS}" "${CURL_MAX_TIME}" <<'PY'
import math
import sys

try:
    smoke_timeout = float(sys.argv[1])
    curl_max = float(sys.argv[2])
except ValueError:
    raise SystemExit(1)

if not math.isfinite(smoke_timeout) or smoke_timeout <= 0:
    raise SystemExit(1)
if not math.isfinite(curl_max) or curl_max <= 0:
    raise SystemExit(1)
if curl_max < smoke_timeout:
    raise SystemExit(1)
PY
then
  echo "[BL-18.1] Timeout-Werte ungültig: SMOKE_TIMEOUT_SECONDS und CURL_MAX_TIME müssen Zahlen >0 sein, zusätzlich CURL_MAX_TIME >= SMOKE_TIMEOUT_SECONDS." >&2
  exit 2
fi

case "${SMOKE_MODE}" in
  basic|extended|risk) ;;
  *)
    echo "[BL-18.1] Ungültiger SMOKE_MODE='${SMOKE_MODE}' (erlaubt: basic|extended|risk)." >&2
    exit 2
    ;;
esac

AUTH_HEADER=()
if [[ -n "${DEV_API_AUTH_TOKEN:-}" ]]; then
  DEV_API_AUTH_TOKEN_TRIMMED="$(trim "${DEV_API_AUTH_TOKEN}")"
  if [[ -z "${DEV_API_AUTH_TOKEN_TRIMMED}" ]]; then
    echo "[BL-18.1] DEV_API_AUTH_TOKEN ist leer nach Whitespace-Normalisierung." >&2
    exit 2
  fi
  AUTH_HEADER=(-H "Authorization: Bearer ${DEV_API_AUTH_TOKEN_TRIMMED}")
fi

export SMOKE_QUERY SMOKE_MODE SMOKE_TIMEOUT_SECONDS
REQUEST_BODY="$(python3 - <<'PY'
import json
import os

payload = {
    "query": os.environ["SMOKE_QUERY"],
    "intelligence_mode": os.environ["SMOKE_MODE"],
    "timeout_seconds": float(os.environ["SMOKE_TIMEOUT_SECONDS"]),
}
print(json.dumps(payload, ensure_ascii=False))
PY
)"

TMP_BODY="$(mktemp)"
TMP_HEADERS="$(mktemp)"
trap 'rm -f "$TMP_BODY" "$TMP_HEADERS"' EXIT

STARTED_AT_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
START_EPOCH="$(date +%s)"

set +e
HTTP_CODE=$(curl -sS -m "${CURL_MAX_TIME}" \
  -D "${TMP_HEADERS}" \
  -o "${TMP_BODY}" \
  -w "%{http_code}" \
  -X POST "${ANALYZE_URL}" \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: ${SMOKE_REQUEST_ID}" \
  "${AUTH_HEADER[@]}" \
  -d "${REQUEST_BODY}")
CURL_EXIT=$?
set -e

ENDED_AT_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
END_EPOCH="$(date +%s)"
DURATION_SECONDS="$((END_EPOCH - START_EPOCH))"

if [[ "${CURL_EXIT}" -ne 0 ]]; then
  echo "[BL-18.1] FAIL: curl-Aufruf fehlgeschlagen (exit=${CURL_EXIT})."
  if [[ -s "${TMP_BODY}" ]]; then
    head -c 1200 "${TMP_BODY}" || true
    echo
  fi

  if [[ -n "${SMOKE_OUTPUT_JSON}" ]]; then
    mkdir -p "$(dirname -- "${SMOKE_OUTPUT_JSON}")"
    python3 - "${SMOKE_OUTPUT_JSON}" <<'PY'
import json
import os
import sys

out = sys.argv[1]
report = {
    "status": "fail",
    "reason": "curl_error",
    "http_status": None,
    "url": os.environ["ANALYZE_URL"],
    "request_id": os.environ["SMOKE_REQUEST_ID"],
    "started_at_utc": os.environ["STARTED_AT_UTC"],
    "ended_at_utc": os.environ["ENDED_AT_UTC"],
    "duration_seconds": int(os.environ["DURATION_SECONDS"]),
}
with open(out, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
PY
  fi

  exit 1
fi

export ANALYZE_URL SMOKE_REQUEST_ID STARTED_AT_UTC ENDED_AT_UTC DURATION_SECONDS SMOKE_OUTPUT_JSON
python3 - "${HTTP_CODE}" "${TMP_BODY}" <<'PY'
import json
import os
import pathlib
import sys

http_code = int(sys.argv[1])
body = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")

report = {
    "status": "fail",
    "reason": None,
    "http_status": http_code,
    "url": os.environ["ANALYZE_URL"],
    "request_id": os.environ["SMOKE_REQUEST_ID"],
    "started_at_utc": os.environ["STARTED_AT_UTC"],
    "ended_at_utc": os.environ["ENDED_AT_UTC"],
    "duration_seconds": int(os.environ["DURATION_SECONDS"]),
    "result_keys": [],
}

try:
    data = json.loads(body)
except json.JSONDecodeError:
    report["reason"] = "invalid_json"
    print(f"[BL-18.1] FAIL: Response ist kein valides JSON (HTTP {http_code}).")
    print(body)
else:
    if http_code != 200:
        report["reason"] = "http_status"
        print(f"[BL-18.1] FAIL: Erwartet HTTP 200, erhalten {http_code}.")
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif data.get("ok") is not True:
        report["reason"] = "ok_flag"
        print("[BL-18.1] FAIL: Feld 'ok' ist nicht true.")
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        result = data.get("result")
        if not isinstance(result, dict) or not result:
            report["reason"] = "missing_result"
            print("[BL-18.1] FAIL: Feld 'result' fehlt oder ist leer.")
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            report["status"] = "pass"
            report["reason"] = "ok"
            report["result_keys"] = sorted(result.keys())
            print("[BL-18.1] PASS: HTTP 200, ok=true, result vorhanden.")
            print(json.dumps({
                "request_id": report["request_id"],
                "duration_seconds": report["duration_seconds"],
                "result_keys": report["result_keys"][:12],
            }, ensure_ascii=False, indent=2))

out = os.environ.get("SMOKE_OUTPUT_JSON", "").strip()
if out:
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

if report["status"] != "pass":
    raise SystemExit(1)
PY
