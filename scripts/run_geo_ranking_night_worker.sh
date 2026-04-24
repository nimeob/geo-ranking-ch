#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_DIR="${REPO_ROOT}/.nightlock"
LOCK_FILE="${LOCK_DIR}/geo-ranking-night-worker.lock"
RUNTIME_DIR="${REPO_ROOT}/.night-worker/runtime"
REPORT_DIR="${REPO_ROOT}/reports/nightworker"
MAIN_LOG="${REPO_ROOT}/reports/nightwatchdog.log"
PID_FILE="${RUNTIME_DIR}/night-worker.pid"

INTERVAL_SECONDS="${NIGHT_WORKER_INTERVAL_SECONDS:-900}"
UI_BASE_URL="${NIGHT_WORKER_UI_BASE_URL:-https://www.dev.georanking.ch}"
API_BASE_URL="${NIGHT_WORKER_API_BASE_URL:-https://api.dev.georanking.ch}"
ONE_SHOT="${NIGHT_WORKER_ONESHOT:-0}"
CI_AUTORETRY_ENABLED="${NIGHT_WORKER_CI_AUTORETRY_ENABLED:-1}"
CI_AUTORETRY_MAX_PER_CYCLE="${NIGHT_WORKER_CI_AUTORETRY_MAX_PER_CYCLE:-3}"
CI_AUTORETRY_COOLDOWN_MINUTES="${NIGHT_WORKER_CI_AUTORETRY_COOLDOWN_MINUTES:-90}"
CI_RERUN_TIMEOUT_SECONDS="${NIGHT_WORKER_CI_RERUN_TIMEOUT_SECONDS:-90}"
CI_MONITORED_BRANCHES="${NIGHT_WORKER_CI_MONITORED_BRANCHES:-main}"
CI_MONITORED_EVENTS="${NIGHT_WORKER_CI_MONITORED_EVENTS:-push,workflow_dispatch,schedule,repository_dispatch}"

GHA_BIN="${NIGHT_WORKER_GHA_BIN:-./scripts/gha}"
BLOCKER_RETRY_SCRIPT="${NIGHT_WORKER_BLOCKER_RETRY_SCRIPT:-scripts/blocker_retry_supervisor.py}"
AUTH_SMOKE_SCRIPT="${NIGHT_WORKER_AUTH_SMOKE_SCRIPT:-./scripts/smoke/run_auth_perimeter_smoke_bundle.sh}"
PYTHON_BIN="${NIGHT_WORKER_PYTHON_BIN:-python3}"
CI_RERUN_STATE_FILE="${RUNTIME_DIR}/ci-rerun-state.json"

# Ensure gh CLI is discoverable in non-interactive/night shells.
for d in \
  "${REPO_ROOT}/.tools/bin" \
  "${REPO_ROOT}/.local/bin" \
  "/data/.openclaw/workspace/.tools/bin" \
  "/data/.openclaw/workspace/.local/bin" \
  "/data/.openclaw/workspace/tools/gh/bin" \
  "/data/.openclaw/workspace/bin" \
  "/data/linuxbrew/.linuxbrew/bin"; do
  if [[ -d "$d" ]]; then
    PATH="$d:$PATH"
  fi
done
export PATH

mkdir -p "${LOCK_DIR}" "${RUNTIME_DIR}" "${REPORT_DIR}" "$(dirname "${MAIN_LOG}")"

log() {
  local msg="$1"
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '[%s] %s\n' "${ts}" "${msg}" | tee -a "${MAIN_LOG}" >> "${RUNTIME_DIR}/night-worker.log"
}

run_gha_rerun() {
  local run_id="$1"
  if [[ "${CI_RERUN_TIMEOUT_SECONDS}" =~ ^[0-9]+$ ]] && (( CI_RERUN_TIMEOUT_SECONDS > 0 )) && command -v timeout >/dev/null 2>&1; then
    timeout --signal=TERM --kill-after=10s "${CI_RERUN_TIMEOUT_SECONDS}s" "${GHA_BIN}" run rerun "${run_id}"
  else
    "${GHA_BIN}" run rerun "${run_id}"
  fi
}

json_get_pid() {
  local lock_path="$1"
  "${PYTHON_BIN}" - <<'PY' "${lock_path}" 2>/dev/null || true
import json
import sys

try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    raise SystemExit(0)

pid = data.get("pid")
if pid is None:
    raise SystemExit(0)
print(pid)
PY
}

