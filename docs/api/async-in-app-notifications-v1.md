# Async In-App Notification Pipeline v1

- Issue: #601 (Parent #594)
- Stand: 2026-03-01
- Status: umgesetzt

## Ziel

Für terminale Async-Analyze-Jobs (`completed|failed`) wird im File-Store ein
job-bezogener Notification-Record erzeugt, damit Clients den Abschlusszustand
über einen additiven API-Lesepfad abrufen können.

## Datenmodell im Async-Store

Implementiert in `src/api/async_jobs.py` unter `state.notifications`.

Pro Record:

- `notification_id`
- `job_id`
- `channel` (`in_app`)
- `template_key` (`async.job.completed` oder `async.job.failed`)
- `delivery_status` (`pending`)
- `attempt_count`
- `last_error`
- `dedupe_key`
- `scheduled_at`
- `sent_at`
- `created_at`
- `payload_json`

### Payload-Mindestfelder (`payload_json`)

- `job_id`
- `status`
- `result_id`
- `progress_percent`
- `error_code`
- `retry_hint`
- `finished_at`

## Lifecycle

1. Transition `running|partial -> completed` erzeugt genau einen
   `async.job.completed` Notification-Record.
2. Transition `running|partial -> failed` erzeugt genau einen
   `async.job.failed` Notification-Record.
3. Deduplizierung erfolgt über `dedupe_key` (`<job_id>:in_app:<template_key>`),
   sodass wiederholte Transition-Versuche keinen zweiten Record erzeugen.
4. Der API-Lesepfad liefert Notifications read-only aus (kein Zustandswechsel im Endpoint).

## API-Lesepfad (additiv)

### `GET /analyze/jobs/{job_id}/notifications`

Query-Parameter:

- `channel` (optional): `in_app|email|webhook`
- `limit` (optional, default `50`, max `200`)

Response:

- `ok`
- `job_id`
- `channel`
- `limit`
- `notifications` (latest-first)
- `request_id`

Guardrails:

- Tenant-Scope identisch zu `GET /analyze/jobs/{job_id}` via `X-Org-Id`/`X-Tenant-Id`
- unbekannte `job_id` oder Cross-Tenant-Zugriff => `404 not_found`
- ungültige Query-Parameter (`channel`, `limit`) => `400 bad_request`

## Tests

- `tests/test_async_jobs_runtime_skeleton.py`
  - E2E: Completed/Failed erzeugen in_app-Notifications
  - Tenant-Guard auf Notification-Endpoint
  - Query-Parameter-Validierung (`channel`, `limit`)
- Store-level: deduplizierbare Terminal-Notifications via `AsyncJobStore.list_notifications(...)`
