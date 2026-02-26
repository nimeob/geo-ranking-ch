#!/usr/bin/env bash
set -euo pipefail

# Reproduzierbarer Remote-Smoke-Test für Issue BL-18.1
# Erwartet öffentliche Base-URL des Services und prüft POST /analyze auf 200 + ok=true + result-Objekt.
# DEV_BASE_URL darf optional bereits auf /health oder /analyze enden (wird robust normalisiert).
#
# Nutzung:
#   DEV_BASE_URL="https://<endpoint>" ./scripts/run_remote_api_smoketest.sh
#   DEV_BASE_URL="https://<endpoint>/analyze" ./scripts/run_remote_api_smoketest.sh
#   DEV_BASE_URL="https://<endpoint>" DEV_API_AUTH_TOKEN="<token>" ./scripts/run_remote_api_smoketest.sh
#
# Optionale Env-Variablen:
#   SMOKE_QUERY="St. Leonhard-Strasse 40, St. Gallen"
#   SMOKE_MODE="basic"   # basic|extended|risk
#   SMOKE_TIMEOUT_SECONDS="20"
#   CURL_MAX_TIME="45"
#   CURL_RETRY_COUNT="3"
#   CURL_RETRY_DELAY="2"
#   SMOKE_REQUEST_ID="bl18-<id>"  # wird getrimmt; keine Steuerzeichen; max. 128 Zeichen
#   SMOKE_REQUEST_ID_HEADER="request"  # request|correlation (Default: request)
#   SMOKE_ENFORCE_REQUEST_ID_ECHO="1"  # 1|0 (Default: 1)
#   SMOKE_OUTPUT_JSON="artifacts/bl18.1-smoke.json"

if [[ -z "${DEV_BASE_URL:-}" ]]; then
  echo "[BL-18.1] DEV_BASE_URL ist nicht gesetzt. Beispiel: DEV_BASE_URL=https://<endpoint> ./scripts/run_remote_api_smoketest.sh" >&2
  exit 2
fi

DEV_BASE_URL_TRIMMED="$(python3 - "${DEV_BASE_URL}" <<'PY'
import sys
print(sys.argv[1].strip())
PY
)"

if [[ -z "${DEV_BASE_URL_TRIMMED}" ]]; then
  echo "[BL-18.1] DEV_BASE_URL ist leer nach Whitespace-Normalisierung." >&2
  exit 2
fi

if ! python3 - "${DEV_BASE_URL_TRIMMED}" <<'PY'
import sys

value = sys.argv[1]
if any(ch.isspace() for ch in value):
    raise SystemExit(1)
if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
    raise SystemExit(1)
PY
then
  echo "[BL-18.1] DEV_BASE_URL darf keine eingebetteten Whitespaces/Steuerzeichen enthalten (aktuell: ${DEV_BASE_URL})." >&2
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
SMOKE_REQUEST_ID_HEADER="${SMOKE_REQUEST_ID_HEADER:-request}"
SMOKE_ENFORCE_REQUEST_ID_ECHO="${SMOKE_ENFORCE_REQUEST_ID_ECHO:-1}"

SMOKE_REQUEST_ID="$(python3 - "${SMOKE_REQUEST_ID}" <<'PY'
import sys
print(sys.argv[1].strip())
PY
)"

if [[ -z "${SMOKE_REQUEST_ID}" ]]; then
  echo "[BL-18.1] SMOKE_REQUEST_ID ist leer nach Whitespace-Normalisierung." >&2
  exit 2
fi

if ! python3 - "${SMOKE_REQUEST_ID}" <<'PY'
import sys

request_id = sys.argv[1]
if any(ord(ch) < 32 or ord(ch) == 127 for ch in request_id):
    raise SystemExit(1)
PY
then
  echo "[BL-18.1] SMOKE_REQUEST_ID darf keine Steuerzeichen enthalten." >&2
  exit 2
fi

if ! python3 - "${SMOKE_REQUEST_ID}" <<'PY'
import sys

request_id = sys.argv[1]
if len(request_id) > 128:
    raise SystemExit(1)
PY
then
  echo "[BL-18.1] SMOKE_REQUEST_ID darf maximal 128 Zeichen enthalten (aktuell: ${#SMOKE_REQUEST_ID})." >&2
  exit 2
fi

export SMOKE_QUERY SMOKE_MODE SMOKE_TIMEOUT_SECONDS SMOKE_OUTPUT_JSON SMOKE_REQUEST_ID SMOKE_REQUEST_ID_HEADER SMOKE_ENFORCE_REQUEST_ID_ECHO

