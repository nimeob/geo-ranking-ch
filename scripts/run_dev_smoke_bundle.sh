#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage: scripts/run_dev_smoke_bundle.sh [options]

Runs the local dev smoke bundle (lint + typecheck + BL-334 split smokes).

Options:
  --skip-lint        Skip pre-commit lint step
  --skip-typecheck   Skip compileall typecheck step
  --skip-smoke       Skip BL-334 split smoke step
  --only <csv>       Run only selected steps (lint,typecheck,smoke)
  -h, --help         Show this help and exit
EOF
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

parse_only_steps_csv() {
  local csv_raw="$1"

  RUN_LINT=0
  RUN_TYPECHECK=0
  RUN_SMOKE=0

  IFS=',' read -r -a only_tokens <<<"${csv_raw}"
  for raw_token in "${only_tokens[@]}"; do
    local token
    token="$(echo "${raw_token}" | xargs)"
    if [[ -z "${token}" ]]; then
      continue
    fi

    case "${token}" in
      lint)
        RUN_LINT=1
        ;;
      typecheck)
        RUN_TYPECHECK=1
        ;;
      smoke)
        RUN_SMOKE=1
        ;;
      *)
        echo "ERROR: Unsupported step in --only: ${token}" >&2
        echo "HINT: supported values are lint,typecheck,smoke" >&2
        usage >&2
        exit 2
        ;;
    esac
  done
}

DEFAULT_PYTHON="python3"
if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  DEFAULT_PYTHON="${REPO_ROOT}/.venv/bin/python"
fi

DEFAULT_PRE_COMMIT="pre-commit"
if [[ -x "${REPO_ROOT}/.venv/bin/pre-commit" ]]; then
  DEFAULT_PRE_COMMIT="${REPO_ROOT}/.venv/bin/pre-commit"
fi

PYTHON_BIN="${PYTHON_BIN:-${DEFAULT_PYTHON}}"
PRE_COMMIT_BIN="${PRE_COMMIT_BIN:-${DEFAULT_PRE_COMMIT}}"
CURL_BIN="${CURL_BIN:-curl}"
TYPECHECK_TARGETS="${TYPECHECK_TARGETS:-src tests scripts}"
LINT_SCOPE="${LINT_SCOPE:-staged}"
SMOKE_SCRIPT="${SMOKE_SCRIPT:-${REPO_ROOT}/scripts/check_bl334_split_smokes.sh}"

RUN_LINT=1
RUN_TYPECHECK=1
RUN_SMOKE=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-lint)
      RUN_LINT=0
      shift
      ;;
    --skip-typecheck)
      RUN_TYPECHECK=0
      shift
      ;;
    --skip-smoke)
      RUN_SMOKE=0
      shift
      ;;
    --only)
      require_option_value "--only" "${2:-}"
      parse_only_steps_csv "$2"
      shift 2
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

if (( RUN_LINT == 0 && RUN_TYPECHECK == 0 && RUN_SMOKE == 0 )); then
  echo "ERROR: no steps selected (all steps skipped)" >&2
  usage >&2
  exit 2
fi

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "ERROR: required command not found: ${cmd}" >&2
    exit 2
  fi
}

run_lint() {
  if [[ "${LINT_SCOPE}" == "all" ]]; then
    "${PRE_COMMIT_BIN}" run --all-files
    return
  fi

  mapfile -t lint_files < <(
    {
      git diff --name-only --diff-filter=ACMR HEAD
      git ls-files --others --exclude-standard
    } | awk 'NF' | sort -u
  )

  if (( ${#lint_files[@]} > 0 )); then
    "${PRE_COMMIT_BIN}" run --files "${lint_files[@]}"
  else
    "${PRE_COMMIT_BIN}" run
  fi
}

run_typecheck() {
  # shellcheck disable=SC2086
  "${PYTHON_BIN}" -m compileall -q ${TYPECHECK_TARGETS}
}

run_smoke_subset() {
  PYTHON_BIN="${PYTHON_BIN}" CURL_BIN="${CURL_BIN}" "${SMOKE_SCRIPT}"
}

run_step() {
  local name="$1"
  shift

  echo "[dev:smoke] ${name}: start"
  set +e
  "$@"
  local rc=$?
  set -e

  STEP_NAMES+=("${name}")
  STEP_CODES+=("${rc}")

  if (( rc == 0 )); then
    echo "[dev:smoke] ${name}: PASS"
  else
    echo "[dev:smoke] ${name}: FAIL (exit ${rc})"
  fi
}

if (( RUN_LINT )); then
  require_cmd "${PRE_COMMIT_BIN}"
  require_cmd "git"
fi

if (( RUN_TYPECHECK || RUN_SMOKE )); then
  require_cmd "${PYTHON_BIN}"
fi

if (( RUN_SMOKE )); then
  require_cmd "${CURL_BIN}"
  if [[ ! -x "${SMOKE_SCRIPT}" ]]; then
    echo "ERROR: missing or non-executable smoke script: ${SMOKE_SCRIPT}" >&2
    exit 2
  fi
fi

cd "${REPO_ROOT}"

declare -a STEP_NAMES=()
declare -a STEP_CODES=()

if (( RUN_LINT )); then
  run_step "lint" run_lint
else
  echo "[dev:smoke] lint: SKIP (--skip-lint)"
fi

if (( RUN_TYPECHECK )); then
  run_step "typecheck" run_typecheck
else
  echo "[dev:smoke] typecheck: SKIP (--skip-typecheck)"
fi

if (( RUN_SMOKE )); then
  run_step "smoke" run_smoke_subset
else
  echo "[dev:smoke] smoke: SKIP (--skip-smoke)"
fi

overall_rc=0
echo "[dev:smoke] summary"
for idx in "${!STEP_NAMES[@]}"; do
  name="${STEP_NAMES[$idx]}"
  rc="${STEP_CODES[$idx]}"
  if (( rc == 0 )); then
    echo "  - ${name}: PASS"
  else
    echo "  - ${name}: FAIL (exit ${rc})"
    overall_rc=1
  fi
done

if (( overall_rc != 0 )); then
  echo "❌ dev:smoke failed"
  exit 1
fi

echo "✅ dev:smoke passed"
