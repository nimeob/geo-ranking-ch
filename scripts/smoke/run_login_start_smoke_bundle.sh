#!/usr/bin/env bash
set -euo pipefail

BASE_URL=""
ENV_NAME=""
OUTPUT_DIR="artifacts"
REASON="manual_login"
TIMEOUT_SECONDS="20"
MAX_ATTEMPTS="8"
RETRY_DELAY_SECONDS="5"
EXPECTED_AUTHORIZE_HOST=""
ROUTES_CSV=""
ROUTE_PRESETS_CSV=""
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/smoke/gui_smoke_routes.sh
source "${REPO_ROOT}/scripts/smoke/gui_smoke_routes.sh"

usage() {
  cat <<'EOF'
Usage: scripts/smoke/run_login_start_smoke_bundle.sh --base-url <url> --env-name <dev|staging> [options]

Options:
  --base-url <url>              Base URL der GUI (z. B. https://www.dev.georanking.ch)
  --env-name <name>             Präfix für Artefakte (z. B. dev, staging)
  --output-dir <dir>            Ausgabeordner für JSON-Artefakte (default: artifacts)
  --reason <reason>             login-start reason (default: manual_login)
  --timeout <seconds>           Request-Timeout je Probe (default: 20)
  --max-attempts <count>        Retry-Versuche je Route (default: 8)
  --retry-delay <seconds>       Delay zwischen Retries (default: 5)
  --routes <csv>                Optionale CSV-Route-Subset aus GUI_SMOKE_ROUTES
  --route-presets <csv>         Optionale Presets (all,core,modern,legacy,jobs,results,trace,minimal)
                                (Alternative zu --routes)
  --expected-authorize-host <h> Erwarteter Host für absolute authorize-Redirects
                                (hostname, host:port oder URL; optional;
                                 default: auth.<base-host> + <base-host>)
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
from urllib.parse import urlparse
import sys


def expand_geo_host_variants(host: str) -> list[str]:
    variants = [host]
    if "geo-ranking" in host:
        variants.append(host.replace("geo-ranking", "georanking"))
    return variants


base_url = sys.argv[1].strip()
host = (urlparse(base_url).hostname or "").strip().lower()
if not host:
    raise SystemExit("")

seed_hosts = []
if host.startswith("www.") and len(host) > 4:
    bare_host = host[4:]
    seed_hosts.append(f"auth.{bare_host}")
    seed_hosts.append(host)
    seed_hosts.append(bare_host)
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

mkdir -p "$OUTPUT_DIR"

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
    --expected-authorize-host "$EXPECTED_AUTHORIZE_HOST" \
    --output-json "$output_json"
}

declare -a failed_routes=()

declare -A route_rc=()
set +e
for route in "${selected_routes[@]}"; do
  suffix="$(gui_login_start_artifact_suffix_for_route "$route")" || {
    echo "::error::No artifact suffix mapping for route=${route}" >&2
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
  echo "::error::UI login-start smoke failed for ${#failed_routes[@]} route(s): ${failed_routes[*]}. See ${OUTPUT_DIR}/${ENV_NAME}-login-start-smoke*.json"
  exit 1
fi

echo "UI login-start smoke bundle passed for env='${ENV_NAME}' (base_url=${BASE_URL}, expected_authorize_host=${EXPECTED_AUTHORIZE_HOST})"
