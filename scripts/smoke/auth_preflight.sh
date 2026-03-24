#!/usr/bin/env bash
set -euo pipefail

AUTH_PREFLIGHT_EXIT_CODE=42

fail_preflight() {
  local message="$1"
  echo "[auth-preflight-failed] ${message}" >&2
  exit "${AUTH_PREFLIGHT_EXIT_CODE}"
}

trim() {
  python3 - "$1" <<'PY'
import sys
print(sys.argv[1].strip())
PY
}

validate_no_control_chars() {
  local value="$1"
  local field_name="$2"
  if ! python3 - "$value" <<'PY'
import sys
value = sys.argv[1]
if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
    raise SystemExit(1)
PY
  then
    fail_preflight "${field_name} darf keine Steuerzeichen enthalten."
  fi
}

validate_no_whitespace() {
  local value="$1"
  local field_name="$2"
  if ! python3 - "$value" <<'PY'
import sys
value = sys.argv[1]
if any(ch.isspace() for ch in value):
    raise SystemExit(1)
PY
  then
    fail_preflight "${field_name} darf keine Whitespaces enthalten."
  fi
}

validate_url() {
  local value="$1"
  local field_name="$2"
  if ! python3 - "$value" <<'PY'
import sys
from urllib.parse import urlsplit

value = sys.argv[1]
parts = urlsplit(value)
if parts.scheme not in {"http", "https"} or not parts.netloc:
    raise SystemExit(1)
PY
  then
    fail_preflight "${field_name} muss eine gültige http(s)-URL sein."
  fi
}

validate_int_ge() {
  local value="$1"
  local field_name="$2"
  local min_value="$3"
  if ! python3 - "$value" "$min_value" <<'PY'
import sys

raw = sys.argv[1]
minimum = int(sys.argv[2])
if not raw.isdigit():
    raise SystemExit(1)
parsed = int(raw)
if parsed < minimum:
    raise SystemExit(1)
PY
  then
    fail_preflight "${field_name} muss ein Integer >= ${min_value} sein."
  fi
}

validate_float_ge() {
  local value="$1"
  local field_name="$2"
  local min_value="$3"
  if ! python3 - "$value" "$min_value" <<'PY'
import math
import sys

parsed = float(sys.argv[1])
minimum = float(sys.argv[2])
if not math.isfinite(parsed) or parsed < minimum:
    raise SystemExit(1)
PY
  then
    fail_preflight "${field_name} muss eine finite Zahl >= ${min_value} sein."
  fi
}

resolve_retry_delay_seconds() {
  local headers_file="$1"
  local default_delay_seconds="$2"
  local max_retry_delay_seconds="$3"

  python3 - "$headers_file" "$default_delay_seconds" "$max_retry_delay_seconds" <<'PY'
from __future__ import annotations

import math
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

headers_file = Path(sys.argv[1])
default_delay = float(sys.argv[2])
max_delay = float(sys.argv[3])

if not math.isfinite(default_delay) or default_delay < 0:
    default_delay = 0.0
if not math.isfinite(max_delay) or max_delay < 0:
    max_delay = 0.0

def cap(value: float) -> float:
    return min(max(0.0, value), max_delay)

fallback = cap(default_delay)
raw = ""
for line in headers_file.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.lower().startswith("retry-after:"):
        raw = line.split(":", 1)[1].strip()
        break

if not raw:
    print(fallback)
    raise SystemExit(0)

try:
    print(cap(float(raw)))
    raise SystemExit(0)
except ValueError:
    pass

try:
    retry_at = parsedate_to_datetime(raw)
except (TypeError, ValueError):
    print(fallback)
    raise SystemExit(0)

if retry_at.tzinfo is None:
    retry_at = retry_at.replace(tzinfo=timezone.utc)

delta = (retry_at - datetime.now(timezone.utc)).total_seconds()
print(cap(delta if delta > 0 else fallback))
PY
}

