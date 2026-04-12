#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/smoke/run_gui_live_auth_analyze_route_set.sh [options]

Führt den gemeinsamen GUI-Route-Satz seriell aus und startet mit einem Secrets-Preflight.

Options:
  --base-url <url>        BASE_URL override (z. B. https://www.dev.georanking.ch)
  --ui-base-url <url>     Alias für --base-url
  --output-dir <dir>      Evidence/Blocker-Ausgabeordner (default: reports/evidence)
  --timeout-ms <ms>       Timeout pro UI-Run (default: DEV_UI_SMOKE_TIMEOUT_MS bzw. 60000)
  --address-file <path>   Adressliste für Analyze-Smoke (default: scripts/smoke/ch_live_addresses.txt)
  --login-reason <text>   reason-Parameter für /login (default: manual_login)
  --run-id-base <token>   Basis für DEV_UI_SMOKE_RUN_ID je Route
  --routes <csv>          Komma-separierte Route-Liste (überschreibt GUI_SMOKE_ROUTES)
  --route-presets <csv>   Presets (all,core,modern,legacy,jobs,results,trace,minimal)
                          (Alternative zu --routes)
  --quiet                 Unterdrückt Fortschritts-/Success-Logs auf stdout
  --fallback-login-start-on-preflight-fail
                           Führt bei fehlenden Live-Secrets automatisch
                           den Login-Start-Bundle-Smoke als Fallback aus
                           (degraded mode statt harter Abbruch)
  --headless              Erzwingt headless mode
  --headful               Erzwingt headful mode
  -h, --help              Diese Hilfe anzeigen
EOF
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/smoke/gui_smoke_routes.sh
source "${REPO_ROOT}/scripts/smoke/gui_smoke_routes.sh"
SCRIPT_STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: node command not found" >&2
  exit 2
fi

base_url_override=""
output_dir_override=""
timeout_ms_override=""
address_file_override=""
login_reason_override=""
run_id_base_override=""
routes_override=""
route_presets_override=""
quiet="0"
headful_override=""
fallback_login_start_on_preflight_fail="${DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_PREFLIGHT_FAIL:-${DEV_UI_SMOKE_ALLOW_LOGIN_START_FALLBACK:-0}}"
selected_routes_csv=""
selected_route_presets_csv=""
fallback_bundle_script="${DEV_UI_SMOKE_LOGIN_START_FALLBACK_BUNDLE_SCRIPT:-./scripts/smoke/run_login_start_smoke_bundle.sh}"

declare -a selected_routes=()

resolve_selected_routes() {
  if (( ${#GUI_SMOKE_ROUTES[@]} == 0 )); then
    echo "ERROR: GUI_SMOKE_ROUTES ist leer" >&2
    exit 2
  fi

  if [[ -n "${routes_override}" && -n "${route_presets_override}" ]]; then
    echo "ERROR: --routes und --route-presets dürfen nicht gleichzeitig gesetzt werden" >&2
    usage >&2
    exit 2
  fi

  if [[ -n "${route_presets_override}" ]]; then
    if ! gui_smoke_parse_route_presets_csv "${route_presets_override}"; then
      usage >&2
      exit 2
    fi
    selected_routes=("${GUI_SMOKE_SELECTED_ROUTES[@]}")
    selected_route_presets_csv="$(gui_smoke_selected_presets_csv)"
  elif [[ -n "${routes_override}" ]]; then
    if ! gui_smoke_parse_route_csv "${routes_override}"; then
      usage >&2
      exit 2
    fi
    selected_routes=("${GUI_SMOKE_SELECTED_ROUTES[@]}")
  else
    selected_routes=("${GUI_SMOKE_ROUTES[@]}")
  fi

  if (( ${#selected_routes[@]} == 0 )); then
    echo "ERROR: resolved route list is empty" >&2
    exit 2
  fi

  selected_routes_csv="$(IFS=','; echo "${selected_routes[*]}")"
}

infer_env_name_from_base_url() {
  local base_url="${1:-}"

  if [[ "${base_url}" == *"staging"* ]]; then
    echo "staging"
  else
    echo "dev"
  fi
}

write_route_set_summary() {
  local status="$1"
  local mode="$2"
  local preflight_status="$3"
  local fallback_status="$4"
  local route_rows="$5"
  local failed_routes_csv="$6"
  local fallback_bundle_summary="$7"

  mkdir -p "${summary_output_dir}"

  SUMMARY_STATUS="${status}" \
  SUMMARY_MODE="${mode}" \
  SUMMARY_PREFLIGHT_STATUS="${preflight_status}" \
  SUMMARY_FALLBACK_STATUS="${fallback_status}" \
  SUMMARY_BASE_URL="${summary_base_url}" \
  SUMMARY_ENV_NAME="${summary_env_name}" \
  SUMMARY_RUN_ID_BASE="${base_run_id}" \
  SUMMARY_STARTED_AT="${SCRIPT_STARTED_AT}" \
  SUMMARY_FINISHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  SUMMARY_SELECTED_ROUTES="$(printf '%s\n' "${selected_routes[@]}")" \
  SUMMARY_SELECTED_ROUTE_PRESETS="$(printf '%s\n' "${GUI_SMOKE_SELECTED_PRESETS[@]:-}")" \
  SUMMARY_FALLBACK_ENABLED="${fallback_login_start_on_preflight_fail}" \
  SUMMARY_FAILED_ROUTES_CSV="${failed_routes_csv}" \
  SUMMARY_FALLBACK_BUNDLE_SUMMARY="${fallback_bundle_summary}" \
  SUMMARY_ROUTE_ROWS="${route_rows}" \
  python3 - "${summary_path}" <<'PY'
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _split_lines(name: str) -> list[str]:
    return [line for line in os.environ.get(name, "").splitlines() if line]


def _split_csv(name: str) -> list[str]:
    raw = os.environ.get(name, "")
    if not raw:
        return []
    return [token for token in raw.split(",") if token]


def _parse_route_rows(raw_rows: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in raw_rows.splitlines():
        if not line:
            continue
        route, run_id, rc_raw = line.split("\t", 2)
        rc = int(rc_raw)
        rows.append(
            {
                "route": route,
                "run_id": run_id,
                "status": "passed" if rc == 0 else "failed",
                "rc": rc,
            }
        )
    return rows


summary = {
    "status": os.environ.get("SUMMARY_STATUS", "unknown"),
    "mode": os.environ.get("SUMMARY_MODE", "unknown"),
    "preflight_status": os.environ.get("SUMMARY_PREFLIGHT_STATUS", "unknown"),
    "fallback_status": os.environ.get("SUMMARY_FALLBACK_STATUS", "unknown"),
    "base_url": os.environ.get("SUMMARY_BASE_URL", ""),
    "env_name": os.environ.get("SUMMARY_ENV_NAME", ""),
    "run_id_base": os.environ.get("SUMMARY_RUN_ID_BASE", ""),
    "started_at": os.environ.get("SUMMARY_STARTED_AT", ""),
    "finished_at": os.environ.get("SUMMARY_FINISHED_AT", ""),
    "selected_routes": _split_lines("SUMMARY_SELECTED_ROUTES"),
    "selected_route_presets": _split_lines("SUMMARY_SELECTED_ROUTE_PRESETS"),
    "fallback_login_start_on_preflight_fail": os.environ.get(
        "SUMMARY_FALLBACK_ENABLED", "0"
    )
    == "1",
    "failed_routes": _split_csv("SUMMARY_FAILED_ROUTES_CSV"),
    "fallback_bundle_summary": os.environ.get("SUMMARY_FALLBACK_BUNDLE_SUMMARY", ""),
    "routes": _parse_route_rows(os.environ.get("SUMMARY_ROUTE_ROWS", "")),
}

summary_path = Path(sys.argv[1])
summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url|--ui-base-url)
      require_option_value "$1" "${2:-}"
      base_url_override="$2"
      shift 2
      ;;
    --output-dir)
      require_option_value "--output-dir" "${2:-}"
      output_dir_override="$2"
      shift 2
      ;;
    --timeout-ms)
      require_option_value "--timeout-ms" "${2:-}"
      timeout_ms_override="$2"
      shift 2
      ;;
    --address-file)
      require_option_value "--address-file" "${2:-}"
      address_file_override="$2"
      shift 2
      ;;
    --login-reason)
      require_option_value "--login-reason" "${2:-}"
      login_reason_override="$2"
      shift 2
      ;;
    --run-id-base)
      require_option_value "--run-id-base" "${2:-}"
      run_id_base_override="$2"
      shift 2
      ;;
    --routes)
      require_option_value "--routes" "${2:-}"
      routes_override="$2"
      shift 2
      ;;
    --route-presets)
      require_option_value "--route-presets" "${2:-}"
      route_presets_override="$2"
      shift 2
      ;;
    --fallback-login-start-on-preflight-fail)
      fallback_login_start_on_preflight_fail="1"
      shift
      ;;
    --quiet)
      quiet="1"
      shift
      ;;
    --headless)
      headful_override="0"
      shift
      ;;
    --headful)
      headful_override="1"
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

