#!/usr/bin/env bash
set -euo pipefail

BASE_URL=""
REQUESTED_BASE_URL=""
BASE_URL_CANONICALIZED="0"
ENV_NAME=""
OUTPUT_DIR="artifacts"
REASON="manual_login"
TIMEOUT_SECONDS="20"
MAX_ATTEMPTS="8"
RETRY_DELAY_SECONDS="5"
MAX_RETRY_DELAY_SECONDS="10"
EXPECTED_AUTHORIZE_HOST=""
ROUTES_CSV=""
ROUTE_PRESETS_CSV=""
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/smoke/gui_smoke_routes.sh
source "${REPO_ROOT}/scripts/smoke/gui_smoke_routes.sh"
SCRIPT_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

usage() {
  cat <<'EOF'
Usage: scripts/smoke/run_login_start_smoke_bundle.sh --base-url <url> --env-name <dev|staging> [options]

Options:
  --base-url <url>              Base URL der GUI (z. B. https://www.dev.georanking.ch)
  --ui-base-url <url>           Alias für --base-url
  --env-name <name>             Präfix für Artefakte (z. B. dev, staging)
  --output-dir <dir>            Ausgabeordner für JSON-Artefakte (default: artifacts)
  --reason <reason>             login-start reason (default: manual_login)
  --timeout <seconds>           Request-Timeout je Probe (default: 20)
  --max-attempts <count>        Retry-Versuche je Route (default: 8)
  --retry-delay <seconds>       Delay zwischen Retries (default: 5)
  --max-retry-delay <seconds>   Cap für Retry-Sleep (default: 10)
  --routes <csv>                Optionale CSV-Route-Subset aus GUI_SMOKE_ROUTES
  --route-presets <csv>         Optionale Presets (all,core,modern,legacy,jobs,results,trace,minimal)
                                (Alternative zu --routes)
  --expected-authorize-host <h> Erwarteter Host für absolute authorize-Redirects
                                (hostname, host:port oder URL; optional;
                                 default: auth.<base-host-without-www> + <base-host>
                                 bei www-Origins; ansonsten auth.<base-host> + <base-host>;
                                 localhost/IP-Origins deaktivieren Host-Checks per default)
EOF
}

require_option_value() {
  local option_name="$1"
  local option_value="${2:-}"

  if [ -z "${option_value}" ] || [[ "${option_value}" == --* ]]; then
    echo "::error::Missing value for ${option_name}" >&2
    usage >&2
    exit 2
  fi
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --base-url|--ui-base-url)
      require_option_value "$1" "${2:-}"
      BASE_URL="$2"
      shift 2
      ;;
    --env-name)
      require_option_value "--env-name" "${2:-}"
      ENV_NAME="$2"
      shift 2
      ;;
    --output-dir)
      require_option_value "--output-dir" "${2:-}"
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --reason)
      require_option_value "--reason" "${2:-}"
      REASON="$2"
      shift 2
      ;;
    --timeout)
      require_option_value "--timeout" "${2:-}"
      TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    --max-attempts)
      require_option_value "--max-attempts" "${2:-}"
      MAX_ATTEMPTS="$2"
      shift 2
      ;;
    --retry-delay)
      require_option_value "--retry-delay" "${2:-}"
      RETRY_DELAY_SECONDS="$2"
      shift 2
      ;;
    --max-retry-delay)
      require_option_value "--max-retry-delay" "${2:-}"
      MAX_RETRY_DELAY_SECONDS="$2"
      shift 2
      ;;
    --routes)
      require_option_value "--routes" "${2:-}"
      ROUTES_CSV="$2"
      shift 2
      ;;
    --route-presets)
      require_option_value "--route-presets" "${2:-}"
      ROUTE_PRESETS_CSV="$2"
      shift 2
      ;;
    --expected-authorize-host)
      require_option_value "--expected-authorize-host" "${2:-}"
      EXPECTED_AUTHORIZE_HOST="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$BASE_URL" ]; then
  echo "::error::Missing required --base-url" >&2
  usage >&2
  exit 2
fi

REQUESTED_BASE_URL="$BASE_URL"

