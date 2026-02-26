#!/usr/bin/env bash
set -euo pipefail

# BL-18.1 Stabilitäts-/Abnahme-Lauf über mehrere Remote-Smoke-Requests.
# Führt das bestehende Smoke-Script mehrfach aus und schreibt einen NDJSON-Report.
#
# Nutzung:
#   DEV_BASE_URL="https://<endpoint>" ./scripts/run_remote_api_stability_check.sh
#
# Optionale Env-Variablen:
#   STABILITY_RUNS="6"
#   STABILITY_INTERVAL_SECONDS="15"
#   STABILITY_MAX_FAILURES="0"
#   STABILITY_REPORT_PATH="artifacts/bl18.1-remote-stability.ndjson"  # wird getrimmt; whitespace-only -> fail-fast
#   STABILITY_STOP_ON_FIRST_FAIL="0"
#   STABILITY_SMOKE_SCRIPT="/path/to/run_remote_api_smoketest.sh"  # optionales Override (Tests/Debug)
#   + alle Variablen aus run_remote_api_smoketest.sh (SMOKE_QUERY, DEV_API_AUTH_TOKEN, ...)

if [[ -z "${DEV_BASE_URL:-}" ]]; then
  echo "[BL-18.1] DEV_BASE_URL ist nicht gesetzt. Beispiel: DEV_BASE_URL=https://<endpoint> ./scripts/run_remote_api_stability_check.sh" >&2
  exit 2
fi

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SMOKE_SCRIPT="${STABILITY_SMOKE_SCRIPT:-${REPO_ROOT}/scripts/run_remote_api_smoketest.sh}"

if [[ ! -x "$SMOKE_SCRIPT" ]]; then
  echo "[BL-18.1] Smoke-Script nicht ausführbar/gefunden: ${SMOKE_SCRIPT}" >&2
  exit 2
fi

STABILITY_RUNS="${STABILITY_RUNS:-6}"
STABILITY_INTERVAL_SECONDS="${STABILITY_INTERVAL_SECONDS:-15}"
STABILITY_MAX_FAILURES="${STABILITY_MAX_FAILURES:-0}"
STABILITY_REPORT_PATH_RAW="${STABILITY_REPORT_PATH:-artifacts/bl18.1-remote-stability.ndjson}"
STABILITY_REPORT_PATH="${STABILITY_REPORT_PATH_RAW}"
STABILITY_STOP_ON_FIRST_FAIL="${STABILITY_STOP_ON_FIRST_FAIL:-0}"

trim_value() {
  python3 - "$1" <<'PY'
import sys
print(sys.argv[1].strip())
PY
}

STABILITY_RUNS="$(trim_value "${STABILITY_RUNS}")"
STABILITY_INTERVAL_SECONDS="$(trim_value "${STABILITY_INTERVAL_SECONDS}")"
STABILITY_MAX_FAILURES="$(trim_value "${STABILITY_MAX_FAILURES}")"
STABILITY_REPORT_PATH="$(trim_value "${STABILITY_REPORT_PATH}")"
STABILITY_STOP_ON_FIRST_FAIL="$(trim_value "${STABILITY_STOP_ON_FIRST_FAIL}")"

if [[ -n "${STABILITY_REPORT_PATH_RAW}" && -z "${STABILITY_REPORT_PATH}" ]]; then
  echo "[BL-18.1] STABILITY_REPORT_PATH ist leer nach Whitespace-Normalisierung." >&2
  exit 2
fi

if ! python3 - "${STABILITY_REPORT_PATH}" <<'PY'
import sys

path = sys.argv[1]
if any(ord(ch) < 32 or ord(ch) == 127 for ch in path):
    raise SystemExit(1)
PY
then
  echo "[BL-18.1] STABILITY_REPORT_PATH darf keine Steuerzeichen enthalten." >&2
  exit 2
fi

if ! [[ "$STABILITY_RUNS" =~ ^[0-9]+$ ]] || [[ "$STABILITY_RUNS" -le 0 ]]; then
  echo "[BL-18.1] STABILITY_RUNS muss eine positive Ganzzahl sein (aktuell: ${STABILITY_RUNS})." >&2
  exit 2
fi
if ! [[ "$STABILITY_INTERVAL_SECONDS" =~ ^[0-9]+$ ]]; then
  echo "[BL-18.1] STABILITY_INTERVAL_SECONDS muss eine Ganzzahl >= 0 sein (aktuell: ${STABILITY_INTERVAL_SECONDS})." >&2
  exit 2
fi
if ! [[ "$STABILITY_MAX_FAILURES" =~ ^[0-9]+$ ]]; then
  echo "[BL-18.1] STABILITY_MAX_FAILURES muss eine Ganzzahl >= 0 sein (aktuell: ${STABILITY_MAX_FAILURES})." >&2
  exit 2
