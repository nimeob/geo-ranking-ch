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

if [[ -z "${DEV_BASE_URL:-}" ]]; then
  echo "[BL-18.1] DEV_BASE_URL ist nicht gesetzt. Beispiel: DEV_BASE_URL=https://<endpoint> ./scripts/run_remote_api_smoketest.sh" >&2
  exit 2
fi

SMOKE_QUERY="${SMOKE_QUERY:-St. Leonhard-Strasse 40, St. Gallen}"
SMOKE_MODE="${SMOKE_MODE:-basic}"
SMOKE_TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-20}"
CURL_MAX_TIME="${CURL_MAX_TIME:-45}"

BASE_URL="${DEV_BASE_URL%/}"
ANALYZE_URL="${BASE_URL}/analyze"

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

echo "[BL-18.1] Remote-Smoke-Test gegen: ${ANALYZE_URL}"
HTTP_CODE=$(curl -sS -m "${CURL_MAX_TIME}" -o "$TMP_BODY" -w "%{http_code}" \
  -X POST "${ANALYZE_URL}" \
  -H "Content-Type: application/json" \
  "${AUTH_HEADER[@]}" \
  -d "$REQUEST_BODY")

python3 - "$HTTP_CODE" "$TMP_BODY" <<'PY'
import json
import pathlib
import sys

http_code = int(sys.argv[1])
body = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")

try:
    data = json.loads(body)
except json.JSONDecodeError:
    print(f"[BL-18.1] FAIL: Response ist kein valides JSON (HTTP {http_code}).")
    print(body)
    sys.exit(1)

if http_code != 200:
    print(f"[BL-18.1] FAIL: Erwartet HTTP 200, erhalten {http_code}.")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(1)

if data.get("ok") is not True:
    print("[BL-18.1] FAIL: Feld 'ok' ist nicht true.")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(1)

result = data.get("result")
if not isinstance(result, dict) or not result:
    print("[BL-18.1] FAIL: Feld 'result' fehlt oder ist leer.")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(1)

print("[BL-18.1] PASS: HTTP 200, ok=true, result vorhanden.")
print(json.dumps({"ok": data.get("ok"), "result_keys": sorted(result.keys())[:12]}, ensure_ascii=False, indent=2))
PY