is_positive_number() {
  python3 - "$1" <<'PY'
import math
import sys

try:
    value = float(sys.argv[1])
except ValueError:
    raise SystemExit(1)

if not math.isfinite(value) or value <= 0:
    raise SystemExit(1)
PY
}

case "$SMOKE_MODE" in
  basic|extended|risk) ;;
  *)
    echo "[BL-18.1] Ungültiger SMOKE_MODE='${SMOKE_MODE}' (erlaubt: basic|extended|risk)." >&2
    exit 2
    ;;
esac

if ! is_positive_number "$SMOKE_TIMEOUT_SECONDS"; then
  echo "[BL-18.1] SMOKE_TIMEOUT_SECONDS muss eine Zahl > 0 sein (aktuell: ${SMOKE_TIMEOUT_SECONDS})." >&2
  exit 2
fi

if ! is_positive_number "$CURL_MAX_TIME"; then
  echo "[BL-18.1] CURL_MAX_TIME muss eine Zahl > 0 sein (aktuell: ${CURL_MAX_TIME})." >&2
  exit 2
fi

if [[ ! "$CURL_RETRY_COUNT" =~ ^[0-9]+$ ]]; then
  echo "[BL-18.1] CURL_RETRY_COUNT muss eine Ganzzahl >= 0 sein (aktuell: ${CURL_RETRY_COUNT})." >&2
  exit 2
fi

if [[ ! "$CURL_RETRY_DELAY" =~ ^[0-9]+$ ]]; then
  echo "[BL-18.1] CURL_RETRY_DELAY muss eine Ganzzahl >= 0 sein (aktuell: ${CURL_RETRY_DELAY})." >&2
  exit 2
fi

SMOKE_REQUEST_ID_HEADER="${SMOKE_REQUEST_ID_HEADER,,}"
case "$SMOKE_REQUEST_ID_HEADER" in
  request|correlation) ;;
  *)
    echo "[BL-18.1] Ungültiger SMOKE_REQUEST_ID_HEADER='${SMOKE_REQUEST_ID_HEADER}' (erlaubt: request|correlation)." >&2
    exit 2
    ;;
esac

case "$SMOKE_ENFORCE_REQUEST_ID_ECHO" in
  0|1) ;;
  *)
    echo "[BL-18.1] Ungültiger SMOKE_ENFORCE_REQUEST_ID_ECHO='${SMOKE_ENFORCE_REQUEST_ID_ECHO}' (erlaubt: 0|1)." >&2
    exit 2
    ;;
esac

strip_trailing_slashes() {
  local value="$1"
  while [[ "$value" == */ ]]; do
    value="${value%/}"
  done
  printf '%s' "$value"
}