write_lock() {
  cat > "${LOCK_FILE}" <<EOF
{"pid":$$,"timestamp":"$(date --iso-8601=seconds)","epoch":$(date +%s),"worker":"geo-ranking-night-worker","worktree":"${REPO_ROOT}"}
EOF
  echo "$$" > "${PID_FILE}"
}

cleanup() {
  local rc=$?
  if [[ -f "${PID_FILE}" ]] && [[ "$(cat "${PID_FILE}" 2>/dev/null || true)" == "$$" ]]; then
    rm -f "${PID_FILE}"
  fi
  if [[ -f "${LOCK_FILE}" ]]; then
    local owner_pid
    owner_pid="$(json_get_pid "${LOCK_FILE}")"
    if [[ "${owner_pid}" == "$$" ]]; then
      rm -f "${LOCK_FILE}"
    fi
  fi
  log "STOP: geo-ranking-night-worker beendet (rc=${rc})"
}
trap cleanup EXIT INT TERM

if [[ -f "${LOCK_FILE}" ]]; then
  existing_pid="$(json_get_pid "${LOCK_FILE}")"
  if [[ -n "${existing_pid}" ]] && kill -0 "${existing_pid}" 2>/dev/null; then
    echo "Night worker läuft bereits mit PID ${existing_pid} (${LOCK_FILE})" >&2
    exit 3
  fi
fi

cd "${REPO_ROOT}"
write_lock
log "START: geo-ranking-night-worker auf ${REPO_ROOT} (interval=${INTERVAL_SECONDS}s, ui=${UI_BASE_URL}, api=${API_BASE_URL})"

if command -v gh >/dev/null 2>&1; then
  log "PRECHECK: gh gefunden unter $(command -v gh)"
else
  log "BLOCKER: gh CLI nicht gefunden (PATH=$PATH)"
fi
log "PRECHECK: CI monitor filter branches=${CI_MONITORED_BRANCHES:-*}, events=${CI_MONITORED_EVENTS:-*}, rerun-timeout=${CI_RERUN_TIMEOUT_SECONDS}s"

while true; do
  cycle_ts="$(date -u +%Y%m%dT%H%M%SZ)"
  cycle_blockers=0

  log "CYCLE ${cycle_ts}: begin"

  blocker_snapshot_json="${REPORT_DIR}/${cycle_ts}-blocked-issues.json"
  if "${GHA_BIN}" issue list --state open --label status:blocked --limit 200 --json number,title,url > "${blocker_snapshot_json}" 2>> "${RUNTIME_DIR}/night-worker.log"; then
    blocked_count="$("${PYTHON_BIN}" - <<'PY' "${blocker_snapshot_json}"
import json
import sys

try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    print(len(data))
except Exception:
    print(-1)
PY
)"
    if [[ "${blocked_count}" =~ ^[0-9]+$ ]] && (( blocked_count > 0 )); then
      cycle_blockers=$((cycle_blockers + blocked_count))
      log "BLOCKER: ${blocked_count} Issue(s) mit status:blocked gefunden (siehe ${blocker_snapshot_json})"
    else
      log "CYCLE ${cycle_ts}: keine offenen status:blocked Issues"
    fi
  else
    cycle_blockers=$((cycle_blockers + 1))
    log "BLOCKER: status:blocked Snapshot fehlgeschlagen"
  fi

  if "${PYTHON_BIN}" "${BLOCKER_RETRY_SCRIPT}" >> "${RUNTIME_DIR}/night-worker.log" 2>&1; then
    log "CYCLE ${cycle_ts}: blocker_retry_supervisor erfolgreich"
  else
    cycle_blockers=$((cycle_blockers + 1))
    log "BLOCKER: blocker_retry_supervisor fehlgeschlagen"
  fi

  auth_summary="${REPO_ROOT}/reports/evidence/dev-night-${cycle_ts}-auth-perimeter-smoke-bundle-summary.json"
  mkdir -p "$(dirname "${auth_summary}")"
  if "${AUTH_SMOKE_SCRIPT}" \
      --base-url "${UI_BASE_URL}" \
      --api-base-url "${API_BASE_URL}" \
      --route-presets minimal \
      --env-name "dev-night-${cycle_ts}" \
      --summary-json "${auth_summary}" \
      --quiet >> "${RUNTIME_DIR}/night-worker.log" 2>&1; then
    log "CYCLE ${cycle_ts}: auth-perimeter smoke PASS (${auth_summary})"
  else
    cycle_blockers=$((cycle_blockers + 1))
    log "BLOCKER: auth-perimeter smoke FAIL (${auth_summary})"
  fi

  runs_snapshot_json="${REPORT_DIR}/${cycle_ts}-recent-runs.json"
  if "${GHA_BIN}" run list --limit 10 --json databaseId,workflowName,status,conclusion,createdAt,url,headBranch,event > "${runs_snapshot_json}" 2>> "${RUNTIME_DIR}/night-worker.log"; then
    recent_failures="$("${PYTHON_BIN}" - <<'PY' "${runs_snapshot_json}" "${CI_MONITORED_BRANCHES}" "${CI_MONITORED_EVENTS}"