resolve_output_file() {
  local raw="${SMOKE_AUTH_OUTPUT_FILE:-}"
  local normalized=""

  if [[ -n "${raw}" ]]; then
    normalized="$(trim "${raw}")"
  elif [[ -n "${RUNNER_TEMP:-}" ]]; then
    normalized="$(trim "${RUNNER_TEMP}")/smoke_auth.env"
  else
    normalized="artifacts/smoke_auth.env"
  fi

  normalized="$(trim "${normalized}")"
  if [[ -z "${normalized}" ]]; then
    fail_preflight "SMOKE_AUTH_OUTPUT_FILE ist leer nach Whitespace-Normalisierung."
  fi

  validate_no_control_chars "${normalized}" "SMOKE_AUTH_OUTPUT_FILE"

  if [[ -d "${normalized}" ]]; then
    fail_preflight "SMOKE_AUTH_OUTPUT_FILE darf kein Verzeichnis sein (${normalized})."
  fi

  local parent
  parent="$(dirname -- "${normalized}")"
  if [[ -e "${parent}" && ! -d "${parent}" ]]; then
    fail_preflight "Elternpfad von SMOKE_AUTH_OUTPUT_FILE ist kein Verzeichnis (${parent})."
  fi

  mkdir -p -- "${parent}"
  printf '%s' "${normalized}"
}

write_output_contract() {
  local output_file="$1"
  local auth_mode="$2"
  local token="$3"

  umask 077
  {
    printf 'SMOKE_AUTH_MODE=%s\n' "${auth_mode}"
    printf 'SMOKE_BEARER_TOKEN=%s\n' "${token}"
  } > "${output_file}"

  echo "[auth-preflight] wrote contract: ${output_file}"
  echo "SMOKE_AUTH_OUTPUT_FILE=${output_file}"
}

SMOKE_AUTH_MODE="$(trim "${SMOKE_AUTH_MODE:-}")"
if [[ -z "${SMOKE_AUTH_MODE}" ]]; then
  fail_preflight "SMOKE_AUTH_MODE fehlt (erlaubt: oidc_client_credentials|none)."
fi
SMOKE_AUTH_MODE="${SMOKE_AUTH_MODE,,}"

OUTPUT_FILE="$(resolve_output_file)"

case "${SMOKE_AUTH_MODE}" in
  none)
    write_output_contract "${OUTPUT_FILE}" "none" ""
    exit 0
    ;;
  oidc_client_credentials)
    ;;
  *)
    fail_preflight "Ungültiger SMOKE_AUTH_MODE='${SMOKE_AUTH_MODE}' (erlaubt: oidc_client_credentials|none)."
    ;;
esac

OIDC_TOKEN_URL="$(trim "${OIDC_TOKEN_URL:-}")"
OIDC_CLIENT_ID="$(trim "${OIDC_CLIENT_ID:-}")"
OIDC_CLIENT_SECRET="$(trim "${OIDC_CLIENT_SECRET:-}")"
OIDC_CLIENT_SECRET_FILE="$(trim "${OIDC_CLIENT_SECRET_FILE:-}")"
OIDC_SCOPE="$(trim "${OIDC_SCOPE:-}")"
OIDC_AUDIENCE="$(trim "${OIDC_AUDIENCE:-}")"

OIDC_MAX_ATTEMPTS="$(trim "${OIDC_MAX_ATTEMPTS:-3}")"
OIDC_RETRY_DELAY_SECONDS="$(trim "${OIDC_RETRY_DELAY_SECONDS:-1}")"
OIDC_MAX_RETRY_DELAY_SECONDS="$(trim "${OIDC_MAX_RETRY_DELAY_SECONDS:-10}")"
OIDC_CONNECT_TIMEOUT_SECONDS="$(trim "${OIDC_CONNECT_TIMEOUT_SECONDS:-5}")"
OIDC_MAX_TIME_SECONDS="$(trim "${OIDC_MAX_TIME_SECONDS:-20}")"

validate_int_ge "${OIDC_MAX_ATTEMPTS}" "OIDC_MAX_ATTEMPTS" 1
validate_float_ge "${OIDC_RETRY_DELAY_SECONDS}" "OIDC_RETRY_DELAY_SECONDS" 0
validate_float_ge "${OIDC_MAX_RETRY_DELAY_SECONDS}" "OIDC_MAX_RETRY_DELAY_SECONDS" 0
validate_float_ge "${OIDC_CONNECT_TIMEOUT_SECONDS}" "OIDC_CONNECT_TIMEOUT_SECONDS" 0.001
validate_float_ge "${OIDC_MAX_TIME_SECONDS}" "OIDC_MAX_TIME_SECONDS" 0.001

