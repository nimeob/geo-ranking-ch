#!/usr/bin/env bash
set -euo pipefail

BASE_URL=""
ENV_NAME=""
OUTPUT_DIR="artifacts"
SUMMARY_JSON=""
CANONICAL_ORIGIN=""
CANONICAL_HOSTS=""
ALIAS_HOST=""
REASON="manual_login"
TIMEOUT_SECONDS="20"
MAX_ATTEMPTS="8"
RETRY_DELAY_SECONDS="5"
MAX_RETRY_DELAY_SECONDS="10"
ROUTES_CSV=""
ROUTE_PRESETS_CSV=""
QUIET="0"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/smoke/gui_smoke_routes.sh
source "${REPO_ROOT}/scripts/smoke/gui_smoke_routes.sh"
SCRIPT_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

usage() {
  cat <<'EOF'
Usage: scripts/smoke/run_canonical_redirect_smoke_bundle.sh --base-url <url> --env-name <dev|staging> [options]

Options:
  --base-url <url>              Canonical GUI-Base-URL (z. B. https://www.dev.georanking.ch)
  --ui-base-url <url>           Alias für --base-url
  --env-name <name>             Präfix für Artefakte (z. B. dev, staging)
  --output-dir <dir>            Ausgabeordner für JSON-Artefakte (default: artifacts)
  --summary-json <path>         Optionaler Pfad für Bundle-Summary-JSON
                                (default: <output-dir>/<env>-canonical-host-redirect-smoke-bundle-summary.json)
  --json-out <path>             Legacy-Alias für --summary-json
  --canonical-origin <origin>   Optionaler Canonical-Origin Override
  --canonical-hosts <hosts>     Optionale CSV-Liste für UI_CANONICAL_HOSTS
  --alias-host <host>           Optionaler Alias-Host Override
  --reason <reason>             login reason Query-Wert (default: manual_login)
  --timeout <seconds>           Request-Timeout je Probe (default: 20)
  --max-attempts <count>        Retry-Versuche je Route (default: 8)
  --retry-delay <seconds>       Delay zwischen Retries (default: 5)
  --max-retry-delay <seconds>   Cap für Retry-Sleep (default: 10)
  --routes <csv>                Optionale CSV-Route-Subset aus GUI_SMOKE_ROUTES
  --route-presets <csv>         Optionale Presets (all,core,modern,legacy,jobs,results,trace,minimal)
                                (Alternative zu --routes)
  --quiet                       Unterdrückt Fortschritts-/Success-Logs auf stdout
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
    --summary-json|--json-out)
      require_option_value "$1" "${2:-}"
      SUMMARY_JSON="$2"
      shift 2
      ;;
    --canonical-origin)
      require_option_value "--canonical-origin" "${2:-}"
      CANONICAL_ORIGIN="$2"
      shift 2
      ;;
    --canonical-hosts)
      require_option_value "--canonical-hosts" "${2:-}"
      CANONICAL_HOSTS="$2"
      shift 2
      ;;
    --alias-host)
      require_option_value "--alias-host" "${2:-}"
      ALIAS_HOST="$2"
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
    --quiet)
      QUIET="1"
      shift
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
if [[ -n "${SUMMARY_JSON}" ]]; then
  mkdir -p "$(dirname "$SUMMARY_JSON")"
fi

