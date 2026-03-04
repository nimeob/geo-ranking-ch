#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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

require_cmd "${PYTHON_BIN}"
require_cmd "${PRE_COMMIT_BIN}"
require_cmd "${CURL_BIN}"
require_cmd "git"

if [[ ! -x "${SMOKE_SCRIPT}" ]]; then
  echo "ERROR: missing or non-executable smoke script: ${SMOKE_SCRIPT}" >&2
  exit 2
fi

cd "${REPO_ROOT}"

declare -a STEP_NAMES=()
declare -a STEP_CODES=()

run_step "lint" run_lint
run_step "typecheck" run_typecheck
run_step "smoke" run_smoke_subset

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