if [[ -z "${OIDC_TOKEN_URL}" ]]; then
  fail_preflight "OIDC_TOKEN_URL fehlt für SMOKE_AUTH_MODE=oidc_client_credentials."
fi
if [[ -z "${OIDC_CLIENT_ID}" ]]; then
  fail_preflight "OIDC_CLIENT_ID fehlt für SMOKE_AUTH_MODE=oidc_client_credentials."
fi

validate_no_control_chars "${OIDC_TOKEN_URL}" "OIDC_TOKEN_URL"
validate_no_control_chars "${OIDC_CLIENT_ID}" "OIDC_CLIENT_ID"
validate_no_whitespace "${OIDC_CLIENT_ID}" "OIDC_CLIENT_ID"
validate_url "${OIDC_TOKEN_URL}" "OIDC_TOKEN_URL"

if [[ -z "${OIDC_CLIENT_SECRET}" ]]; then
  if [[ -n "${OIDC_CLIENT_SECRET_FILE}" ]]; then
    validate_no_control_chars "${OIDC_CLIENT_SECRET_FILE}" "OIDC_CLIENT_SECRET_FILE"
    if [[ ! -f "${OIDC_CLIENT_SECRET_FILE}" ]]; then
      fail_preflight "OIDC_CLIENT_SECRET_FILE zeigt nicht auf eine existierende Datei (${OIDC_CLIENT_SECRET_FILE})."
    fi
    if [[ ! -r "${OIDC_CLIENT_SECRET_FILE}" ]]; then
      fail_preflight "OIDC_CLIENT_SECRET_FILE ist nicht lesbar (${OIDC_CLIENT_SECRET_FILE})."
    fi
    OIDC_CLIENT_SECRET="$(python3 - "${OIDC_CLIENT_SECRET_FILE}" <<'PY'
import pathlib
import sys
print(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8').strip())
PY
)"
  fi
fi

if [[ -z "${OIDC_CLIENT_SECRET}" ]]; then
  fail_preflight "OIDC_CLIENT_SECRET fehlt (oder OIDC_CLIENT_SECRET_FILE ohne Inhalt) für SMOKE_AUTH_MODE=oidc_client_credentials."
fi

validate_no_control_chars "${OIDC_CLIENT_SECRET}" "OIDC_CLIENT_SECRET"
validate_no_whitespace "${OIDC_CLIENT_SECRET}" "OIDC_CLIENT_SECRET"

if [[ -n "${OIDC_SCOPE}" ]]; then
  validate_no_control_chars "${OIDC_SCOPE}" "OIDC_SCOPE"
fi

if [[ -n "${OIDC_AUDIENCE}" ]]; then
  validate_no_control_chars "${OIDC_AUDIENCE}" "OIDC_AUDIENCE"
fi

TMP_BODY="$(mktemp)"
TMP_HEADERS="$(mktemp)"
trap 'rm -f "${TMP_BODY}" "${TMP_HEADERS}"' EXIT

build_curl_args() {
  local body_file="$1"
  local headers_file="$2"

  CURL_ARGS=(
    -sS
    --connect-timeout "${OIDC_CONNECT_TIMEOUT_SECONDS}"
    --max-time "${OIDC_MAX_TIME_SECONDS}"
    -X POST "${OIDC_TOKEN_URL}"
    -H "Content-Type: application/x-www-form-urlencoded"
    --data-urlencode "grant_type=client_credentials"
    --data-urlencode "client_id=${OIDC_CLIENT_ID}"
    --data-urlencode "client_secret=${OIDC_CLIENT_SECRET}"
    -D "${headers_file}"
    -o "${body_file}"
    -w "%{http_code}"
  )

  if [[ -n "${OIDC_SCOPE}" ]]; then
    CURL_ARGS+=(--data-urlencode "scope=${OIDC_SCOPE}")
  fi

  if [[ -n "${OIDC_AUDIENCE}" ]]; then
    CURL_ARGS+=(--data-urlencode "audience=${OIDC_AUDIENCE}")
  fi
}

