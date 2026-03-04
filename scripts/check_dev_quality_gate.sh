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

if [[ "${LINT_SCOPE}" == "all" ]]; then
  echo "[dev-check] lint: ${PRE_COMMIT_BIN} run --all-files"
  "${PRE_COMMIT_BIN}" run --all-files
else
  mapfile -t lint_files < <(
    {
      git diff --name-only --diff-filter=ACMR HEAD
      git ls-files --others --exclude-standard
    } | awk 'NF' | sort -u
  )

  if (( ${#lint_files[@]} > 0 )); then
    echo "[dev-check] lint: ${PRE_COMMIT_BIN} run --files ${lint_files[*]}"
    "${PRE_COMMIT_BIN}" run --files "${lint_files[@]}"
  else
    echo "[dev-check] lint: ${PRE_COMMIT_BIN} run"
    "${PRE_COMMIT_BIN}" run
  fi
fi

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