if [[ -n "${base_url_override}" ]]; then
  export BASE_URL="${base_url_override}"
fi
if [[ -n "${output_dir_override}" ]]; then
  export DEV_UI_SMOKE_EVIDENCE_DIR="${output_dir_override}"
  export DEV_UI_SMOKE_BLOCKER_DIR="${output_dir_override}"
fi
if [[ -n "${timeout_ms_override}" ]]; then
  export DEV_UI_SMOKE_TIMEOUT_MS="${timeout_ms_override}"
fi
if [[ -n "${address_file_override}" ]]; then
  export DEV_UI_SMOKE_ADDRESS_FILE="${address_file_override}"
fi
if [[ -n "${login_reason_override}" ]]; then
  export DEV_UI_SMOKE_LOGIN_REASON="${login_reason_override}"
fi
if [[ -n "${headful_override}" ]]; then
  export DEV_UI_SMOKE_HEADFUL="${headful_override}"
fi

resolve_selected_routes

base_run_id="${run_id_base_override:-${DEV_UI_SMOKE_RUN_ID_BASE:-}}"
if [[ -z "${base_run_id}" ]]; then
  if [[ -n "${GITHUB_RUN_NUMBER:-}" ]]; then
    base_run_id="${GITHUB_RUN_NUMBER}-${GITHUB_RUN_ATTEMPT:-1}"
  elif [[ -n "${GITHUB_RUN_ID:-}" ]]; then
    base_run_id="${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT:-1}"
  else
    base_run_id="manual-$(date -u +%Y%m%dT%H%M%SZ)"
  fi