HTTP_CODE=""
CURL_EXIT=0
TRANSIENT_STATUS_REGEX='^(408|429|500|502|503|504)$'

for ((attempt=1; attempt<=OIDC_MAX_ATTEMPTS; attempt++)); do
  : > "${TMP_BODY}"
  : > "${TMP_HEADERS}"
  build_curl_args "${TMP_BODY}" "${TMP_HEADERS}"

  set +e
  HTTP_CODE="$(curl "${CURL_ARGS[@]}")"
  CURL_EXIT=$?
  set -e

  if [[ "${CURL_EXIT}" -eq 0 ]]; then
    if ! [[ "${HTTP_CODE}" =~ ^[0-9]{3}$ ]]; then
      fail_preflight "Ungültiger HTTP-Status vom OIDC-Token-Endpoint (${HTTP_CODE})."
    fi

    if [[ "${HTTP_CODE}" -ge 200 && "${HTTP_CODE}" -lt 300 ]]; then
      break
    fi

    if [[ "${HTTP_CODE}" =~ ${TRANSIENT_STATUS_REGEX} && "${attempt}" -lt "${OIDC_MAX_ATTEMPTS}" ]]; then
      sleep "$(resolve_retry_delay_seconds "${TMP_HEADERS}" "${OIDC_RETRY_DELAY_SECONDS}" "${OIDC_MAX_RETRY_DELAY_SECONDS}")"
      continue
    fi

    RESPONSE_PREVIEW="$(head -c 300 "${TMP_BODY}" || true)"
    fail_preflight "OIDC-Token-Endpoint antwortete mit HTTP ${HTTP_CODE}. Body-Preview: ${RESPONSE_PREVIEW}"
  fi

  if [[ "${attempt}" -lt "${OIDC_MAX_ATTEMPTS}" ]]; then
    sleep "${OIDC_RETRY_DELAY_SECONDS}"
    continue
  fi

  fail_preflight "Token-Request zu OIDC_TOKEN_URL fehlgeschlagen (curl exit=${CURL_EXIT})."
done

if [[ "${CURL_EXIT}" -ne 0 ]]; then
  fail_preflight "Token-Request zu OIDC_TOKEN_URL fehlgeschlagen (curl exit=${CURL_EXIT})."
fi

if ! [[ "${HTTP_CODE}" =~ ^[0-9]{3}$ ]]; then
  fail_preflight "Ungültiger HTTP-Status vom OIDC-Token-Endpoint (${HTTP_CODE})."
fi

if [[ "${HTTP_CODE}" -lt 200 || "${HTTP_CODE}" -ge 300 ]]; then
  RESPONSE_PREVIEW="$(head -c 300 "${TMP_BODY}" || true)"
  fail_preflight "OIDC-Token-Endpoint antwortete mit HTTP ${HTTP_CODE}. Body-Preview: ${RESPONSE_PREVIEW}"
fi

SMOKE_BEARER_TOKEN="$(python3 - "${TMP_BODY}" <<'PY'
import json
import pathlib
import sys

raw = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
try:
    payload = json.loads(raw)
except json.JSONDecodeError:
    raise SystemExit(2)

token = payload.get('access_token')
if not isinstance(token, str) or not token.strip():
    raise SystemExit(3)
print(token.strip())
PY
)" || {
  parse_exit=$?
  if [[ "${parse_exit}" -eq 2 ]]; then
    fail_preflight "OIDC-Token-Endpoint lieferte kein valides JSON."
  fi
  fail_preflight "OIDC-Token-Endpoint enthält kein gültiges access_token."
}

validate_no_control_chars "${SMOKE_BEARER_TOKEN}" "SMOKE_BEARER_TOKEN"
validate_no_whitespace "${SMOKE_BEARER_TOKEN}" "SMOKE_BEARER_TOKEN"

write_output_contract "${OUTPUT_FILE}" "oidc_client_credentials" "${SMOKE_BEARER_TOKEN}"