import json
import sys
from datetime import datetime, timedelta, timezone


runs_path, branches_raw, events_raw = sys.argv[1:4]


def parse_csv(raw: str, lower: bool = False) -> set[str]:
    out: set[str] = set()
    for item in (raw or "").split(','):
        value = item.strip()
        if not value:
            continue
        out.add(value.lower() if lower else value)
    return out


branch_allow = parse_csv(branches_raw)
event_allow = parse_csv(events_raw, lower=True)


def parse_dt(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(timezone.utc)


def monitored(run):
    if branch_allow:
        branch = (run.get('headBranch') or '').strip()
        if branch not in branch_allow:
            return False
    if event_allow:
        event = (run.get('event') or '').strip().lower()
        if event not in event_allow:
            return False
    return True


try:
    data = json.load(open(runs_path, encoding="utf-8"))
except Exception:
    print(0)
    raise SystemExit

cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
count = 0
for run in data:
    if not monitored(run):
        continue
    conclusion = (run.get('conclusion') or '').lower()
    status = (run.get('status') or '').lower()
    created = run.get('createdAt')
    if not created:
        continue
    try:
        dt = parse_dt(created)
    except Exception:
        continue
    if dt < cutoff:
        continue
    if conclusion in {'failure', 'cancelled', 'timed_out', 'action_required', 'startup_failure'}:
        count += 1
    elif status == 'completed' and conclusion not in {'success', 'skipped', 'neutral'}:
        count += 1
print(count)
PY
)"
    if [[ "${recent_failures}" =~ ^[0-9]+$ ]] && (( recent_failures > 0 )); then
      cycle_blockers=$((cycle_blockers + recent_failures))
      log "BLOCKER: ${recent_failures} fehlgeschlagene/abgebrochene CI Runs in den letzten 6h (Filter branches=${CI_MONITORED_BRANCHES:-*}, events=${CI_MONITORED_EVENTS:-*}; siehe ${runs_snapshot_json})"

      if [[ "${CI_AUTORETRY_ENABLED}" == "1" ]]; then
        rerun_candidates="$(${PYTHON_BIN} - <<'PY' "${runs_snapshot_json}" "${CI_RERUN_STATE_FILE}" "${CI_AUTORETRY_MAX_PER_CYCLE}" "${CI_AUTORETRY_COOLDOWN_MINUTES}" "${CI_MONITORED_BRANCHES}" "${CI_MONITORED_EVENTS}"
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

runs_path, state_path, max_per_cycle_raw, cooldown_minutes_raw, branches_raw, events_raw = sys.argv[1:7]

try:
    max_per_cycle = int(max_per_cycle_raw)
except Exception:
    max_per_cycle = 3
if max_per_cycle < 1:
    max_per_cycle = 1

try:
    cooldown_minutes = int(cooldown_minutes_raw)
except Exception:
    cooldown_minutes = 90
if cooldown_minutes < 1:
    cooldown_minutes = 1
cooldown_seconds = cooldown_minutes * 60


def parse_csv(raw: str, lower: bool = False) -> set[str]:
    out: set[str] = set()
    for item in (raw or "").split(','):
        value = item.strip()
        if not value:
            continue
        out.add(value.lower() if lower else value)
    return out


branch_allow = parse_csv(branches_raw)
event_allow = parse_csv(events_raw, lower=True)

