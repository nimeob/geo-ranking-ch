#!/usr/bin/env bash
set -euo pipefail

BASE_URL=""
ENV_NAME=""
OUTPUT_DIR="artifacts"
CANONICAL_ORIGIN=""
CANONICAL_HOSTS=""
ALIAS_HOST=""
REASON="manual_login"
TIMEOUT_SECONDS="20"
MAX_ATTEMPTS="8"
RETRY_DELAY_SECONDS="5"
MAX_RETRY_DELAY_SECONDS="10"
ROUTES_CSV=""
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/smoke/gui_smoke_routes.sh
source "${REPO_ROOT}/scripts/smoke/gui_smoke_routes.sh"

usage() {
  cat <<'EOF'
Usage: scripts/smoke/run_canonical_redirect_smoke_bundle.sh --base-url <url> --env-name <dev|staging> [options]

Options:
  --base-url <url>              Canonical GUI-Base-URL (z. B. https://www.dev.georanking.ch)
  --env-name <name>             Präfix für Artefakte (z. B. dev, staging)
  --output-dir <dir>            Ausgabeordner für JSON-Artefakte (default: artifacts)
  --canonical-origin <origin>   Optionaler Canonical-Origin Override
  --canonical-hosts <hosts>     Optionale CSV-Liste für UI_CANONICAL_HOSTS
  --alias-host <host>           Optionaler Alias-Host Override
  --reason <reason>             login reason Query-Wert (default: manual_login)
  --timeout <seconds>           Request-Timeout je Probe (default: 20)
  --max-attempts <count>        Retry-Versuche je Route (default: 8)
  --retry-delay <seconds>       Delay zwischen Retries (default: 5)
  --max-retry-delay <seconds>   Cap für Retry-Sleep (default: 10)
  --routes <csv>                Optionale CSV-Route-Subset aus GUI_SMOKE_ROUTES
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
    --base-url)
      require_option_value "--base-url" "${2:-}"
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

if ! gui_smoke_parse_route_csv "$ROUTES_CSV"; then
  usage >&2
  exit 2
fi

if (( ${#GUI_SMOKE_SELECTED_ROUTES[@]} == 0 )); then
  echo "::error::Resolved route set is empty" >&2
  exit 2
fi

selected_routes=("${GUI_SMOKE_SELECTED_ROUTES[@]}")

mkdir -p "$OUTPUT_DIR"

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

declare -a failed_routes=()

declare -A route_rc=()
set +e
for route in "${selected_routes[@]}"; do
  suffix="$(gui_canonical_redirect_artifact_suffix_for_route "$route")" || {
    echo "::error::No canonical artifact suffix mapping for route=${route}" >&2
    exit 2
  }

  output_json="${OUTPUT_DIR}/${ENV_NAME}-${suffix}.json"
  run_probe "$route" "$output_json"
  route_rc["$route"]=$?
done
set -e

for route in "${selected_routes[@]}"; do
  rc="${route_rc[$route]:-1}"
  if [ "$rc" -ne 0 ]; then
    failed_routes+=("${route} (rc=${rc})")
  fi
done

if (( ${#failed_routes[@]} > 0 )); then
  echo "::error::UI canonical-host redirect smoke failed for ${#failed_routes[@]} route(s): ${failed_routes[*]}. See ${OUTPUT_DIR}/${ENV_NAME}-canonical-host-redirect-smoke*.json"
  exit 1
fi

echo "UI canonical-host redirect smoke bundle passed for env='${ENV_NAME}' (base_url=${BASE_URL})"
