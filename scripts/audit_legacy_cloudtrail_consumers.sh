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

out_path = sys.argv[1]
page_path = sys.argv[2]

with open(page_path, "r", encoding="utf-8") as f:
    page = json.load(f)

events = page.get("Events", [])
with open(out_path, "a", encoding="utf-8") as out:
    for event in events:
        raw = event.get("CloudTrailEvent")
        detail = {}
        if isinstance(raw, str) and raw:
            try:
                detail = json.loads(raw)
            except Exception:
                detail = {}

        recipient = detail.get("recipientAccountId") or detail.get("userIdentity", {}).get("accountId")
        source_ip = detail.get("sourceIPAddress") or "unknown"
        user_agent = detail.get("userAgent") or "unknown"
        event_source = detail.get("eventSource") or event.get("EventSource") or "unknown"

        rec = {
            "event_time": event.get("EventTime") or detail.get("eventTime"),
            "event_name": event.get("EventName") or detail.get("eventName") or "unknown",
            "event_source": event_source,
            "source_ip": source_ip,
            "user_agent": user_agent,
            "recipient_account": recipient or "unknown",
            "username": event.get("Username") or detail.get("userIdentity", {}).get("userName") or "unknown",
        }
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(page.get("NextToken") or "")
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

echo "=== Legacy CloudTrail Consumer Fingerprint Audit (read-only) ==="
echo "Repo:          $ROOT_DIR"
echo "Legacy user:   $LEGACY_USER"
echo "Region:        $REGION"
echo "Zeitfenster:   ${start_time} .. ${end_time} (UTC, ${LOOKBACK_HOURS}h)"
echo "Seiten gelesen: $pages"
echo "LookupEvents in Auswertung: $([[ "$INCLUDE_LOOKUP_EVENTS" == "1" ]] && echo "inkludiert" || echo "exkludiert")"
echo

summary_status="$({
  START_TIME="$start_time" \
  END_TIME="$end_time" \
  LOOKBACK_HOURS="$LOOKBACK_HOURS" \
  REGION="$REGION" \
  LEGACY_USER="$LEGACY_USER" \
  INCLUDE_LOOKUP_EVENTS="$INCLUDE_LOOKUP_EVENTS" \
  MAX_RESULTS="$MAX_RESULTS" \
  MAX_PAGES="$MAX_PAGES" \
  READ_PAGES="$pages" \
  FINGERPRINT_REPORT_JSON="$FINGERPRINT_REPORT_JSON" \
  python3 - "$tmp_events" <<'PY'
import collections
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
report_path = Path(os.environ["FINGERPRINT_REPORT_JSON"])
if not report_path.is_absolute():
    report_path = Path.cwd() / report_path


def parse_ts(value: str):
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def normalize_ts(value: str) -> str:
    parsed = parse_ts(value)
    if parsed is None:
        return "unknown"
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


records = []
with path.open("r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except Exception:
            pass

raw_count = len(records)
include_lookup_events = os.environ.get("INCLUDE_LOOKUP_EVENTS", "0") == "1"
if include_lookup_events:
    analyzed = list(records)
else:
    analyzed = [
        rec
        for rec in records
        if not (
            (rec.get("event_source") or "") == "cloudtrail.amazonaws.com"
            and (rec.get("event_name") or "") == "LookupEvents"
        )
    ]

filtered_lookup_count = raw_count - len(analyzed)
records_sorted = sorted(
    analyzed,
    key=lambda r: parse_ts(r.get("event_time") or "") or datetime.min,
    reverse=True,
)

combo = collections.defaultdict(
    lambda: {
        "count": 0,
        "latest": None,
        "event_sources": set(),
        "event_names": set(),
    }
)

for rec in records_sorted:
    key = (rec.get("source_ip", "unknown"), rec.get("user_agent", "unknown"))
    entry = combo[key]
    entry["count"] += 1
    entry["event_sources"].add(rec.get("event_source", "unknown"))
    entry["event_names"].add(rec.get("event_name", "unknown"))

    ts = parse_ts(rec.get("event_time") or "")
    if ts is not None and (entry["latest"] is None or ts > entry["latest"]):
        entry["latest"] = ts

ranked = sorted(combo.items(), key=lambda item: item[1]["count"], reverse=True)[:10]
top_fingerprints = []
for idx, ((source_ip, user_agent), data) in enumerate(ranked, start=1):
    latest = data["latest"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if data["latest"] else "unknown"
    top_fingerprints.append(
        {
            "rank": idx,
            "source_ip": source_ip,
            "user_agent": user_agent,
            "event_count": data["count"],
            "latest_event_time": latest,
            "event_sources": sorted(data["event_sources"]),
            "event_names": sorted(data["event_names"]),
        }
    )

recent_events = [
    {
        "event_time": rec.get("event_time") or "unknown",
        "event_source": rec.get("event_source") or "unknown",
        "event_name": rec.get("event_name") or "unknown",
        "source_ip": rec.get("source_ip") or "unknown",
        "user_agent": rec.get("user_agent") or "unknown",
        "recipient_account": rec.get("recipient_account") or "unknown",
        "username": rec.get("username") or "unknown",
    }
    for rec in records_sorted[:10]
]

status = "found_events" if records_sorted else "no_events"
report = {
    "summary": "Legacy CloudTrail Consumer Fingerprint Audit (read-only)",
    "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "window_utc": {
        "start": os.environ.get("START_TIME"),
        "end": os.environ.get("END_TIME"),
        "lookback_hours": int(os.environ.get("LOOKBACK_HOURS", "0")),
    },
    "config": {
        "legacy_user": os.environ.get("LEGACY_USER"),
        "region": os.environ.get("REGION"),
        "max_results": int(os.environ.get("MAX_RESULTS", "0")),
        "max_pages": int(os.environ.get("MAX_PAGES", "0")),
        "pages_read": int(os.environ.get("READ_PAGES", "0")),
        "include_lookup_events": include_lookup_events,
    },
    "counts": {
        "events_raw": raw_count,
        "events_analyzed": len(records_sorted),
        "lookup_events_filtered": filtered_lookup_count,
    },
    "top_fingerprints": top_fingerprints,
    "latest_events": recent_events,
    "status": status,
    "expected_exit_code": 10 if status == "found_events" else 0,
}

report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if not records_sorted:
    if raw_count and not include_lookup_events:
        print(f"Events im Fenster (raw): {raw_count}")
        print("Events in Auswertung: 0 (nach Filter)")
    print("__NO_EVENTS__")
    sys.exit(0)

print(f"Events im Fenster (raw): {raw_count}")
print(f"Events in Auswertung: {len(records_sorted)}")
print()
print("Top Fingerprints (source_ip + user_agent):")
for fp in top_fingerprints:
    print(f"{fp['rank']:>2}. count={fp['event_count']:<3} latest={fp['latest_event_time']}")
    print(f"    source_ip={fp['source_ip']}")
    print(f"    user_agent={fp['user_agent']}")
    print(f"    event_sources={','.join(fp['event_sources'])}")
    print(f"    event_names={','.join(fp['event_names'])}")

print()
print("Letzte 10 Events:")
for rec in recent_events:
    print(
        "- {event_time} | {event_source}:{event_name} | ip={source_ip} | ua={user_agent}".format(
            event_time=normalize_ts(rec["event_time"]),
            event_source=rec["event_source"],
            event_name=rec["event_name"],
            source_ip=rec["source_ip"],
            user_agent=rec["user_agent"],
        )
    )

print("__FOUND_EVENTS__")
PY
})"

if [[ "$summary_status" == *"__NO_EVENTS__"* ]]; then
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
