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
LINT_INCLUDE_UNTRACKED="${LINT_INCLUDE_UNTRACKED:-1}"
LINT_CHUNK_SIZE="${LINT_CHUNK_SIZE:-200}"
LINT_EXCLUDE_PREFIXES_DEFAULT=".local/ .tmp .night-worker/ .nightworker/ .nightlock/ .worktrees/ artifacts/ logs/ workspace-logs/ node_modules/ reports/evidence/"
LINT_EXCLUDE_PREFIXES_RAW="${LINT_EXCLUDE_PREFIXES:-${LINT_EXCLUDE_PREFIXES_DEFAULT}}"

read -r -a LINT_EXCLUDE_PREFIXES <<< "${LINT_EXCLUDE_PREFIXES_RAW}"

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

is_excluded_lint_prefix() {
  local candidate="$1"
  local prefix
  for prefix in "${LINT_EXCLUDE_PREFIXES[@]}"; do
    [[ -n "${prefix}" ]] || continue
    if [[ "${candidate}" == "${prefix}"* ]]; then
      return 0
    fi
  done
  return 1
}

is_known_binary_artifact() {
  local candidate="$1"
  case "${candidate}" in
    *.tar|*.tar.gz|*.tgz|*.zip|*.gz|*.7z|*.rar|*.pdf|*.png|*.jpg|*.jpeg|*.gif|*.webp|*.ico|*.mp3|*.mp4|*.mov|*.avi|*.woff|*.woff2)
      return 0
      ;;
  esac
  return 1
}

lint_file_allowed() {
  local candidate="$1"
  [[ -n "${candidate}" ]] || return 1
  [[ -f "${candidate}" ]] || return 1

  if is_forbidden_lint_file "${candidate}"; then
    return 1
  fi

  if is_excluded_lint_prefix "${candidate}"; then
    return 1
  fi

  if is_known_binary_artifact "${candidate}"; then
    return 1
  fi

  return 0
}

run_pre_commit_for_files() {
  local -a files=("$@")
  local total="${#files[@]}"
  local preview_limit=10
  local chunk_size="${LINT_CHUNK_SIZE}"

  if ! [[ "${chunk_size}" =~ ^[0-9]+$ ]] || (( chunk_size < 1 )); then
    chunk_size=200
  fi

  if (( total == 0 )); then
    echo "[dev-check] lint: ${PRE_COMMIT_BIN} run"
    "${PRE_COMMIT_BIN}" run
    return
  fi

  if (( total <= preview_limit )); then
    echo "[dev-check] lint targets (${total}): ${files[*]}"
  else
    echo "[dev-check] lint targets (${total}, preview ${preview_limit}): ${files[*]:0:preview_limit} ..."
  fi

  if (( total <= chunk_size )); then
    echo "[dev-check] lint: ${PRE_COMMIT_BIN} run --files <${total} files>"
    "${PRE_COMMIT_BIN}" run --files "${files[@]}"
    return
  fi

  echo "[dev-check] lint: ${PRE_COMMIT_BIN} run --files in chunks (chunk_size=${chunk_size})"
  local i=0
  while (( i < total )); do
    local -a chunk=("${files[@]:i:chunk_size}")
    echo "[dev-check] lint chunk: files $((i + 1))-$((i + ${#chunk[@]}))/${total}"
    "${PRE_COMMIT_BIN}" run --files "${chunk[@]}"
    (( i += ${#chunk[@]} ))
  done
}

if [[ "${LINT_SCOPE}" == "all" ]]; then
  echo "[dev-check] lint: ${PRE_COMMIT_BIN} run --all-files"
  "${PRE_COMMIT_BIN}" run --all-files
else
  mapfile -t lint_files < <(
    {
      git diff --name-only --diff-filter=ACMR HEAD
      if [[ "${LINT_INCLUDE_UNTRACKED}" == "1" ]]; then
        git ls-files --others --exclude-standard
      fi
    } | awk 'NF' | sort -u | while IFS= read -r file; do
      if lint_file_allowed "${file}"; then
        printf '%s\n' "${file}"
      fi
    done
  )

  run_pre_commit_for_files "${lint_files[@]}"
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