canonicalized_base_url_payload="$(python3 - "$BASE_URL" <<'PY'
from __future__ import annotations

import sys
from urllib.parse import urlsplit, urlunsplit


LEGACY_DEV_HOSTS = {"dev.georanking.ch", "dev.geo-ranking.ch"}


def canonicalize_ui_origin(raw_base_url: str) -> tuple[str, bool, list[str]]:
    candidate = str(raw_base_url or "").strip()
    if not candidate:
        return "", False, []

    try:
        parsed = urlsplit(candidate)
    except Exception:
        return candidate, False, []

    if not parsed.scheme or not parsed.netloc:
        return candidate, False, []

    host = str(parsed.hostname or "").strip().lower()
    if not host:
        return candidate, False, []

    reasons: list[str] = []
    canonical_host = host.rstrip(".")
    if canonical_host != host:
        reasons.append("trailing_dot")

    if canonical_host in LEGACY_DEV_HOSTS:
        canonical_host = f"www.{canonical_host}"
        reasons.append("legacy_dev_non_www")

    if not reasons:
        return candidate, False, []

    userinfo = ""
    if parsed.username:
        userinfo = parsed.username
        if parsed.password:
            userinfo += f":{parsed.password}"
        userinfo += "@"

    port_segment = f":{parsed.port}" if parsed.port is not None else ""
    canonical_netloc = f"{userinfo}{canonical_host}{port_segment}"

    canonicalized = urlunsplit(
        (
            parsed.scheme,
            canonical_netloc,
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )
    return canonicalized, True, reasons


canonicalized, changed, reasons = canonicalize_ui_origin(sys.argv[1])
print(f"{canonicalized}\t{1 if changed else 0}\t{','.join(reasons)}")
PY
)"

IFS=$'\t' read -r canonicalized_base_url canonicalized_base_url_flag canonicalized_base_url_reasons <<< "$canonicalized_base_url_payload"
if [[ "$canonicalized_base_url_flag" == "1" ]]; then
  BASE_URL="$canonicalized_base_url"
  BASE_URL_CANONICALIZED="1"
  if [[ "$canonicalized_base_url_reasons" == "legacy_dev_non_www" ]]; then
    echo "::warning::Base URL '${REQUESTED_BASE_URL}' verwendet einen nicht mehr unterstützten DEV-Origin; kanonisiere auf '${BASE_URL}'." >&2
  elif [[ "$canonicalized_base_url_reasons" == "trailing_dot" ]]; then
    echo "::warning::Base URL '${REQUESTED_BASE_URL}' enthält einen Trailing-Dot im Host; kanonisiere auf '${BASE_URL}', um TLS-Hostname-Mismatch zu vermeiden." >&2
  else
    echo "::warning::Base URL '${REQUESTED_BASE_URL}' wurde kanonisiert auf '${BASE_URL}' (reasons=${canonicalized_base_url_reasons})." >&2
  fi
fi

if [ -z "$ENV_NAME" ]; then
  echo "::error::Missing required --env-name" >&2
  usage >&2
  exit 2
fi

if [[ -n "${ROUTES_CSV}" && -n "${ROUTE_PRESETS_CSV}" ]]; then
  echo "::error::--routes und --route-presets dürfen nicht gleichzeitig gesetzt werden" >&2
  usage >&2
  exit 2
fi

if [ -z "$EXPECTED_AUTHORIZE_HOST" ]; then
  EXPECTED_AUTHORIZE_HOST="$(python3 - "$BASE_URL" <<'PY'
from __future__ import annotations

import ipaddress
import sys
from urllib.parse import urlparse


def expand_geo_host_variants(host: str) -> list[str]:
    variants = [host]
    if "geo-ranking" in host:
        variants.append(host.replace("geo-ranking", "georanking"))
    if "georanking" in host:
        variants.append(host.replace("georanking", "geo-ranking"))
    return variants


base_url = sys.argv[1].strip()
parsed = urlparse(base_url)
host = (parsed.hostname or "").strip().lower()
if not host and "://" not in base_url:
    host = (urlparse(f"//{base_url}").hostname or "").strip().lower()
