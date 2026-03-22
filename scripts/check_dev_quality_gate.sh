#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python_has_module() {
  local python_bin="$1"
  local module_name="$2"
  "${python_bin}" - "${module_name}" >/dev/null 2>&1 <<'PY'
import importlib.util
import sys
module_name = sys.argv[1]
raise SystemExit(0 if importlib.util.find_spec(module_name) else 1)
PY
}

pick_python_bin() {
  local -a candidates=()

  if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    candidates+=("${REPO_ROOT}/.venv/bin/python")
  fi

  candidates+=("python3")

  if [[ -x "/usr/bin/python3" ]]; then
    candidates+=("/usr/bin/python3")
  fi

  local candidate
  for candidate in "${candidates[@]}"; do
    if ! command -v "${candidate}" >/dev/null 2>&1; then
      continue
    fi

    if python_has_module "${candidate}" "pytest"; then
      echo "${candidate}"
      return 0
    fi
  done

  # Fallback to the first executable candidate and let pytest fail with a clear message later.
  for candidate in "${candidates[@]}"; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      echo "${candidate}"
      return 0
    fi
  done

  return 1
}

DEFAULT_PYTHON="$(pick_python_bin)"

DEFAULT_PRE_COMMIT="pre-commit"
if [[ -x "${REPO_ROOT}/.venv/bin/pre-commit" ]]; then
  DEFAULT_PRE_COMMIT="${REPO_ROOT}/.venv/bin/pre-commit"
fi

PYTHON_BIN="${PYTHON_BIN:-${DEFAULT_PYTHON}}"
PRE_COMMIT_BIN="${PRE_COMMIT_BIN:-${DEFAULT_PRE_COMMIT}}"
TYPECHECK_TARGETS="${TYPECHECK_TARGETS:-src tests scripts}"
UNIT_TEST_TARGETS="${UNIT_TEST_TARGETS:-}"
LINT_SCOPE="${LINT_SCOPE:-staged}"

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "ERROR: required command not found: ${cmd}" >&2
    exit 2
  fi
}

require_cmd "${PYTHON_BIN}"
require_cmd "${PRE_COMMIT_BIN}"
require_cmd "git"

cd "${REPO_ROOT}"

FORBIDDEN_WIP_LINT_FILES=(
  "reports/consistency_report.json"
  "reports/consistency_report.md"
  "triage_add_labels.sh"
)

is_forbidden_lint_file() {
  local candidate="$1"
  local forbidden
  for forbidden in "${FORBIDDEN_WIP_LINT_FILES[@]}"; do
    if [[ "${candidate}" == "${forbidden}" ]]; then
      return 0
    fi
  done
  return 1
}

if [[ "${LINT_SCOPE}" == "all" ]]; then
  echo "[dev-check] lint: ${PRE_COMMIT_BIN} run --all-files"
  "${PRE_COMMIT_BIN}" run --all-files
else
  mapfile -t lint_files < <(
    {
      git diff --name-only --diff-filter=ACMR HEAD
      git ls-files --others --exclude-standard
    } | awk 'NF' | sort -u | while IFS= read -r file; do
      [[ -n "${file}" ]] || continue
      [[ -f "${file}" ]] || continue
      if is_forbidden_lint_file "${file}"; then
        continue
      fi
      printf '%s\n' "${file}"
    done
  )

  if (( ${#lint_files[@]} > 0 )); then
    echo "[dev-check] lint: ${PRE_COMMIT_BIN} run --files ${lint_files[*]}"
    "${PRE_COMMIT_BIN}" run --files "${lint_files[@]}"
  else
    echo "[dev-check] lint: ${PRE_COMMIT_BIN} run"
    "${PRE_COMMIT_BIN}" run
  fi
fi

echo "[dev-check] boundaries: ${PYTHON_BIN} scripts/check_bl31_service_boundaries.py --src-dir src"
"${PYTHON_BIN}" scripts/check_bl31_service_boundaries.py --src-dir src

echo "[dev-check] typecheck: ${PYTHON_BIN} -m compileall -q ${TYPECHECK_TARGETS}"
"${PYTHON_BIN}" -m compileall -q ${TYPECHECK_TARGETS}

if [[ -n "${UNIT_TEST_TARGETS}" ]]; then
  echo "[dev-check] unit-tests: ${PYTHON_BIN} -m pytest -q ${UNIT_TEST_TARGETS}"
  # shellcheck disable=SC2086
  "${PYTHON_BIN}" -m pytest -q ${UNIT_TEST_TARGETS}
else
  echo "[dev-check] unit-tests: ${PYTHON_BIN} -m pytest -q"
  "${PYTHON_BIN}" -m pytest -q
fi

echo "✅ dev-check passed"