fi

case "$STABILITY_STOP_ON_FIRST_FAIL" in
  0|1) ;;
  *)
    echo "[BL-18.1] STABILITY_STOP_ON_FIRST_FAIL muss 0 oder 1 sein (aktuell: ${STABILITY_STOP_ON_FIRST_FAIL})." >&2
    exit 2
    ;;
esac

mkdir -p "$(dirname -- "$STABILITY_REPORT_PATH")"
: > "$STABILITY_REPORT_PATH"

echo "[BL-18.1] Stabilitätslauf startet: runs=${STABILITY_RUNS}, interval=${STABILITY_INTERVAL_SECONDS}s, max_failures=${STABILITY_MAX_FAILURES}"

pass_count=0
fail_count=0

for run_no in $(seq 1 "$STABILITY_RUNS"); do
  echo "[BL-18.1] Run ${run_no}/${STABILITY_RUNS} ..."
  tmp_json="$(mktemp)"
  request_id="bl18-stability-${run_no}-$(date +%s)-$$"

  set +e
  (
    cd "$REPO_ROOT"
    SMOKE_REQUEST_ID="$request_id" SMOKE_OUTPUT_JSON="$tmp_json" "$SMOKE_SCRIPT"
  )
  rc=$?
  set -e

  run_failed=0
  if [[ "$rc" -ne 0 ]]; then
    run_failed=1
    echo "[BL-18.1] WARN: Run ${run_no} fehlgeschlagen (rc=${rc})."
  fi

  if [[ -s "$tmp_json" ]]; then
    report_outcome="$(python3 - "$tmp_json" "$run_no" "$STABILITY_REPORT_PATH" <<'PY'
import json
import sys

src = sys.argv[1]
run_no = int(sys.argv[2])
report_path = sys.argv[3]

status = "pass"
reason = "ok"

try:
    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    data = {
        "status": "fail",
        "reason": "invalid_report_json",
        "run_no": run_no,
    }
    status = "fail"
    reason = "invalid_report_json"
else:
    if not isinstance(data, dict):
        data = {
            "status": "fail",
            "reason": "invalid_report_payload",
            "run_no": run_no,
            "report_type": type(data).__name__,
        }
        status = "fail"
        reason = "invalid_report_payload"
    else:
        data["run_no"] = run_no
        if data.get("status") != "pass":
            status = "fail"
            reason = str(data.get("reason") or "smoke_report_status")

with open(report_path, "a", encoding="utf-8") as f:
    f.write(json.dumps(data, ensure_ascii=False) + "\n")

print(f"{status}:{reason}")
PY
)"

    if [[ "$report_outcome" != pass:* ]]; then
      run_failed=1
      echo "[BL-18.1] WARN: Run ${run_no} lieferte keinen PASS-Report (${report_outcome#*:})."
    fi
  else
    run_failed=1
    if [[ "$rc" -eq 0 ]]; then
      echo "[BL-18.1] WARN: Run ${run_no} lieferte kein Smoke-JSON (tmp_json fehlt/leer trotz rc=0)."
    fi
    python3 - "$run_no" "$rc" >> "$STABILITY_REPORT_PATH" <<'PY'
import json
import sys

run_no = int(sys.argv[1])
rc = int(sys.argv[2])
print(json.dumps({"status": "fail", "reason": "missing_report", "run_no": run_no, "rc": rc}, ensure_ascii=False))
PY
  fi

  if [[ "$run_failed" -eq 0 ]]; then
    pass_count=$((pass_count + 1))
  else
    fail_count=$((fail_count + 1))
  fi

  rm -f "$tmp_json"

  if [[ "$STABILITY_STOP_ON_FIRST_FAIL" == "1" && "$run_failed" -ne 0 ]]; then
    echo "[BL-18.1] Abbruch nach erstem Fehlrun (STABILITY_STOP_ON_FIRST_FAIL=1)."
    break
  fi

  if [[ "$run_no" -lt "$STABILITY_RUNS" && "$STABILITY_INTERVAL_SECONDS" -gt 0 ]]; then
    sleep "$STABILITY_INTERVAL_SECONDS"
  fi
done

echo "[BL-18.1] Stabilitätslauf abgeschlossen: pass=${pass_count}, fail=${fail_count}, report=${STABILITY_REPORT_PATH}"

if [[ "$fail_count" -gt "$STABILITY_MAX_FAILURES" ]]; then
  echo "[BL-18.1] FAIL: fail_count (${fail_count}) > STABILITY_MAX_FAILURES (${STABILITY_MAX_FAILURES})."
  exit 1
fi

echo "[BL-18.1] PASS: fail_count (${fail_count}) <= STABILITY_MAX_FAILURES (${STABILITY_MAX_FAILURES})."