def parse_dt(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(timezone.utc)


def monitored(run):
    if branch_allow:
        branch = (run.get('headBranch') or '').strip()
        if branch not in branch_allow:
            return False
    if event_allow:
        event = (run.get('event') or '').strip().lower()
        if event not in event_allow:
            return False
    return True

try:
    runs = json.load(open(runs_path, encoding='utf-8'))
except Exception:
    raise SystemExit(0)

try:
    state = json.load(open(state_path, encoding='utf-8'))
except Exception:
    state = {}
if not isinstance(state, dict):
    state = {}

cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
now_epoch = int(time.time())

def failed(run):
    conclusion = (run.get('conclusion') or '').lower()
    status = (run.get('status') or '').lower()
    if conclusion in {'failure', 'cancelled', 'timed_out', 'action_required', 'startup_failure'}:
        return True
    if status == 'completed' and conclusion not in {'success', 'skipped', 'neutral'}:
        return True
    return False

selected = []
for run in runs:
    if not monitored(run):
        continue
    if not failed(run):
        continue
    created = run.get('createdAt')
    if not created:
        continue
    try:
        if parse_dt(created) < cutoff:
            continue
    except Exception:
        continue

    run_id = run.get('databaseId')
    if not isinstance(run_id, int):
        continue
    last_retry = state.get(str(run_id), 0)
    if isinstance(last_retry, str) and last_retry.isdigit():
        last_retry = int(last_retry)
    if not isinstance(last_retry, int):
        last_retry = 0
    if now_epoch - last_retry < cooldown_seconds:
        continue

    selected.append((run_id, run.get('workflowName') or 'unknown'))
    if len(selected) >= max_per_cycle:
        break

for run_id, workflow_name in selected:
    print(f"{run_id}|{workflow_name}")
PY
)"

        rerun_success_ids=""
        if [[ -n "${rerun_candidates}" ]]; then
          while IFS='|' read -r run_id workflow_name; do
            [[ -n "${run_id}" ]] || continue
            if run_gha_rerun "${run_id}" >> "${RUNTIME_DIR}/night-worker.log" 2>&1; then
              log "ACTION: CI-Rerun ausgelöst für Run ${run_id} (${workflow_name})"
              rerun_success_ids+="${run_id} "
            else
              rerun_rc=$?
              cycle_blockers=$((cycle_blockers + 1))
              if [[ ${rerun_rc} -eq 124 ]]; then
                log "BLOCKER: CI-Rerun timeout nach ${CI_RERUN_TIMEOUT_SECONDS}s für Run ${run_id} (${workflow_name})"
              else
                log "BLOCKER: CI-Rerun fehlgeschlagen (rc=${rerun_rc}) für Run ${run_id} (${workflow_name})"
              fi
            fi
          done <<< "${rerun_candidates}"

          if [[ -n "${rerun_success_ids}" ]]; then
            ${PYTHON_BIN} - <<'PY' "${CI_RERUN_STATE_FILE}" ${rerun_success_ids}
import json
import sys
import time

state_path = sys.argv[1]
ids = sys.argv[2:]

try:
    state = json.load(open(state_path, encoding='utf-8'))
except Exception:
    state = {}
if not isinstance(state, dict):
    state = {}

now_epoch = int(time.time())
for rid in ids:
    if rid:
        state[str(rid)] = now_epoch

with open(state_path, 'w', encoding='utf-8') as fh:
    json.dump(state, fh, ensure_ascii=False, indent=2)
PY
          fi
        else
          log "CYCLE ${cycle_ts}: keine CI-Rerun-Kandidaten (Cooldown aktiv oder keine retry-fähigen Runs)"
        fi
      fi
    else
      log "CYCLE ${cycle_ts}: keine fehlgeschlagenen überwachten CI Runs in den letzten 6h"
    fi
  else
    cycle_blockers=$((cycle_blockers + 1))
    log "BLOCKER: CI-Run-Snapshot fehlgeschlagen"
  fi

  if (( cycle_blockers > 0 )); then
    blocker_note="${REPORT_DIR}/${cycle_ts}-blockers.md"
    mkdir -p "$(dirname "${blocker_note}")"
    {
      printf '# Night Worker Blockers – %s\n\n' "${cycle_ts}"
      printf -- '- Worktree: `%s`\n' "${REPO_ROOT}"
      printf -- '- Erkannte Blocker-Signale: **%s**\n' "${cycle_blockers}"
      printf -- '- Blocked-Issues-Snapshot: `%s`\n' "${blocker_snapshot_json}"
      printf -- '- CI-Snapshot: `%s`\n' "${runs_snapshot_json}"
      printf -- '- Runtime-Log: `%s`\n' "${RUNTIME_DIR}/night-worker.log"
      printf -- '- Auth-Summary: `%s`\n' "${auth_summary}"
    } > "${blocker_note}"
    log "CYCLE ${cycle_ts}: abgeschlossen MIT BLOCKERN (${blocker_note})"
  else
    log "CYCLE ${cycle_ts}: abgeschlossen ohne Blocker"
  fi

  if [[ "${ONE_SHOT}" == "1" ]]; then
    log "CYCLE ${cycle_ts}: one-shot mode aktiv, beende nach einem Zyklus"
    break
  fi

  sleep "${INTERVAL_SECONDS}"
done
