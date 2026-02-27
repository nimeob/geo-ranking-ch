#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

LEGACY_USER="${LEGACY_USER:-swisstopo-api-deploy}"
LOOKBACK_HOURS="${LOOKBACK_HOURS:-6}"
REGION="${AWS_REGION:-eu-central-1}"
MAX_RESULTS="${MAX_RESULTS:-50}"
MAX_PAGES="${MAX_PAGES:-20}"
INCLUDE_LOOKUP_EVENTS="${INCLUDE_LOOKUP_EVENTS:-0}"
FINGERPRINT_INCLUDE_REGION="${FINGERPRINT_INCLUDE_REGION:-0}"
FINGERPRINT_INCLUDE_ACCOUNT="${FINGERPRINT_INCLUDE_ACCOUNT:-0}"
FINGERPRINT_REPORT_JSON_RAW="${FINGERPRINT_REPORT_JSON:-artifacts/bl15/legacy-cloudtrail-fingerprint-report.json}"
FINGERPRINT_REPORT_JSON="$(printf '%s' "$FINGERPRINT_REPORT_JSON_RAW" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

if ! [[ "$LOOKBACK_HOURS" =~ ^[0-9]+$ ]] || [[ "$LOOKBACK_HOURS" -lt 1 ]]; then
  echo "ERROR: LOOKBACK_HOURS muss eine positive Ganzzahl sein (aktuell: $LOOKBACK_HOURS)." >&2
  exit 20
fi

if ! [[ "$MAX_RESULTS" =~ ^[0-9]+$ ]] || [[ "$MAX_RESULTS" -lt 1 ]] || [[ "$MAX_RESULTS" -gt 50 ]]; then
  echo "ERROR: MAX_RESULTS muss zwischen 1 und 50 liegen (aktuell: $MAX_RESULTS)." >&2
  exit 20
fi

if ! [[ "$MAX_PAGES" =~ ^[0-9]+$ ]] || [[ "$MAX_PAGES" -lt 1 ]]; then
  echo "ERROR: MAX_PAGES muss eine positive Ganzzahl sein (aktuell: $MAX_PAGES)." >&2
  exit 20
fi

if [[ "$INCLUDE_LOOKUP_EVENTS" != "0" && "$INCLUDE_LOOKUP_EVENTS" != "1" ]]; then
  echo "ERROR: INCLUDE_LOOKUP_EVENTS muss 0 oder 1 sein (aktuell: $INCLUDE_LOOKUP_EVENTS)." >&2
  exit 20
fi

if [[ "$FINGERPRINT_INCLUDE_REGION" != "0" && "$FINGERPRINT_INCLUDE_REGION" != "1" ]]; then
  echo "ERROR: FINGERPRINT_INCLUDE_REGION muss 0 oder 1 sein (aktuell: $FINGERPRINT_INCLUDE_REGION)." >&2
  exit 20
fi

if [[ "$FINGERPRINT_INCLUDE_ACCOUNT" != "0" && "$FINGERPRINT_INCLUDE_ACCOUNT" != "1" ]]; then
  echo "ERROR: FINGERPRINT_INCLUDE_ACCOUNT muss 0 oder 1 sein (aktuell: $FINGERPRINT_INCLUDE_ACCOUNT)." >&2
  exit 20
fi

if [[ -z "$FINGERPRINT_REPORT_JSON" ]]; then
  echo "ERROR: FINGERPRINT_REPORT_JSON darf nicht leer sein." >&2
  exit 20
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "ERROR: aws CLI nicht gefunden." >&2
  exit 20
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 nicht gefunden." >&2
  exit 20
fi

start_time="$(date -u -d "-${LOOKBACK_HOURS} hour" +"%Y-%m-%dT%H:%M:%SZ")"
end_time="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

tmp_events="$(mktemp)"
tmp_page="$(mktemp)"
trap 'rm -f "$tmp_events" "$tmp_page"' EXIT

pages=0
next_token=""

while :; do
  pages=$((pages + 1))

  args=(
    cloudtrail
    lookup-events
    --region "$REGION"
    --lookup-attributes "AttributeKey=Username,AttributeValue=${LEGACY_USER}"
    --start-time "$start_time"
    --end-time "$end_time"
    --max-results "$MAX_RESULTS"
    --output json
  )

  if [[ -n "$next_token" ]]; then
    args+=(--next-token "$next_token")
  fi

  if ! page_json="$(aws "${args[@]}" 2>/dev/null)"; then
    echo "ERROR: CloudTrail lookup-events fehlgeschlagen (Region=${REGION})." >&2
    echo "Hinweis: Prüfe Berechtigung cloudtrail:LookupEvents und gültige AWS-Credentials." >&2
    exit 20
  fi

  printf '%s' "$page_json" >"$tmp_page"

  next_token="$(python3 - "$tmp_events" "$tmp_page" <<'PY'
import json
import sys
from pathlib import Path

from src.legacy_consumer_fingerprint import extract_records_from_lookup_page

out_path = Path(sys.argv[1])
page_path = Path(sys.argv[2])

try:
    page = json.loads(page_path.read_text(encoding="utf-8"))
except json.JSONDecodeError:
    page = {}

if not isinstance(page, dict):
    page = {}

