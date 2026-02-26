#!/usr/bin/env bash
set -euo pipefail

# Reproduzierbarer Remote-Smoke-Test für Issue BL-18.1
# Erwartet öffentliche Base-URL des Services und prüft POST /analyze auf 200 + ok=true + result-Objekt.
#
# Nutzung:
#   DEV_BASE_URL="https://<endpoint>" ./scripts/run_remote_api_smoketest.sh
#   DEV_BASE_URL="https://<endpoint>" DEV_API_AUTH_TOKEN="<token>" ./scripts/run_remote_api_smoketest.sh
#
# Optionale Env-Variablen:
#   SMOKE_QUERY="St. Leonhard-Strasse 40, St. Gallen"
#   SMOKE_MODE="basic"   # basic|extended|risk
#   SMOKE_TIMEOUT_SECONDS="20"
#   CURL_MAX_TIME="45"
#   CURL_RETRY_COUNT="3"
#   CURL_RETRY_DELAY="2"
#   SMOKE_REQUEST_ID="bl18-<id>"
#   SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke.json"

if [[ -z "${DEV_BASE_URL:-}" ]]; then
  echo "[BL-18.1] DEV_BASE_URL ist nicht gesetzt. Beispiel: DEV_BASE_URL=https://<endpoint> ./scripts/run_remote_api_smoketest.sh" >&2
  exit 2
fi

SMOKE_QUERY="${SMOKE_QUERY:-St. Leonhard-Strasse 40, St. Gallen}"
SMOKE_MODE="${SMOKE_MODE:-basic}"
SMOKE_TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-20}"
CURL_MAX_TIME="${CURL_MAX_TIME:-45}"
CURL_RETRY_COUNT="${CURL_RETRY_COUNT:-3}"
CURL_RETRY_DELAY="${CURL_RETRY_DELAY:-2}"
SMOKE_OUTPUT_JSON="${SMOKE_OUTPUT_JSON:-}"
SMOKE_REQUEST_ID="${SMOKE_REQUEST_ID:-bl18-$(date +%s)}"

export SMOKE_QUERY SMOKE_MODE SMOKE_TIMEOUT_SECONDS SMOKE_OUTPUT_JSON SMOKE_REQUEST_ID

case "$SMOKE_MODE" in
  basic|extended|risk) ;;
  *)
    echo "[BL-18.1] Ungültiger SMOKE_MODE='${SMOKE_MODE}' (erlaubt: basic|extended|risk)." >&2
    exit 2
    ;;
esac

BASE_URL="${DEV_BASE_URL%/}"
ANALYZE_URL="${BASE_URL}/analyze"
export ANALYZE_URL

AUTH_HEADER=()
if [[ -n "${DEV_API_AUTH_TOKEN:-}" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer ${DEV_API_AUTH_TOKEN}")
fi

REQUEST_BODY=$(python3 - <<'PY'
import json
import os

payload = {
    "query": os.environ["SMOKE_QUERY"],
    "intelligence_mode": os.environ["SMOKE_MODE"],
    "timeout_seconds": float(os.environ["SMOKE_TIMEOUT_SECONDS"]),
}
print(json.dumps(payload, ensure_ascii=False))
PY
)

TMP_BODY="$(mktemp)"
trap 'rm -f "$TMP_BODY"' EXIT

started_at_utc="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
start_epoch="$(date +%s)"

echo "[BL-18.1] Remote-Smoke-Test gegen: ${ANALYZE_URL}"
set +e
HTTP_CODE=$(curl -sS -m "${CURL_MAX_TIME}" \
  --retry "${CURL_RETRY_COUNT}" \
  --retry-delay "${CURL_RETRY_DELAY}" \
  --retry-connrefused \
  --retry-all-errors \
  -o "$TMP_BODY" -w "%{http_code}" \
  -X POST "${ANALYZE_URL}" \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: ${SMOKE_REQUEST_ID}" \
  "${AUTH_HEADER[@]}" \
  -d "$REQUEST_BODY")
CURL_EXIT=$?
set -e

ended_at_utc="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
end_epoch="$(date +%s)"
duration_seconds="$((end_epoch - start_epoch))"
export started_at_utc ended_at_utc duration_seconds

if [[ "$CURL_EXIT" -ne 0 ]]; then
  echo "[BL-18.1] FAIL: curl-Aufruf fehlgeschlagen (exit=${CURL_EXIT})."
  export CURL_EXIT
  if [[ -s "$TMP_BODY" ]]; then
    head -c 1200 "$TMP_BODY" || true
    echo
  fi

  if [[ -n "$SMOKE_OUTPUT_JSON" ]]; then
    mkdir -p "$(dirname -- "$SMOKE_OUTPUT_JSON")"
    python3 - "$SMOKE_OUTPUT_JSON" <<'PY'
import json
import os
import sys

out_path = sys.argv[1]
report = {
    "status": "fail",
    "reason": "curl_error",
    "curl_exit": int(os.environ["CURL_EXIT"]),
    "http_status": None,
    "request_id": os.environ["SMOKE_REQUEST_ID"],
    "url": os.environ["ANALYZE_URL"],
    "started_at_utc": os.environ["started_at_utc"],
    "ended_at_utc": os.environ["ended_at_utc"],
    "duration_seconds": int(os.environ["duration_seconds"]),
}
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
PY
  fi
  exit 1
fi

python3 - "$HTTP_CODE" "$TMP_BODY" <<'PY'
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
    "request_id": os.environ["SMOKE_REQUEST_ID"],
    "url": os.environ["ANALYZE_URL"],
    "started_at_utc": os.environ["started_at_utc"],
    "ended_at_utc": os.environ["ended_at_utc"],
    "duration_seconds": int(os.environ["duration_seconds"]),
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
            print(
                json.dumps(
                    {
                        "ok": data.get("ok"),
                        "result_keys": sorted(result.keys())[:12],
                        "duration_seconds": report["duration_seconds"],
                        "request_id": report["request_id"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )

smoke_output_json = os.environ.get("SMOKE_OUTPUT_JSON", "").strip()
if smoke_output_json:
    out = pathlib.Path(smoke_output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

if report["status"] != "pass":
    sys.exit(1)
PY
