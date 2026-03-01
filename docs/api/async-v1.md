# Async Analyze — Konsolidierte Dokumentation v1

> Dieses Dokument ist der **kanonische Ort** für alle Async-Analyze-Themen.
> Die Quell-Dokumente bleiben für Test-Kompatibilität erhalten.

Stand: 2026-03-01

**Quell-Dokumente:**
- [`docs/api/async-analyze-domain-design-v1.md`](async-analyze-domain-design-v1.md) — Domain-Design (#587)
- [`docs/api/async-analyze-runtime-skeleton-v1.md`](async-analyze-runtime-skeleton-v1.md) — Runtime-Skeleton (#592)
- [`docs/api/async-analyze-worker-pipeline-v1.md`](async-analyze-worker-pipeline-v1.md) — Worker-Pipeline (#593)
- [`docs/api/async-result-permalink-tenant-guard-v1.md`](async-result-permalink-tenant-guard-v1.md) — Tenant-Guard (#599)
- [`docs/api/async-retention-cleanup-v1.md`](async-retention-cleanup-v1.md) — Retention (#600)
- [`docs/api/async-in-app-notifications-v1.md`](async-in-app-notifications-v1.md) — Notifications (#601)
- [`docs/api/async-delivery-ops-runbook-v1.md`](async-delivery-ops-runbook-v1.md) — Ops-Runbook (#602)

---

## 1) Job-State-Machine (verbindlich v1)

### Kanonische States

| State | Bedeutung | Terminal |
|---|---|---|
| `queued` | Akzeptiert, wartet auf Worker | nein |
| `running` | Verarbeitung aktiv | nein |
| `partial` | Teilresultat verfügbar, Endresultat noch offen | nein |
| `completed` | Finales Resultat persistiert | **ja** |
| `failed` | Terminal fehlgeschlagen | **ja** |
| `canceled` | Bewusst abgebrochen | **ja** |

### Erlaubte Transitionen

| From | → To | Bedingung |
|---|---|---|
| `queued` | `running` | Worker startet |
| `queued` | `canceled` | Nutzer/System bricht ab |
| `running` | `partial` | erstes validiertes Chunk-Resultat |
| `running` | `completed` | endet ohne Teilresultat direkt |
| `running` | `failed` | terminaler Fehler |
| `running` | `canceled` | Nutzer/System bricht ab |
| `partial` | `partial` | weitere Chunks |
| `partial` | `completed` | finale Aggregation |
| `partial` | `failed` | terminaler Fehler |
| `partial` | `canceled` | Nutzer/System bricht ab |

**Nicht erlaubt (v1):** `queued -> completed` ohne `running`; `completed|failed|canceled -> running`.

---

## 2) Datenmodell

### Persistenzpfad
- Default Store: `runtime/async_jobs/store.v1.json`
- Override: `ASYNC_JOBS_STORE_FILE`
- Store-Inhalt (v1): `schema_version`, `jobs`, `events`, `results`, `notifications`

### Job-Record (Pflichtfelder)
`job_id`, `org_id`, `status`, `progress_percent` (monoton, 0..100), `result_id`, `started_at`, `partial_count`, `event_seq`

### Result-Record
`result_id`, `job_id`, `result_kind` (`partial|final`), `result_seq` (monoton, je Job strikt)

### Notification-Record (in-app)
`notification_id`, `job_id`, `channel` (`in_app`), `template_key` (`async.job.completed|failed`),
`delivery_status` (`pending`), `dedupe_key` (`<job_id>:in_app:<template_key>`), `payload_json`

---

## 3) API-Endpunkte

### `POST /analyze` (additiv)
Wenn `options.async_mode.requested=true`:
- Antwortet `202 Accepted` mit `job`-Statusobjekt
- Sync-Pfad bleibt unverändert

### `GET /analyze/jobs/{job_id}`
- `200`: Job-Status + Event-Liste
- `404`: unbekannte `job_id` (oder Tenant-Mismatch)

### `GET /analyze/results/{result_id}`
Query-Parameter:
- `view=latest` (Default): finaler Snapshot, sonst letzter partial
- `view=requested`: exakt der angefragte Snapshot

Response additiv: `requested_result_id`, `requested_result_kind`, `projection_mode`

- `200`: persistierter Result-Payload
- `404`: unbekannte `result_id` (oder Tenant-Mismatch)

### `POST /analyze/jobs/{job_id}/cancel`
- `queued`: direkt auf `canceled`
- `running/partial`: `cancel_requested_at` setzen, Worker terminiert idempotent

### `GET /analyze/jobs/{job_id}/notifications`
- Notifications read-only (kein Zustandswechsel im Endpoint)

---

## 4) Tenant-Guard

- Header: `X-Org-Id` (primär), Alias `X-Tenant-Id`; ohne Header: Fallback auf `default-org`
- Validation: `[A-Za-z0-9_.:-]`, max 128 Zeichen; ungültig → `400`
- Bei Org-Mismatch → `404` (kein Existenz-Leak über fremde Tenant-Daten)
- CORS Allow-Headers: `X-Org-Id`, `X-Tenant-Id`

---

## 5) Retention Cleanup

### Konfiguration
| ENV | Default | Beschreibung |
|---|---|---|
| `ASYNC_JOB_RESULTS_RETENTION_SECONDS` | `604800` (7 Tage) | TTL für `job_results` |
| `ASYNC_JOB_EVENTS_RETENTION_SECONDS` | `259200` (3 Tage) | TTL für `job_events` |

### Cleanup-Script
```bash
# Dry-Run
./scripts/run_async_retention_cleanup.py --dry-run

# Produktiv mit Artefakt
./scripts/run_async_retention_cleanup.py \
  --results-ttl-seconds 604800 \
  --events-ttl-seconds 259200 \
  --output-json artifacts/async/retention-latest.json
```
- Cleanup nur für terminale Jobs (`completed|failed|canceled`)
- Idempotent — zweiter Lauf ohne neue Alt-Daten: `delete_count=0`

---

## 6) Fehlerpfad (deterministisch für E2E/Smoke)

Bei `ENABLE_E2E_FAULT_INJECTION=1`:
- `query == "__timeout__"` → `error_code=timeout`, `retry_hint=retry_with_backoff`
- `query == "__internal__"` → `error_code=internal`, `retry_hint=retry_with_backoff`
- `query == "__address_intel__"` → `error_code=address_intel`, `retry_hint=check_input_and_retry`

---

## 7) Ops-Runbook (Reproduce-Checkliste)

```bash
export BASE_URL="http://127.0.0.1:8080"
export ORG_ID="default-org"
export JOB_ID="<job-id>"
export RESULT_ID="<result-id>"

# Result-Permalink prüfen
curl -fsS -H "X-Org-Id: ${ORG_ID}" \
  "${BASE_URL}/analyze/results/${RESULT_ID}?view=latest"

# Job-Status prüfen
curl -fsS -H "X-Org-Id: ${ORG_ID}" \
  "${BASE_URL}/analyze/jobs/${JOB_ID}"

# Notifications prüfen
curl -fsS -H "X-Org-Id: ${ORG_ID}" \
  "${BASE_URL}/analyze/jobs/${JOB_ID}/notifications"

# Retention Dry-Run
./scripts/run_async_retention_cleanup.py \
  --store-file runtime/async_jobs/store.v1.json --dry-run
```

Vollständiges Ops-Runbook: [`docs/api/async-delivery-ops-runbook-v1.md`](async-delivery-ops-runbook-v1.md)

---

## 8) Follow-up-Status

- ✅ #587 Domain-Design
- ✅ #592 Runtime-Skeleton
- ✅ #593 Worker-Pipeline
- ✅ #599 Tenant-Guard + Snapshot-Projektion
- ✅ #600 Retention-Cleanup
- ✅ #601 In-App-Notifications
- ✅ #602 Ops-Runbook
- Nächste Tracks: #594 Parent (Result-Page Delivery), #588 MVP→Scale Rollout