fi

case "${fallback_login_start_on_preflight_fail,,}" in
  1|true|yes|on)
    fallback_login_start_on_preflight_fail="1"
    ;;
  *)
    fallback_login_start_on_preflight_fail="0"
    ;;
esac

fallback_output_dir="${output_dir_override:-${DEV_UI_SMOKE_EVIDENCE_DIR:-${DEV_UI_SMOKE_BLOCKER_DIR:-reports/evidence}}}"
fallback_login_reason="${login_reason_override:-${DEV_UI_SMOKE_LOGIN_REASON:-manual_login}}"
fallback_timeout_seconds=""
if [[ -n "${DEV_UI_SMOKE_TIMEOUT_MS:-}" && "${DEV_UI_SMOKE_TIMEOUT_MS}" =~ ^[0-9]+$ ]]; then
  fallback_timeout_seconds="$(( (DEV_UI_SMOKE_TIMEOUT_MS + 999) / 1000 ))"
  if (( fallback_timeout_seconds <= 0 )); then
    fallback_timeout_seconds="1"
  fi
fi
summary_output_dir="${fallback_output_dir}"
summary_base_url="${BASE_URL:-https://www.dev.georanking.ch}"
summary_env_name="$(infer_env_name_from_base_url "${summary_base_url}")"
summary_path="${summary_output_dir}/${summary_env_name}-ui-auth-analyze-route-set-summary.json"

declare -a fallback_route_args=()
if [[ -n "${route_presets_override}" ]]; then
  fallback_route_args=(--route-presets "${selected_route_presets_csv}")
elif [[ -n "${routes_override}" ]]; then
  fallback_route_args=(--routes "${selected_routes_csv}")
fi

