#!/usr/bin/env bash
set -euo pipefail

MODE="dry-run"
MIN_ERRORS="${MIN_ERRORS:-5}"
TAIL_LINES="${TAIL_LINES:-120}"

usage() {
  cat <<'EOF'
Usage: scripts/cleanup_stale_geo_night_workers.sh [--apply] [--min-errors N] [--tail-lines N]

Detects noisy/stale geo night-worker processes that repeatedly emit
"No such file or directory" path errors and (optionally) terminates them.

Default mode is dry-run.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      MODE="apply"
      shift
      ;;
    --min-errors)
      MIN_ERRORS="$2"
      shift 2
      ;;
    --tail-lines)
      TAIL_LINES="$2"
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

if ! [[ "${MIN_ERRORS}" =~ ^[0-9]+$ ]]; then
  echo "--min-errors must be an integer" >&2
  exit 2
fi

if ! [[ "${TAIL_LINES}" =~ ^[0-9]+$ ]]; then
  echo "--tail-lines must be an integer" >&2
  exit 2
fi

mapfile -t candidates < <(ps -eo pid=,args= | awk '/run_geo_ranking_night_worker\.sh/ {print $1}')

if (( ${#candidates[@]} == 0 )); then
  echo "No geo night-worker processes found."
  exit 0
fi

declare -a stale_pids=()

echo "Found ${#candidates[@]} geo night-worker process(es). Inspecting…"

for pid in "${candidates[@]}"; do
  [[ -d "/proc/${pid}" ]] || continue

  cmdline="$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)"
  cwd="$(readlink -f "/proc/${pid}/cwd" 2>/dev/null || true)"
  stdout_target="$(readlink -f "/proc/${pid}/fd/1" 2>/dev/null || true)"
  err_count=0

  if [[ -n "${stdout_target}" ]] && [[ -f "${stdout_target}" ]]; then
    err_count="$(tail -n "${TAIL_LINES}" "${stdout_target}" 2>/dev/null | grep -cE 'run_geo_ranking_night_worker\.sh: line [0-9]+: .*No such file or directory' || true)"
  fi

  if (( err_count >= MIN_ERRORS )); then
    stale_pids+=("${pid}")
    echo "STALE pid=${pid} errors=${err_count}/${TAIL_LINES} cwd=${cwd:-unknown}"
    echo "  cmd: ${cmdline}"
    if [[ -n "${stdout_target}" ]]; then
      echo "  log: ${stdout_target}"
    fi
  else
    echo "OK    pid=${pid} errors=${err_count}/${TAIL_LINES} cwd=${cwd:-unknown}"
  fi
done

if (( ${#stale_pids[@]} == 0 )); then
  echo "No stale/noisy geo night-worker processes detected."
  exit 0
fi

if [[ "${MODE}" != "apply" ]]; then
  echo "Dry-run only. Re-run with --apply to terminate stale processes: ${stale_pids[*]}"
  exit 0
fi

for pid in "${stale_pids[@]}"; do
  if kill -0 "${pid}" 2>/dev/null; then
    kill -TERM "${pid}" 2>/dev/null || true
  fi
done

sleep 1

for pid in "${stale_pids[@]}"; do
  if kill -0 "${pid}" 2>/dev/null; then
    echo "pid=${pid} still running after TERM; sending KILL"
    kill -KILL "${pid}" 2>/dev/null || true
  fi
done

echo "Cleanup done. Terminated stale process(es): ${stale_pids[*]}"
