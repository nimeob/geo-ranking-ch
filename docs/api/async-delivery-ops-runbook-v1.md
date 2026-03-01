> **Diese Datei wurde archiviert.** Inhalt jetzt in [async-v1.md](async-v1.md)

---

# Async Delivery Ops-Runbook v1

Stand: 2026-03-01  
Issue: #602 (Parent #594)

## Ziel

Produktionsnahe Operate-/Diagnose-Anleitung für die drei ausgelieferten Async-Delivery-Bausteine:

1. Result-Permalink (`GET /analyze/results/{result_id}`)
2. Retention-Cleanup (`cleanup_retention`, `scripts/run_async_retention_cleanup.py`)
3. In-App-Notifications (`GET /analyze/jobs/{job_id}/notifications`)

Das Runbook fokussiert auf reproduzierbare Checks, minimale Betriebsmetriken und klare Alert-Hinweise.

## Voraussetzungen

- API erreichbar (`/health`)
- gültiger Tenant-Kontext (`X-Org-Id` oder `X-Tenant-Id`)
- Zugang zu einem existierenden `job_id`/`result_id` aus einem aktuellen Async-Lauf
- Python-Umgebung für Cleanup-Script vorhanden

Beispiel-Umgebungsvariablen:

```bash
export BASE_URL="http://127.0.0.1:8080"
export ORG_ID="default-org"
export JOB_ID="<job-id>"
export RESULT_ID="<result-id>"
```

## Operate-/Diagnose-Schritte (reproduzierbar)

### 1) Result-Permalink prüfen

```bash
curl -fsS \
  -H "X-Org-Id: ${ORG_ID}" \
  "${BASE_URL}/analyze/results/${RESULT_ID}?view=latest"
```

Erwartung:

- HTTP `200`
- Response enthält `result_id`, `requested_result_id`, `projection_mode`
- bei Tenant-Mismatch bewusst `404` (kein Daten-Leak)

### 2) Job-Status + Notification-Read prüfen

```bash
curl -fsS -H "X-Org-Id: ${ORG_ID}" \
  "${BASE_URL}/analyze/jobs/${JOB_ID}"

curl -fsS -H "X-Org-Id: ${ORG_ID}" \
  "${BASE_URL}/analyze/jobs/${JOB_ID}/notifications?channel=in_app&limit=20"
```

Erwartung:

- Status-Endpunkt liefert konsistente `status`-/`result_id`-Information
- Notification-Endpunkt liefert `notifications` latest-first
- für terminale Jobs (`completed|failed`) mindestens ein Notification-Event vorhanden

### 3) Retention Dry-Run (vor produktivem Cleanup)

```bash
./scripts/run_async_retention_cleanup.py \
  --store-file runtime/async_jobs/store.v1.json \
  --results-ttl-seconds 604800 \
  --events-ttl-seconds 259200 \
  --dry-run \
  --output-json artifacts/async/retention-dry-run.json
```

Erwartung:

- Script-Exit `0`
- JSON-Artefakt enthält `terminal_job_count`, `results.delete_count`, `events.delete_count`
- keine Store-Mutation im Dry-Run

### 4) Produktiver Cleanup

```bash
./scripts/run_async_retention_cleanup.py \
  --store-file runtime/async_jobs/store.v1.json \
  --results-ttl-seconds 604800 \
  --events-ttl-seconds 259200 \
  --output-json artifacts/async/retention-live.json
```

Erwartung:

- Script-Exit `0`
- Retention greift ausschließlich für terminale Jobs (`completed|failed|canceled`)
- wiederholte Ausführung ist idempotent (zweiter Lauf: `delete_count` typischerweise `0` ohne neue Altdaten)

## Monitoring-Mindestmetriken + Alert-Hinweise

