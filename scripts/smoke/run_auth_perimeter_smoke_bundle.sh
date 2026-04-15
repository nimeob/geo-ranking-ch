#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/smoke/run_auth_perimeter_smoke_bundle.sh --base-url <url> [options]

Runs the auth perimeter smoke bundle (UI login-start + canonical redirect + BFF auth-proxy guard).

Options:
  --base-url <url>              Canonical UI base URL (e.g. https://www.dev.georanking.ch)
  --ui-base-url <url>           Alias for --base-url
  --api-base-url <url>          Optional API base URL override for BFF guard
  --env-name <name>             Artifact prefix (default inferred from --base-url: dev|staging)
  --output-dir <dir>            Artifact directory (default: reports/evidence; relative paths resolved from repo root)
  --summary-json <path>         Optional summary JSON output path
                                (default: <output-dir>/<env>-auth-perimeter-smoke-bundle-summary.json)
  --json-out <path>             Legacy alias for --summary-json
  --reason <reason>             Login reason query param (default: manual_login)
  --timeout <seconds>           Timeout per request (default: 20)
  --max-attempts <count>        Retry attempts per route/check (default: 8)
  --retry-delay <seconds>       Retry delay (default: 5)
  --max-retry-delay <seconds>   Retry delay cap (default: 10)
  --routes <csv>                Optional route subset (forwarded to login/canonical bundles)
  --route-presets <csv>         Optional route presets (all,core,modern,legacy,jobs,results,trace,minimal)
  --canonical-origin <origin>   Optional canonical origin override for canonical-redirect smoke
  --canonical-hosts <hosts>     Optional CSV canonical host list for canonical-redirect smoke
  --alias-host <host>           Optional alias host override for canonical-redirect smoke
  --preserve-requested-base-url Keep requested origin for login-start bundle (no canonicalization)
  --expected-authorize-host <h> Optional authorize host allow-list (forwarded to login + BFF guards)
  --bff-output-json <path>      Optional output path for BFF guard JSON
                                (default: <output-dir>/<env>-auth-proxy-guard-smoke.json)
  --quiet                       Suppress progress logs on stdout
  -h, --help                    Show this help and exit
EOF
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

LOGIN_START_BUNDLE_SCRIPT="${AUTH_PERIMETER_LOGIN_START_BUNDLE_SCRIPT:-./scripts/smoke/run_login_start_smoke_bundle.sh}"
CANONICAL_BUNDLE_SCRIPT="${AUTH_PERIMETER_CANONICAL_BUNDLE_SCRIPT:-./scripts/smoke/run_canonical_redirect_smoke_bundle.sh}"
BFF_GUARD_SCRIPT="${AUTH_PERIMETER_BFF_GUARD_SCRIPT:-./scripts/smoke/check_bff_auth_proxy_guard.py}"

resolve_path_against_repo_root() {
  local raw_path="${1:-}"

  if [[ -z "${raw_path}" ]]; then
    echo ""
    return 0
  fi

  if [[ "${raw_path}" == "~/"* ]]; then
    raw_path="${HOME}/${raw_path#~/}"
  fi

  if [[ "${raw_path}" == /* ]]; then
    echo "${raw_path}"
  else
    echo "${REPO_ROOT}/${raw_path}"
  fi
}

resolve_command_path() {
  local raw_path="${1:-}"

  if [[ -z "${raw_path}" ]]; then
    echo ""
    return 0
  fi

  if [[ "${raw_path}" == /* ]]; then
    echo "${raw_path}"
  else
    echo "${REPO_ROOT}/${raw_path}"
  fi
}

require_option_value() {
  local option_name="$1"
  local option_value="${2:-}"

  if [[ -z "${option_value}" || "${option_value}" == --* ]]; then
    echo "ERROR: Missing value for ${option_name}" >&2
    usage >&2
    exit 2
  fi
}

infer_env_name_from_base_url() {
  local base_url="${1:-}"

  if [[ "${base_url}" == *"staging"* ]]; then
    echo "staging"
  else
    echo "dev"
  fi
}

base_url=""
api_base_url=""
env_name=""
output_dir="${REPO_ROOT}/reports/evidence"
summary_json_override=""
reason="manual_login"
timeout="20"
max_attempts="8"
retry_delay="5"
max_retry_delay="10"
routes_csv=""
route_presets_csv=""
canonical_origin=""
canonical_hosts=""
alias_host=""
preserve_requested_base_url="0"
expected_authorize_host=""
bff_output_json_override=""
quiet="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url|--ui-base-url)
      require_option_value "$1" "${2:-}"
      base_url="$2"
      shift 2
      ;;
    --api-base-url)
      require_option_value "--api-base-url" "${2:-}"
      api_base_url="$2"
      shift 2
      ;;
    --env-name)
      require_option_value "--env-name" "${2:-}"
      env_name="$2"
      shift 2
      ;;
    --output-dir)
      require_option_value "--output-dir" "${2:-}"
      output_dir="$(resolve_path_against_repo_root "$2")"
      shift 2
      ;;
    --summary-json|--json-out)
      require_option_value "$1" "${2:-}"
      summary_json_override="$(resolve_path_against_repo_root "$2")"
      shift 2
      ;;
    --reason)
      require_option_value "--reason" "${2:-}"
      reason="$2"
      shift 2
      ;;
    --timeout)
      require_option_value "--timeout" "${2:-}"
      timeout="$2"
      shift 2
      ;;
    --max-attempts)
      require_option_value "--max-attempts" "${2:-}"
      max_attempts="$2"
      shift 2
      ;;
    --retry-delay)
      require_option_value "--retry-delay" "${2:-}"
      retry_delay="$2"
      shift 2
      ;;
    --max-retry-delay)
      require_option_value "--max-retry-delay" "${2:-}"
      max_retry_delay="$2"
      shift 2
      ;;
    --routes)
      require_option_value "--routes" "${2:-}"
      routes_csv="$2"
      shift 2
      ;;
    --route-presets)
      require_option_value "--route-presets" "${2:-}"
      route_presets_csv="$2"
      shift 2
      ;;
    --canonical-origin)
      require_option_value "--canonical-origin" "${2:-}"
      canonical_origin="$2"
      shift 2
      ;;
    --canonical-hosts)
      require_option_value "--canonical-hosts" "${2:-}"
      canonical_hosts="$2"
      shift 2
      ;;
    --alias-host)
      require_option_value "--alias-host" "${2:-}"
      alias_host="$2"
      shift 2
      ;;
    --preserve-requested-base-url)
      preserve_requested_base_url="1"
      shift
      ;;
    --expected-authorize-host)
      require_option_value "--expected-authorize-host" "${2:-}"
      expected_authorize_host="$2"
      shift 2
      ;;
    --bff-output-json)
      require_option_value "--bff-output-json" "${2:-}"
      bff_output_json_override="$(resolve_path_against_repo_root "$2")"
      shift 2
      ;;
    --quiet)
      quiet="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${base_url}" ]]; then
  echo "ERROR: Missing required --base-url" >&2
  usage >&2
  exit 2
fi

if [[ -z "${env_name}" ]]; then
  env_name="$(infer_env_name_from_base_url "${base_url}")"
fi

summary_path="${summary_json_override:-${output_dir}/${env_name}-auth-perimeter-smoke-bundle-summary.json}"
mkdir -p "${output_dir}" "$(dirname "${summary_path}")"

login_summary_path="${output_dir}/${env_name}-login-start-smoke-bundle-summary.json"
canonical_summary_path="${output_dir}/${env_name}-canonical-host-redirect-smoke-bundle-summary.json"
bff_summary_path="${bff_output_json_override:-${output_dir}/${env_name}-auth-proxy-guard-smoke.json}"

LOGIN_START_BUNDLE_SCRIPT="$(resolve_command_path "${LOGIN_START_BUNDLE_SCRIPT}")"
CANONICAL_BUNDLE_SCRIPT="$(resolve_command_path "${CANONICAL_BUNDLE_SCRIPT}")"
BFF_GUARD_SCRIPT="$(resolve_command_path "${BFF_GUARD_SCRIPT}")"

for required_cmd in "${LOGIN_START_BUNDLE_SCRIPT}" "${CANONICAL_BUNDLE_SCRIPT}" "${BFF_GUARD_SCRIPT}"; do
  if [[ ! -x "${required_cmd}" ]]; then
    echo "ERROR: required executable not found: ${required_cmd}" >&2
    exit 2
  fi
done

if [[ -n "${routes_csv}" && -n "${route_presets_csv}" ]]; then
  echo "ERROR: --routes und --route-presets dürfen nicht gleichzeitig gesetzt werden" >&2
  usage >&2
  exit 2
fi

declare -a common_bundle_args=(
  --base-url "${base_url}"
  --env-name "${env_name}"
  --output-dir "${output_dir}"
  --reason "${reason}"
  --timeout "${timeout}"
  --max-attempts "${max_attempts}"
  --retry-delay "${retry_delay}"
  --max-retry-delay "${max_retry_delay}"
)

if [[ -n "${routes_csv}" ]]; then
  common_bundle_args+=(--routes "${routes_csv}")
elif [[ -n "${route_presets_csv}" ]]; then
  common_bundle_args+=(--route-presets "${route_presets_csv}")
fi

if [[ "${quiet}" == "1" ]]; then
  common_bundle_args+=(--quiet)
fi

declare -a login_args=("${common_bundle_args[@]}" --summary-json "${login_summary_path}")
if [[ "${preserve_requested_base_url}" == "1" ]]; then
  login_args+=(--preserve-requested-base-url)
fi
if [[ -n "${expected_authorize_host}" ]]; then
  login_args+=(--expected-authorize-host "${expected_authorize_host}")
fi

declare -a canonical_args=("${common_bundle_args[@]}" --summary-json "${canonical_summary_path}")
if [[ -n "${canonical_origin}" ]]; then
  canonical_args+=(--canonical-origin "${canonical_origin}")
fi
if [[ -n "${canonical_hosts}" ]]; then
  canonical_args+=(--canonical-hosts "${canonical_hosts}")
fi
if [[ -n "${alias_host}" ]]; then
  canonical_args+=(--alias-host "${alias_host}")
fi

declare -a bff_args=(
  --ui-base-url "${base_url}"
  --timeout "${timeout}"
  --max-attempts "${max_attempts}"
  --retry-delay "${retry_delay}"
  --max-retry-delay "${max_retry_delay}"
  --output-json "${bff_summary_path}"
)
if [[ -n "${api_base_url}" ]]; then
  bff_args+=(--api-base-url "${api_base_url}")
fi
if [[ -n "${expected_authorize_host}" ]]; then
  bff_args+=(--expected-authorize-host "${expected_authorize_host}")
fi

overall_rc=0
rows=""

run_step() {
  local step_name="$1"
  local output_path="$2"
  shift 2

  local rc=0
  if [[ "${quiet}" != "1" ]]; then
    echo "[auth-perimeter] ${step_name}: start"
  fi

  set +e
  (
    cd "${REPO_ROOT}"
    "$@"
  )
  rc=$?
  set -e

  if (( rc != 0 )); then
    overall_rc=1
  fi

  local step_status="passed"
  if (( rc != 0 )); then
    step_status="failed"
  fi

  rows+="${step_name}"$'\t'"${step_status}"$'\t'"${rc}"$'\t'"${output_path}"$'\n'

  if [[ "${quiet}" != "1" ]]; then
    if (( rc == 0 )); then
      echo "[auth-perimeter] ${step_name}: PASS"
    else
      echo "[auth-perimeter] ${step_name}: FAIL (exit ${rc})" >&2
    fi
  fi
}

run_step "login_start_bundle" "${login_summary_path}" "${LOGIN_START_BUNDLE_SCRIPT}" "${login_args[@]}"
run_step "canonical_redirect_bundle" "${canonical_summary_path}" "${CANONICAL_BUNDLE_SCRIPT}" "${canonical_args[@]}"
run_step "bff_auth_proxy_guard" "${bff_summary_path}" "${BFF_GUARD_SCRIPT}" "${bff_args[@]}"

overall_status="passed"
if (( overall_rc != 0 )); then
  overall_status="failed"
fi

SUMMARY_PATH="${summary_path}" \
SUMMARY_STATUS="${overall_status}" \
SUMMARY_BASE_URL="${base_url}" \
SUMMARY_API_BASE_URL="${api_base_url}" \
SUMMARY_ENV_NAME="${env_name}" \
SUMMARY_OUTPUT_DIR="${output_dir}" \
SUMMARY_REASON="${reason}" \
SUMMARY_TIMEOUT="${timeout}" \
SUMMARY_MAX_ATTEMPTS="${max_attempts}" \
SUMMARY_RETRY_DELAY="${retry_delay}" \
SUMMARY_MAX_RETRY_DELAY="${max_retry_delay}" \
SUMMARY_ROUTES_CSV="${routes_csv}" \
SUMMARY_ROUTE_PRESETS_CSV="${route_presets_csv}" \
SUMMARY_CANONICAL_ORIGIN="${canonical_origin}" \
SUMMARY_CANONICAL_HOSTS="${canonical_hosts}" \
SUMMARY_ALIAS_HOST="${alias_host}" \
SUMMARY_PRESERVE_REQUESTED_BASE_URL="${preserve_requested_base_url}" \
SUMMARY_EXPECTED_AUTHORIZE_HOST="${expected_authorize_host}" \
SUMMARY_BFF_OUTPUT_JSON="${bff_summary_path}" \
SUMMARY_STARTED_AT="${SCRIPT_STARTED_AT}" \
SUMMARY_FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
SUMMARY_STEP_ROWS="${rows}" \
python3 - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path


def _load_status(path: str) -> str:
    target = Path(path)
    if not target.is_file():
        return "missing"

    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return "invalid_json"

    status = payload.get("status")
    if isinstance(status, str) and status.strip():
        return status.strip()
    if payload.get("ok") is True:
        return "passed"
    if payload.get("ok") is False:
        return "failed"
    return "unknown"


rows = []
for line in os.environ.get("SUMMARY_STEP_ROWS", "").splitlines():
    if not line:
        continue
    step_name, status, rc_raw, output_path = line.split("\t", 3)
    rc = int(rc_raw)
    rows.append(
        {
            "name": step_name,
            "status": status,
            "rc": rc,
            "output_json": output_path,
            "reported_status": _load_status(output_path),
        }
    )

summary = {
    "status": os.environ.get("SUMMARY_STATUS", "unknown"),
    "base_url": os.environ.get("SUMMARY_BASE_URL", ""),
    "api_base_url": os.environ.get("SUMMARY_API_BASE_URL", ""),
    "env_name": os.environ.get("SUMMARY_ENV_NAME", ""),
    "output_dir": os.environ.get("SUMMARY_OUTPUT_DIR", ""),
    "reason": os.environ.get("SUMMARY_REASON", "manual_login"),
    "timeout": os.environ.get("SUMMARY_TIMEOUT", ""),
    "max_attempts": os.environ.get("SUMMARY_MAX_ATTEMPTS", ""),
    "retry_delay": os.environ.get("SUMMARY_RETRY_DELAY", ""),
    "max_retry_delay": os.environ.get("SUMMARY_MAX_RETRY_DELAY", ""),
    "routes_csv": os.environ.get("SUMMARY_ROUTES_CSV", ""),
    "route_presets_csv": os.environ.get("SUMMARY_ROUTE_PRESETS_CSV", ""),
    "canonical_origin": os.environ.get("SUMMARY_CANONICAL_ORIGIN", ""),
    "canonical_hosts": os.environ.get("SUMMARY_CANONICAL_HOSTS", ""),
    "alias_host": os.environ.get("SUMMARY_ALIAS_HOST", ""),
    "preserve_requested_base_url": os.environ.get("SUMMARY_PRESERVE_REQUESTED_BASE_URL", "0") == "1",
    "expected_authorize_host": os.environ.get("SUMMARY_EXPECTED_AUTHORIZE_HOST", ""),
    "bff_output_json": os.environ.get("SUMMARY_BFF_OUTPUT_JSON", ""),
    "started_at": os.environ.get("SUMMARY_STARTED_AT", ""),
    "finished_at": os.environ.get("SUMMARY_FINISHED_AT", ""),
    "steps": rows,
}

summary_path = Path(os.environ["SUMMARY_PATH"])
summary_path.parent.mkdir(parents=True, exist_ok=True)
summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

if [[ "${quiet}" != "1" ]]; then
  echo "[auth-perimeter] summary: ${summary_path}"
fi

if (( overall_rc != 0 )); then
  exit 1
fi

exit 0
