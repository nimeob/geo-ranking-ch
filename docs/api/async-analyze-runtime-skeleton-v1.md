# Async Analyze Runtime Skeleton v1

Stand: 2026-03-01  
Issue: #592 (Parent #588)

## Ziel

Erste lauffähige Runtime-Basis für persistente Async-Jobs inkl. Status-/Result-Read-API,
ohne bereits die vollständige Worker-Pipeline umzusetzen.

## Implementierter Scope

- Persistenter File-Store `src/api/async_jobs.py` (Schema-Version + atomische Writes)
- Job-Events (`job.queued`, `job.running`, `job.completed`) inkl. monotonic `event_seq`
- Additiver Async-Request-Pfad über `options.async_mode.requested`
- Neue Read-Endpunkte:
  - `GET /analyze/jobs/{job_id}`
  - `GET /analyze/results/{result_id}`
- SQL-Basis-Schema als Migrationsentwurf in `docs/sql/async_jobs_schema_v1.sql`

## Persistenzpfad

- Default Store-Datei: `runtime/async_jobs/store.v1.json`
- Override via ENV: `ASYNC_JOBS_STORE_FILE`
- Store-Inhalt (v1):
  - `schema_version`
  - `jobs`
  - `events`
  - `results`

## API-Verhalten (Skeleton)

### `POST /analyze` (additiv)

Wenn `options.async_mode.requested=true` gesetzt ist:

- Job wird erstellt (`queued -> running -> completed` im Skeleton-Pfad)
- finaler Result-Stub wird persistiert
- Antwort: `202 Accepted` mit `job`-Statusobjekt (`job_id`, `status`, `progress_percent`, `result_id`, Zeiten)

Ohne Async-Option bleibt der bestehende Sync-Pfad unverändert.

### `GET /analyze/jobs/{job_id}`

- `200` mit Job-Status + Event-Liste bei vorhandenem Job
- `404 not_found` bei unbekannter `job_id`

### `GET /analyze/results/{result_id}`

- `200` mit persistiertem Result-Payload bei vorhandenem Result
- `404 not_found` bei unbekannter `result_id`

## State-Transition-Guardrails (v1)

Erlaubte Übergänge:

- `queued -> running|canceled`
- `running -> partial|completed|failed|canceled`
- `partial -> partial|completed|failed|canceled`

Terminale States (`completed|failed|canceled`) sind unveränderlich.
`progress_percent` ist monotonic und auf `0..100` begrenzt.

## Offene Punkte für #593

- echte Queue-/Worker-Ausführung statt skeleton completion path
- Partial-Result-Erzeugung über reale Chunk-Läufe
- robustere Cancel-/Failure-Laufzeitpfade unter Last