write_bundle_summary() {
  local status="$1"
  local summary_path="$2"
  local finished_at="$3"
  local route_rows="$4"

  SUMMARY_BASE_URL="$BASE_URL" \
  SUMMARY_ENV_NAME="$ENV_NAME" \
  SUMMARY_REASON="$REASON" \
  SUMMARY_CANONICAL_ORIGIN="$CANONICAL_ORIGIN" \
  SUMMARY_CANONICAL_HOSTS="$CANONICAL_HOSTS" \
  SUMMARY_ALIAS_HOST="$ALIAS_HOST" \
  SUMMARY_STATUS="$status" \
  SUMMARY_STARTED_AT="$SCRIPT_STARTED_AT" \
  SUMMARY_FINISHED_AT="$finished_at" \
  SUMMARY_SELECTED_ROUTES="$(printf '%s\n' "${selected_routes[@]}")" \
  SUMMARY_SELECTED_ROUTE_PRESETS="$(printf '%s\n' "${selected_route_presets[@]:-}")" \
  SUMMARY_FAILED_ROUTES="$(printf '%s\n' "${failed_route_paths[@]:-}")" \
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
        route, rc_raw, artifact = line.split("\t", 2)
        rc = int(rc_raw)
        rows.append(
            {
                "route": route,
                "status": "passed" if rc == 0 else "failed",
                "rc": rc,
                "artifact": artifact,
            }
        )
    return rows


summary = {
    "status": os.environ.get("SUMMARY_STATUS", "unknown"),
    "base_url": os.environ.get("SUMMARY_BASE_URL", ""),
    "env_name": os.environ.get("SUMMARY_ENV_NAME", ""),
    "reason": os.environ.get("SUMMARY_REASON", ""),
    "canonical_origin": os.environ.get("SUMMARY_CANONICAL_ORIGIN", ""),
    "canonical_hosts": os.environ.get("SUMMARY_CANONICAL_HOSTS", ""),
    "alias_host": os.environ.get("SUMMARY_ALIAS_HOST", ""),
    "started_at": os.environ.get("SUMMARY_STARTED_AT", ""),
    "finished_at": os.environ.get("SUMMARY_FINISHED_AT", ""),
    "selected_routes": _split_lines("SUMMARY_SELECTED_ROUTES"),
    "selected_route_presets": _split_lines("SUMMARY_SELECTED_ROUTE_PRESETS"),
    "failed_routes": _split_lines("SUMMARY_FAILED_ROUTES"),
    "routes": _parse_route_rows(os.environ.get("SUMMARY_ROUTE_ROWS", "")),
}

summary_path = Path(sys.argv[1])
summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

run_probe() {
  local route="$1"
  local output_json="$2"

  local -a probe_args=(
    "--base-url" "$BASE_URL"
    "--next" "$route"
    "--reason" "$REASON"
    "--timeout" "$TIMEOUT_SECONDS"
    "--max-attempts" "$MAX_ATTEMPTS"
    "--retry-delay" "$RETRY_DELAY_SECONDS"
    "--max-retry-delay" "$MAX_RETRY_DELAY_SECONDS"
    "--output-json" "$output_json"
    "--quiet"
  )

  if [ -n "$CANONICAL_ORIGIN" ]; then
    probe_args+=("--canonical-origin" "$CANONICAL_ORIGIN")
  fi
  if [ -n "$CANONICAL_HOSTS" ]; then
    probe_args+=("--canonical-hosts" "$CANONICAL_HOSTS")
  fi
  if [ -n "$ALIAS_HOST" ]; then
    probe_args+=("--alias-host" "$ALIAS_HOST")
  fi

  python3 scripts/smoke/check_ui_canonical_redirect.py "${probe_args[@]}"
}

log_info() {
  if [[ "${QUIET}" == "1" ]]; then
    return 0
  fi
  echo "$*"
}

read_probe_summary_fields() {
  local output_json="$1"
  python3 - "$output_json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print("\t\t")
    raise SystemExit(0)

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("\t\t")
    raise SystemExit(0)

reason = str(payload.get("reason", ""))
status_code = payload.get("status_code", "")
skipped = payload.get("skipped", "")
print(f"{reason}\t{status_code}\t{skipped}")
PY
}

is_transport_failure_reason() {
  local reason="${1:-}"
  [[ "${reason}" == request_failed_* ]]
}

declare -a failed_routes=()
declare -a failed_route_paths=()

declare -A route_rc=()
declare -A route_artifact=()
fail_fast_triggered="0"
fail_fast_route=""
fail_fast_reason=""
set +e
for route in "${selected_routes[@]}"; do
  suffix="$(gui_canonical_redirect_artifact_suffix_for_route "$route")" || {
    echo "::error::No canonical artifact suffix mapping for route=${route}" >&2
    exit 2
  }

  output_json="${OUTPUT_DIR}/${ENV_NAME}-${suffix}.json"
  run_probe "$route" "$output_json"
  route_rc["$route"]=$?
  route_artifact["$route"]="$output_json"

  probe_reason=""
  probe_status_code=""
  probe_skipped=""
  if [[ -f "$output_json" ]]; then
    IFS=$'\t' read -r probe_reason probe_status_code probe_skipped < <(read_probe_summary_fields "$output_json")
  fi
  log_info "UI canonical redirect smoke: route='${route}' rc=${route_rc["$route"]:-1} reason=${probe_reason:-unknown} status_code=${probe_status_code:-na} skipped=${probe_skipped:-na}"

  probe_skipped_lc="${probe_skipped,,}"
  if [[ "${route_rc["$route"]:-1}" -ne 0 ]] \
    && is_transport_failure_reason "${probe_reason}" \
    && [[ "${probe_skipped_lc}" != "true" ]]; then
    fail_fast_triggered="1"
    fail_fast_route="${route}"
    fail_fast_reason="${probe_reason}"
    echo "::warning::Transport-level probe failure detected (route='${route}', reason='${probe_reason}'). Aborting remaining routes (fail-fast)." >&2
    break
  fi
done
set -e

for route in "${selected_routes[@]}"; do
  rc="${route_rc[$route]:-1}"
  if [ "$rc" -ne 0 ]; then
    failed_routes+=("${route} (rc=${rc})")
    failed_route_paths+=("${route}")
  fi
done

bundle_summary_path="${OUTPUT_DIR}/${ENV_NAME}-canonical-host-redirect-smoke-bundle-summary.json"
if [[ -n "${SUMMARY_JSON}" ]]; then
  bundle_summary_path="${SUMMARY_JSON}"
fi
summary_rows=""
for route in "${selected_routes[@]}"; do
  rc="${route_rc[$route]:-1}"
  artifact_path="${route_artifact[$route]:-}"
  summary_rows+="${route}"$'\t'"${rc}"$'\t'"${artifact_path}"$'\n'
done

bundle_status="passed"
if (( ${#failed_routes[@]} > 0 )); then
  bundle_status="failed"
fi
write_bundle_summary "$bundle_status" "$bundle_summary_path" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$summary_rows"

if (( ${#failed_routes[@]} > 0 )); then
  if [[ "${fail_fast_triggered}" == "1" ]]; then
    echo "::error::UI canonical-host redirect smoke failed (fail-fast after route='${fail_fast_route}', reason='${fail_fast_reason}'). Check BASE_URL/CANONICAL_ORIGIN TLS host validity (tip: prefer canonical www-host). See ${OUTPUT_DIR}/${ENV_NAME}-canonical-host-redirect-smoke*.json and ${bundle_summary_path}"
  else
    echo "::error::UI canonical-host redirect smoke failed for ${#failed_routes[@]} route(s): ${failed_routes[*]}. See ${OUTPUT_DIR}/${ENV_NAME}-canonical-host-redirect-smoke*.json and ${bundle_summary_path}"
  fi
  exit 1
fi

log_info "UI canonical-host redirect smoke bundle passed for env='${ENV_NAME}' (base_url=${BASE_URL}, summary=${bundle_summary_path})"