records, next_token = extract_records_from_lookup_page(page)
with out_path.open("a", encoding="utf-8") as handle:
    for record in records:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

print(next_token)
PY
  )"

  if [[ -z "$next_token" ]]; then
    break
  fi

  if [[ "$pages" -ge "$MAX_PAGES" ]]; then
    echo "WARN: Pagination-Limit MAX_PAGES=${MAX_PAGES} erreicht; Auswertung ist ggf. unvollständig." >&2
    break
  fi
done

dimension_suffix=""
if [[ "$FINGERPRINT_INCLUDE_REGION" == "1" ]]; then
  dimension_suffix+=" + region"
fi
if [[ "$FINGERPRINT_INCLUDE_ACCOUNT" == "1" ]]; then
  dimension_suffix+=" + recipient_account"
fi

echo "=== Legacy CloudTrail Consumer Fingerprint Audit (read-only) ==="
echo "Repo:          $ROOT_DIR"
echo "Legacy user:   $LEGACY_USER"
echo "Region:        $REGION"
echo "Zeitfenster:   ${start_time} .. ${end_time} (UTC, ${LOOKBACK_HOURS}h)"
echo "Seiten gelesen: $pages"
echo "LookupEvents in Auswertung: $([[ "$INCLUDE_LOOKUP_EVENTS" == "1" ]] && echo "inkludiert" || echo "exkludiert")"
echo "Fingerprint-Dimensionen: source_ip + user_agent${dimension_suffix}"
echo

summary_status="$(
  START_TIME="$start_time" \
  END_TIME="$end_time" \
  LOOKBACK_HOURS="$LOOKBACK_HOURS" \
  REGION="$REGION" \
  LEGACY_USER="$LEGACY_USER" \
  INCLUDE_LOOKUP_EVENTS="$INCLUDE_LOOKUP_EVENTS" \
  FINGERPRINT_INCLUDE_REGION="$FINGERPRINT_INCLUDE_REGION" \
  FINGERPRINT_INCLUDE_ACCOUNT="$FINGERPRINT_INCLUDE_ACCOUNT" \
  MAX_RESULTS="$MAX_RESULTS" \
  MAX_PAGES="$MAX_PAGES" \
  READ_PAGES="$pages" \
  FINGERPRINT_REPORT_JSON="$FINGERPRINT_REPORT_JSON" \
  python3 - "$tmp_events" <<'PY'
import os
import sys
from pathlib import Path

from src.legacy_consumer_fingerprint import (
    build_fingerprint_report,
    load_ndjson_records,
    render_report_lines,
    write_report,
)

records_path = Path(sys.argv[1])
report_path = Path(os.environ["FINGERPRINT_REPORT_JSON"])
if not report_path.is_absolute():
    report_path = Path.cwd() / report_path

records, invalid_lines = load_ndjson_records(records_path)
report = build_fingerprint_report(
    records,
    start_time=os.environ.get("START_TIME", ""),
    end_time=os.environ.get("END_TIME", ""),
    lookback_hours=int(os.environ.get("LOOKBACK_HOURS", "0")),
    legacy_user=os.environ.get("LEGACY_USER", ""),
    region=os.environ.get("REGION", ""),
    max_results=int(os.environ.get("MAX_RESULTS", "0")),
    max_pages=int(os.environ.get("MAX_PAGES", "0")),
    pages_read=int(os.environ.get("READ_PAGES", "0")),
    include_lookup_events=os.environ.get("INCLUDE_LOOKUP_EVENTS", "0") == "1",
    include_region=os.environ.get("FINGERPRINT_INCLUDE_REGION", "0") == "1",
    include_account=os.environ.get("FINGERPRINT_INCLUDE_ACCOUNT", "0") == "1",
)
if invalid_lines:
    report.setdefault("counts", {})["invalid_ndjson_lines"] = invalid_lines

write_report(report_path, report)
for line in render_report_lines(report):
    print(line)

print("__FOUND_EVENTS__" if report.get("status") == "found_events" else "__NO_EVENTS__")
PY
)"

if [[ "$summary_status" == *"__NO_EVENTS__"* ]]; then
  echo "$summary_status" | sed '/^__NO_EVENTS__$/d;/^__FOUND_EVENTS__$/d'
  echo "Keine Legacy-CloudTrail-Events im gewählten Zeitfenster gefunden."
  echo "Strukturierter Report: $FINGERPRINT_REPORT_JSON"
  echo
  echo "Exit-Code-Interpretation:"
  echo "  0  = kein Legacy-Event im Fenster"
  echo " 10  = Legacy-Events gefunden (Fingerprint-Analyse oben)"
  echo " 20  = Ausführungs-/Berechtigungsfehler"
  exit 0
fi

echo "$summary_status" | sed '/^__FOUND_EVENTS__$/d;/^__NO_EVENTS__$/d'
echo "Strukturierter Report: $FINGERPRINT_REPORT_JSON"
echo
echo "Exit-Code-Interpretation:"
echo "  0  = kein Legacy-Event im Fenster"
echo " 10  = Legacy-Events gefunden (Fingerprint-Analyse oben)"
echo " 20  = Ausführungs-/Berechtigungsfehler"

exit 10