RAW_BASE_URL="$(strip_trailing_slashes "${DEV_BASE_URL_TRIMMED}")"
if [[ ! "$RAW_BASE_URL" =~ ^[Hh][Tt][Tt][Pp]([Ss])?:// ]]; then
  echo "[BL-18.1] DEV_BASE_URL muss mit http:// oder https:// beginnen (aktuell: ${DEV_BASE_URL})." >&2
  exit 2
fi

BASE_URL="$RAW_BASE_URL"
while true; do
  base_url_lower="${BASE_URL,,}"
  if [[ "$base_url_lower" == */health ]]; then
    BASE_URL="${BASE_URL:0:${#BASE_URL}-7}"
    BASE_URL="$(strip_trailing_slashes "${BASE_URL}")"
    continue
  fi
  if [[ "$base_url_lower" == */analyze ]]; then
    BASE_URL="${BASE_URL:0:${#BASE_URL}-8}"
    BASE_URL="$(strip_trailing_slashes "${BASE_URL}")"
    continue
  fi
  break
done

if [[ "$BASE_URL" == *"?"* || "$BASE_URL" == *"#"* ]]; then
  echo "[BL-18.1] DEV_BASE_URL darf keine Query- oder Fragment-Komponenten enthalten (aktuell: ${DEV_BASE_URL})." >&2
  exit 2
fi

if ! python3 - "$BASE_URL" <<'PY'
import sys
from urllib.parse import urlsplit

base_url = sys.argv[1]
parts = urlsplit(base_url)
if parts.username is not None or parts.password is not None:
    raise SystemExit(1)
PY
then
  echo "[BL-18.1] DEV_BASE_URL darf keine Userinfo (user:pass@host) enthalten (aktuell: ${DEV_BASE_URL})." >&2
  exit 2
fi

if ! python3 - "$BASE_URL" <<'PY'
import sys
from urllib.parse import urlsplit

base_url = sys.argv[1]
parts = urlsplit(base_url)
if parts.scheme not in {"http", "https"} or not parts.netloc:
    raise SystemExit(1)

try:
    _ = parts.port
except ValueError:
    raise SystemExit(1)

if parts.hostname is None:
    raise SystemExit(1)
PY
then
  echo "[BL-18.1] DEV_BASE_URL ist nach Normalisierung ungültig (aktuell: ${BASE_URL})." >&2
  exit 2
fi

ANALYZE_URL="${BASE_URL}/analyze"
export ANALYZE_URL

AUTH_HEADER=()
if [[ -n "${DEV_API_AUTH_TOKEN:-}" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer ${DEV_API_AUTH_TOKEN}")
fi

REQUEST_ID_HEADERS=()
if [[ "$SMOKE_REQUEST_ID_HEADER" == "correlation" ]]; then
  REQUEST_ID_HEADERS=(-H "X-Correlation-Id: ${SMOKE_REQUEST_ID}")
else
  REQUEST_ID_HEADERS=(-H "X-Request-Id: ${SMOKE_REQUEST_ID}")
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
TMP_HEADERS="$(mktemp)"
trap 'rm -f "$TMP_BODY" "$TMP_HEADERS"' EXIT

started_at_utc="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
start_epoch="$(date +%s)"

echo "[BL-18.1] Remote-Smoke-Test gegen: ${ANALYZE_URL}"
set +e
HTTP_CODE=$(curl -sS -m "${CURL_MAX_TIME}" \
  --retry "${CURL_RETRY_COUNT}" \
  --retry-delay "${CURL_RETRY_DELAY}" \
  --retry-connrefused \
  --retry-all-errors \
  -D "$TMP_HEADERS" \
  -o "$TMP_BODY" -w "%{http_code}" \
  -X POST "${ANALYZE_URL}" \
  -H "Content-Type: application/json" \
  "${REQUEST_ID_HEADERS[@]}" \
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
    "request_id_header_source": os.environ.get("SMOKE_REQUEST_ID_HEADER", "request"),
    "request_id_echo_enforced": os.environ.get("SMOKE_ENFORCE_REQUEST_ID_ECHO", "1") == "1",
    "response_request_id": None,
    "response_header_request_id": None,
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

python3 - "$HTTP_CODE" "$TMP_BODY" "$TMP_HEADERS" <<'PY'
import json
import os
import pathlib
import sys


def _extract_last_headers(raw_text: str) -> dict[str, str]:
    normalized = raw_text.replace("\r\n", "\n")
    blocks = [b for b in normalized.split("\n\n") if b.strip()]
    for block in reversed(blocks):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if not lines[0].startswith("HTTP/"):
            continue
        headers: dict[str, str] = {}
        for line in lines[1:]:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
        return headers
    return {}


http_code = int(sys.argv[1])
body = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
headers_raw = pathlib.Path(sys.argv[3]).read_text(encoding="utf-8", errors="replace")
headers = _extract_last_headers(headers_raw)
response_header_request_id = headers.get("x-request-id")

enforce_request_id_echo = os.environ.get("SMOKE_ENFORCE_REQUEST_ID_ECHO", "1") == "1"
expected_request_id = os.environ["SMOKE_REQUEST_ID"]

report = {
    "status": "fail",
    "reason": None,
    "http_status": http_code,
    "request_id": expected_request_id,
    "request_id_header_source": os.environ.get("SMOKE_REQUEST_ID_HEADER", "request"),
    "request_id_echo_enforced": enforce_request_id_echo,
    "response_request_id": None,
    "response_header_request_id": response_header_request_id,
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
    response_body_request_id = data.get("request_id")
    report["response_request_id"] = response_body_request_id

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
        elif enforce_request_id_echo and response_header_request_id != expected_request_id:
            report["reason"] = "request_id_header_mismatch"
            print(
                "[BL-18.1] FAIL: Response-Header X-Request-Id stimmt nicht mit Request-ID überein."
            )
            print(
                json.dumps(
                    {
                        "expected_request_id": expected_request_id,
                        "response_header_request_id": response_header_request_id,
                        "response_request_id": response_body_request_id,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif enforce_request_id_echo and response_body_request_id != expected_request_id:
            report["reason"] = "request_id_body_mismatch"
            print(
                "[BL-18.1] FAIL: Response-Feld request_id stimmt nicht mit Request-ID überein."
            )
            print(
                json.dumps(
                    {
                        "expected_request_id": expected_request_id,
                        "response_header_request_id": response_header_request_id,
                        "response_request_id": response_body_request_id,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
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
                        "request_id_header_source": report["request_id_header_source"],
                        "response_request_id": report["response_request_id"],
                        "response_header_request_id": report["response_header_request_id"],
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