| Signal | Quelle | Mindest-Schwelle | Alert-Hinweis |
|---|---|---|---|
| `async_result_permalink_http_5xx_rate_5m` | API-Zugriffslogs auf `/analyze/results/*` | **Warnung** bei `>1%` in 5m, **kritisch** bei `>5%` in 5m | Fehlerbild eingrenzen: Tenant-Header-Validierung, Store-Lesezugriff, letzte Deploy-Änderung |
| `async_result_permalink_p95_ms_15m` | API-Latenz aus Access-Logs/APM | **Warnung** bei `>1200ms`, **kritisch** bei `>2500ms` | Prüfen: IO-Latenz Store, eventuelle Lock-Contention, Host-Last |
| `async_retention_cleanup_exit_code` | Cron/Runner-Status von `run_async_retention_cleanup.py` | Muss `0` sein | Bei `!=0`: Cleanup pausieren, letzte stderr-Ausgabe + Artefakt prüfen |
| `async_retention_results_delete_count` / `async_retention_events_delete_count` | JSON-Ausgabe `retention-*.json` | Trendbeobachtung; Alert bei dauerhaft `0` trotz wachsendem Datenbestand **oder** ungewöhnlichem Spike (`>3x` 7d-Median) | TTL-/Zeitquellen und Datenqualität (`skipped_missing_timestamp`) prüfen |
| `async_notifications_terminal_jobs_without_in_app_10m` | Vergleich `jobs` (terminal) vs. `/notifications` | Soll `0` sein; Warnung bei `>0` über 10m | Prüfen: Notification-Erzeugung (`async.job.completed`/`async.job.failed`), Dedupe-Key-Kollisionen, Lesepfad |

## Smoke-Checkliste Staging

1. `/health` liefert `200`.
2. Mindestens einen Async-Job bis terminalen Zustand laufen lassen.
3. `GET /analyze/jobs/{job_id}` liefert `result_id`.
4. `GET /analyze/results/{result_id}?view=latest` liefert `200` + `projection_mode`.
5. `GET /analyze/jobs/{job_id}/notifications?channel=in_app` liefert terminales Notification-Event.
6. Retention-Dry-Run ausführen; Artefakt mit `delete_count`/`kept_count` prüfen.
7. Optional produktiven Cleanup einmal ausführen und idempotenten Zweitlauf dokumentieren.

## Smoke-Checkliste Prod

1. Vorherige Staging-Checkliste vollständig grün.
2. Read-only Smoke auf aktuellem Prod-Job (`status`, `result`, `notifications`) mit Tenant-Header.
3. Retention zuerst als Dry-Run mit Artefakt in `artifacts/async/`.
4. Produktiven Cleanup nur in freigegebenem Wartungsfenster/Slot starten.
5. Direkt nach Cleanup:
   - API-Health prüfen
   - `async_result_permalink_http_5xx_rate_5m` prüfen
   - Cleanup-Artefakt auf Plausibilität (`delete_count`, `skipped_missing_timestamp`) prüfen
6. Bei Abweichung: Cleanup-Intervall pausieren, Incident-Ticket eröffnen, letzte erfolgreiche Artefakte anhängen.

## Incident-Triage (Kurzablauf)

1. Fehlerklasse bestimmen: Result-Read, Notification-Read oder Retention-Job.
2. Letzte erfolgreiche/fehlgeschlagene Artefakte vergleichen (`artifacts/async/*`).
3. Tenant-/Header-Eingaben validieren (`X-Org-Id`, `X-Tenant-Id`).
4. Bei Persistenzproblemen Store-Datei und letzte Deploy-Änderungen prüfen.
5. Status im zugehörigen Issue/Incident dokumentieren inkl. konkreter Next Step.

## Nachweis / Regression

- `tests/test_async_delivery_ops_runbook_docs.py` (Pflichtmarker + Smoke-Checklisten)
- `tests/test_async_retention_cleanup_docs.py` (Retention-Doku)
- `tests/test_async_in_app_notifications_docs.py` (Notification-Doku)
- `tests/test_async_result_permalink_tenant_guard_docs.py` (Result-Permalink-Doku)