if ! (
  cd "${REPO_ROOT}"
  DEV_UI_SMOKE_RUN_ID="${base_run_id}" \
    ./scripts/smoke/validate_gui_live_auth_analyze_secrets.sh
); then
  fallback_base_url="${summary_base_url}"
  fallback_env_name="${summary_env_name}"

  if [[ "${fallback_login_start_on_preflight_fail}" == "1" ]]; then
    echo "WARN: live-auth route-set preflight failed; running login-start fallback (degraded mode)." >&2

    fallback_cmd=(
      "${fallback_bundle_script}"
      --base-url "${fallback_base_url}"
      --env-name "${fallback_env_name}"
      --output-dir "${fallback_output_dir}"
      --reason "${fallback_login_reason}"
      "${fallback_route_args[@]}"
    )

    if [[ -n "${fallback_timeout_seconds}" ]]; then
      fallback_cmd+=(--timeout "${fallback_timeout_seconds}")
    fi

    if [[ "${quiet}" == "1" ]]; then
      fallback_cmd+=(--quiet)
    fi

    fallback_effective_cmd="${fallback_bundle_script} --base-url ${fallback_base_url} --env-name ${fallback_env_name} --output-dir ${fallback_output_dir} --reason ${fallback_login_reason}"
    if [[ -n "${route_presets_override}" ]]; then
      fallback_effective_cmd+=" --route-presets \"${selected_route_presets_csv}\""
    elif [[ -n "${routes_override}" ]]; then
      fallback_effective_cmd+=" --routes \"${selected_routes_csv}\""
    fi
    if [[ -n "${fallback_timeout_seconds}" ]]; then
      fallback_effective_cmd+=" --timeout ${fallback_timeout_seconds}"
    fi
    if [[ "${quiet}" == "1" ]]; then
      fallback_effective_cmd+=" --quiet"
    fi
    echo "[gui-live-smoke-preflight] fallback_login_start_smoke=${fallback_effective_cmd}" >&2

    if (
      cd "${REPO_ROOT}"
      "${fallback_cmd[@]}"
    ); then
      write_route_set_summary \
        "passed" \
        "fallback_login_start" \
        "failed" \
        "passed" \
        "" \
        "" \
        "${fallback_output_dir}/${fallback_env_name}-login-start-smoke-bundle-summary.json"
      echo "WARN: login-start fallback passed; live-auth route fan-out skipped." >&2
      exit 0
    else
      fallback_rc="$?"
    fi

    write_route_set_summary \
      "failed" \
      "fallback_login_start" \
      "failed" \
      "failed" \
      "" \
      "" \
      "${fallback_output_dir}/${fallback_env_name}-login-start-smoke-bundle-summary.json"

    echo "ERROR: login-start fallback failed after live-auth preflight failure (exit=${fallback_rc})." >&2
    exit "${fallback_rc}"
  fi

  fallback_login_start_hint="${fallback_bundle_script} --base-url ${fallback_base_url} --env-name ${fallback_env_name}"
  fallback_auto_hint="./scripts/smoke/run_gui_live_auth_analyze_route_set.sh --base-url ${fallback_base_url} --fallback-login-start-on-preflight-fail"
  if [[ -n "${route_presets_override}" ]]; then
    fallback_login_start_hint+=" --route-presets \"${selected_route_presets_csv}\""
    fallback_auto_hint+=" --route-presets \"${selected_route_presets_csv}\""
  elif (( ${#fallback_route_args[@]} > 0 )); then
    fallback_login_start_hint+=" --routes \"${selected_routes_csv}\""
    fallback_auto_hint+=" --routes \"${selected_routes_csv}\""
  fi
  if [[ -n "${fallback_timeout_seconds}" ]]; then
    fallback_login_start_hint+=" --timeout ${fallback_timeout_seconds}"
    fallback_auto_hint+=" --timeout-ms ${DEV_UI_SMOKE_TIMEOUT_MS}"
  fi

  echo "ERROR: live-auth route-set preflight failed; aborting route fan-out." >&2
  echo "HINT: If live credentials are unavailable, run login-start coverage instead:" >&2
  echo "  ${fallback_login_start_hint}" >&2
  echo "HINT: Or opt into automatic fallback for this run:" >&2
  echo "  ${fallback_auto_hint}" >&2
  write_route_set_summary "blocked" "none" "failed" "not_requested" "" "" ""
  exit 1
fi

failures=0
route_summary_rows=""
failed_routes_csv=""
for idx in "${!selected_routes[@]}"; do
  ordinal="$((idx + 1))"
  route="${selected_routes[$idx]}"
  run_id="${base_run_id}-${ordinal}"
  route_rc=0

  if [[ "${quiet}" != "1" ]]; then
    echo "[gui-dev-live-auth-analyze-smoke] route ${ordinal}/${#selected_routes[@]}: ${route} (run_id=${run_id})"
  fi

  if (
    cd "${REPO_ROOT}"
      DEV_UI_SMOKE_GUI_PATH="${route}" \
      DEV_UI_SMOKE_RUN_ID="${run_id}" \
      node scripts/run_dev_ui_auth_analyze_smoke.mjs
  ); then
    if [[ "${quiet}" != "1" ]]; then
      echo "[gui-dev-live-auth-analyze-smoke] PASS ${route}"
    fi
  else
    route_rc="$?"
    failures="$((failures + 1))"
    if [[ -z "${failed_routes_csv}" ]]; then
      failed_routes_csv="${route}"
    else
      failed_routes_csv+=",${route}"
    fi
    echo "[gui-dev-live-auth-analyze-smoke] FAIL ${route}" >&2
  fi

  route_summary_rows+="${route}"$'\t'"${run_id}"$'\t'"${route_rc}"$'\n'
done

if (( failures > 0 )); then
  write_route_set_summary \
    "failed" \
    "live_auth_analyze" \
    "passed" \
    "not_used" \
    "${route_summary_rows}" \
    "${failed_routes_csv}" \
    ""
  echo "ERROR: ${failures} route check(s) failed" >&2
  exit 1
fi

write_route_set_summary \
  "passed" \
  "live_auth_analyze" \
  "passed" \
  "not_used" \
  "${route_summary_rows}" \
  "" \
  ""

if [[ "${quiet}" != "1" ]]; then
  echo "✅ gui-dev-live-auth-analyze-smoke route set passed"
fi