if not host:
    print("")
    raise SystemExit(0)

if host in {"localhost", "localhost.localdomain"}:
    print("")
    raise SystemExit(0)

try:
    ipaddress.ip_address(host)
except ValueError:
    pass
else:
    print("")
    raise SystemExit(0)

seed_hosts = []
if host.startswith("www.") and len(host) > 4:
    bare_host = host[4:]
    # Harden default allow-list: keep canonical UI host + auth host,
    # but do not silently allow the legacy bare host variant.
    seed_hosts.append(f"auth.{bare_host}")
    seed_hosts.append(host)
else:
    seed_hosts.append(f"auth.{host}")
    seed_hosts.append(host)

allow_hosts = []
for seed in seed_hosts:
    allow_hosts.extend(expand_geo_host_variants(seed))

seen = set()
ordered = []
for candidate in allow_hosts:
    if candidate and candidate not in seen:
        ordered.append(candidate)
        seen.add(candidate)

print(",".join(ordered))
PY
)"
fi

if [[ -n "${ROUTE_PRESETS_CSV}" ]]; then
  if ! gui_smoke_parse_route_presets_csv "$ROUTE_PRESETS_CSV"; then
    usage >&2
    exit 2
  fi
elif ! gui_smoke_parse_route_csv "$ROUTES_CSV"; then
  usage >&2
  exit 2
fi

