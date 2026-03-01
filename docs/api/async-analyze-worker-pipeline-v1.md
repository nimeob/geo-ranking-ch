# Async Analyze Worker-Pipeline v1

Stand: 2026-03-01  
Issue: #593 (Parent #588)

## Ziel

Nach dem Runtime-Skeleton (#592) wird die worker-ausführung für Async-Jobs
als Queue-/Dispatcher-light ergänzt, inklusive Partial-Snapshots,
deterministischem Fehlerpfad und idempotentem Cancel.

## Implementierter Scope

- Hintergrund-Worker (`src/api/async_worker_runtime.py`) mit serieller Job-Abarbeitung
- Job-Lifecycle: `queued -> running -> partial -> completed`
- Pro Stage persistierte `job_results` mit `result_kind=partial`
- Eventpfad über `job.queued`, `job.running`, `job.partial`, `job.completed`
- Fehlerpfad mit `error_code`, `error_message`, `retryable`, `retry_hint`
- Cancel-API: `POST /analyze/jobs/{job_id}/cancel` (idempotent)

## API-Verhalten

### `POST /analyze` mit `options.async_mode.requested=true`

- erstellt Job in `queued`
- antwortet sofort mit `202 Accepted`
- Worker übernimmt asynchron und schreibt Progress/Eventing in den Store

### `POST /analyze/jobs/{job_id}/cancel`

- queued: Job wird direkt auf `canceled` gesetzt
- running/partial: `cancel_requested_at` wird gesetzt; Worker terminiert den Job auf `canceled`
- idempotent: wiederholte Cancel-Requests bleiben stabil

## Persistenz-/Konsistenzregeln

- `progress_percent` bleibt monoton
- `partial_count` entspricht Anzahl persistierter `result_kind=partial`-Snapshots
- `result_seq` steigt pro Job strikt monoton
- Finalsnapshot (`result_kind=final`) wird genau einmal geschrieben

## Fehlerpfad (deterministisch)

Für E2E-/Smoke-Zwecke (bei `ENABLE_E2E_FAULT_INJECTION=1`):

- `query == "__timeout__"` -> `error_code=timeout`, `retry_hint=retry_with_backoff`
- `query == "__internal__"` -> `error_code=internal`, `retry_hint=retry_with_backoff`
- `query == "__address_intel__"` -> `error_code=address_intel`, `retry_hint=check_input_and_retry`

## Tests / Nachweis

- `tests/test_async_jobs_runtime_skeleton.py`
  - `queued -> partial -> completed`
  - `running -> canceled` inkl. idempotentem Cancel
  - deterministischer `failed`-Pfad inkl. Retry-Hinweis
- `tests/test_async_analyze_runtime_skeleton_docs.py`
  - Marker-Checks für Doku-/Backlog-Sync