if (( ${#GUI_SMOKE_SELECTED_ROUTES[@]} == 0 )); then
  echo "::error::Resolved route set is empty" >&2
  exit 2
fi

selected_routes=("${GUI_SMOKE_SELECTED_ROUTES[@]}")
selected_route_presets=("${GUI_SMOKE_SELECTED_PRESETS[@]}")

mkdir -p "$OUTPUT_DIR"

write_bundle_summary() {
  local status="$1"
  local summary_path="$2"
  local finished_at="$3"
  local route_rows="$4"

  SUMMARY_BASE_URL="$BASE_URL" \
  SUMMARY_REQUESTED_BASE_URL="$REQUESTED_BASE_URL" \
  SUMMARY_BASE_URL_CANONICALIZED="$BASE_URL_CANONICALIZED" \
  SUMMARY_ENV_NAME="$ENV_NAME" \
  SUMMARY_REASON="$REASON" \
  SUMMARY_EXPECTED_AUTHORIZE_HOST="$EXPECTED_AUTHORIZE_HOST" \
  SUMMARY_STATUS="$status" \
  SUMMARY_STARTED_AT="$SCRIPT_STARTED_AT" \
  SUMMARY_FINISHED_AT="$finished_at" \
  SUMMARY_SELECTED_ROUTES="$(printf '%s\n' "${selected_routes[@]}")" \
  SUMMARY_SELECTED_ROUTE_PRESETS="$(printf '%s\n' "${selected_route_presets[@]:-}")" \
  SUMMARY_FAILED_ROUTES="$(printf '%s\n' "${failed_route_paths[@]:-}")" \
  SUMMARY_SKIPPED_ROUTES="$(printf '%s\n' "${skipped_route_paths[@]:-}")" \
  SUMMARY_ROUTE_ROWS="$route_rows" \
  python3 - "$summary_path" <<'PY'
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _split_lines(name: str) -> list[str]:
    return [line for line in os.environ.get(name, "").splitlines() if line]


def _parse_route_rows(raw_rows: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in raw_rows.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue

        route, rc_raw, artifact = parts[0], parts[1], parts[2]
        phase = parts[3] if len(parts) > 3 else ""
        reason = parts[4] if len(parts) > 4 else ""
        status_code_raw = parts[5] if len(parts) > 5 else ""
        duration_seconds_raw = parts[6] if len(parts) > 6 else ""
        status_override = (parts[7] if len(parts) > 7 else "").strip().lower()

        rc: int | None
        if rc_raw == "":
            rc = None
        else:
            rc = int(rc_raw)

        status_code: int | None
        try:
            status_code = int(status_code_raw)
        except (TypeError, ValueError):
            status_code = None

        duration_seconds: int | None
        try:
            duration_seconds = int(duration_seconds_raw)
        except (TypeError, ValueError):
            duration_seconds = None

        if status_override in {"passed", "failed", "skipped"}:
            row_status = status_override
        elif rc is None:
            row_status = "skipped"
        else:
            row_status = "passed" if rc == 0 else "failed"

        rows.append(
            {
                "route": route,
                "status": row_status,
                "rc": rc,
                "artifact": artifact,
                "phase": phase or None,
                "reason": reason or None,
                "status_code": status_code,
                "duration_seconds": duration_seconds,
            }
        )
    return rows


summary = {
    "status": os.environ.get("SUMMARY_STATUS", "unknown"),
    "base_url": os.environ.get("SUMMARY_BASE_URL", ""),
    "requested_base_url": os.environ.get("SUMMARY_REQUESTED_BASE_URL", ""),
    "base_url_canonicalized": os.environ.get("SUMMARY_BASE_URL_CANONICALIZED", "0") == "1",
    "env_name": os.environ.get("SUMMARY_ENV_NAME", ""),
    "reason": os.environ.get("SUMMARY_REASON", ""),
    "expected_authorize_host": os.environ.get("SUMMARY_EXPECTED_AUTHORIZE_HOST", ""),
    "started_at": os.environ.get("SUMMARY_STARTED_AT", ""),
    "finished_at": os.environ.get("SUMMARY_FINISHED_AT", ""),
    "selected_routes": _split_lines("SUMMARY_SELECTED_ROUTES"),
    "selected_route_presets": _split_lines("SUMMARY_SELECTED_ROUTE_PRESETS"),
    "failed_routes": _split_lines("SUMMARY_FAILED_ROUTES"),
    "skipped_routes": _split_lines("SUMMARY_SKIPPED_ROUTES"),
    "routes": _parse_route_rows(os.environ.get("SUMMARY_ROUTE_ROWS", "")),
}

summary_path = Path(sys.argv[1])
summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

run_probe() {
  local route="$1"
  local output_json="$2"

  python3 scripts/smoke/check_ui_login_start.py \
    --base-url "$BASE_URL" \
    --next "$route" \
    --reason "$REASON" \
    --timeout "$TIMEOUT_SECONDS" \
    --max-attempts "$MAX_ATTEMPTS" \
    --retry-delay "$RETRY_DELAY_SECONDS" \
    --max-retry-delay "$MAX_RETRY_DELAY_SECONDS" \
    --expected-authorize-host "$EXPECTED_AUTHORIZE_HOST" \
    --quiet \
    --output-json "$output_json"
}

read_route_artifact_meta() {
  local artifact_path="$1"

  python3 - "$artifact_path" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path


artifact_path = Path(sys.argv[1])
if not artifact_path.is_file():
    print("unknown\tartifact_missing\t")
    raise SystemExit(0)

try:
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
except Exception:
    print("unknown\tartifact_unreadable\t")
    raise SystemExit(0)

phase = str(payload.get("phase") or "unknown")
reason = str(payload.get("reason") or "unknown")
status_code = payload.get("status_code")

if status_code is None and isinstance(payload.get("entry"), dict):
    status_code = payload.get("entry", {}).get("status_code")

status_code_text = "" if status_code is None else str(status_code)
print(f"{phase}\t{reason}\t{status_code_text}")
PY
}

is_transport_failure_reason() {
  local reason="${1:-}"
  [[ "${reason}" == request_failed_* ]]
}

declare -a failed_routes=()
declare -a failed_route_paths=()
declare -a skipped_route_paths=()

declare -A route_rc=()
declare -A route_artifact=()
declare -A route_phase=()
declare -A route_reason=()
declare -A route_status_code=()
declare -A route_duration_seconds=()
fail_fast_triggered="0"
fail_fast_route=""
fail_fast_reason=""
set +e
for route in "${selected_routes[@]}"; do
  suffix="$(gui_login_start_artifact_suffix_for_route "$route")" || {
    echo "::error::No artifact suffix mapping for route=${route}" >&2
    exit 2
  }

  output_json="${OUTPUT_DIR}/${ENV_NAME}-${suffix}.json"
  route_started_at_epoch="$(date +%s)"
  echo "UI login-start smoke: probing route='${route}' -> ${output_json}"
  run_probe "$route" "$output_json"
  rc=$?
  route_finished_at_epoch="$(date +%s)"
  route_duration="$((route_finished_at_epoch - route_started_at_epoch))"

  route_rc["$route"]=$rc
  route_artifact["$route"]="$output_json"
  route_duration_seconds["$route"]="$route_duration"

  route_meta="$(read_route_artifact_meta "$output_json")"
  IFS=$'\t' read -r route_phase_value route_reason_value route_status_code_value <<< "$route_meta"
  route_phase["$route"]="${route_phase_value:-unknown}"
  route_reason["$route"]="${route_reason_value:-unknown}"
  route_status_code["$route"]="${route_status_code_value:-}"

  echo "UI login-start smoke: route='${route}' rc=${rc} phase=${route_phase["$route"]} reason=${route_reason["$route"]} status_code=${route_status_code["$route"]:-n/a} duration_seconds=${route_duration}"

  if [[ "${rc}" -ne 0 ]] \
    && is_transport_failure_reason "${route_reason["$route"]}"; then
    fail_fast_triggered="1"
    fail_fast_route="${route}"
    fail_fast_reason="${route_reason["$route"]}"
    echo "::warning::Transport-level probe failure detected (route='${route}', reason='${route_reason["$route"]}'). Aborting remaining routes (fail-fast)." >&2
    break
  fi
done
set -e

for route in "${selected_routes[@]}"; do
  if [[ -v "route_rc[$route]" ]]; then
    rc="${route_rc[$route]}"
    if [ "$rc" -ne 0 ]; then
      failed_routes+=("${route} (rc=${rc})")
      failed_route_paths+=("${route}")
    fi
  else
    skipped_route_paths+=("${route}")
  fi
done

bundle_summary_path="${OUTPUT_DIR}/${ENV_NAME}-login-start-smoke-bundle-summary.json"
summary_rows=""
for route in "${selected_routes[@]}"; do
  if [[ -v "route_rc[$route]" ]]; then
    rc="${route_rc[$route]}"
    artifact_path="${route_artifact[$route]:-}"
    phase="${route_phase[$route]:-unknown}"
    reason="${route_reason[$route]:-unknown}"
    status_code="${route_status_code[$route]:-}"
    duration_seconds="${route_duration_seconds[$route]:-0}"
    status_label="failed"
    if [[ "${rc}" -eq 0 ]]; then
      status_label="passed"
    fi
  else
    rc=""
    artifact_path=""
    phase="skipped"
    reason="fail_fast_skipped"
    status_code=""
    duration_seconds=""
    status_label="skipped"
  fi
  summary_rows+="${route}"$'\t'"${rc}"$'\t'"${artifact_path}"$'\t'"${phase}"$'\t'"${reason}"$'\t'"${status_code}"$'\t'"${duration_seconds}"$'\t'"${status_label}"$'\n'
done

bundle_status="passed"
if (( ${#failed_routes[@]} > 0 )); then
  bundle_status="failed"
fi
write_bundle_summary "$bundle_status" "$bundle_summary_path" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$summary_rows"

if (( ${#failed_routes[@]} > 0 )); then
  if [[ "${fail_fast_triggered}" == "1" ]]; then
    echo "::error::UI login-start smoke failed (fail-fast after route='${fail_fast_route}', reason='${fail_fast_reason}'). Check BASE_URL / expected auth host / TLS reachability before retrying full route matrix. See ${OUTPUT_DIR}/${ENV_NAME}-login-start-smoke*.json and ${bundle_summary_path}"
  else
    echo "::error::UI login-start smoke failed for ${#failed_routes[@]} route(s): ${failed_routes[*]}. See ${OUTPUT_DIR}/${ENV_NAME}-login-start-smoke*.json and ${bundle_summary_path}"
  fi
  exit 1
fi

echo "UI login-start smoke bundle passed for env='${ENV_NAME}' (base_url=${BASE_URL}, expected_authorize_host=${EXPECTED_AUTHORIZE_HOST}, summary=${bundle_summary_path})"
