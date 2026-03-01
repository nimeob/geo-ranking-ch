# Async Retention Cleanup v1

Stand: 2026-03-01  
Issue: #600 (Parent #594)

## Ziel

Technische Retention für `job_results` und `job_events` bereitstellen, damit der
file-basierte Async-Store (`runtime/async_jobs/store.v1.json`) nicht unbegrenzt wächst.

## Implementierter Scope

- Store-seitiger Cleanup-Mechanismus in `src/api/async_jobs.py` (`cleanup_retention(...)`)
- Konfigurierbare TTLs getrennt für:
  - `job_results`
  - `job_events`
- Sicherheitsregel: Cleanup löscht **nur** für terminale Jobs (`completed|failed|canceled`)
- Idempotente Ausführung mit nachvollziehbaren Metriken (`delete_count`, `kept_count`, `eligible_terminal`)
- Betriebs-Skript für periodische Läufe: `scripts/run_async_retention_cleanup.py`

## Konfiguration

- `ASYNC_JOB_RESULTS_RETENTION_SECONDS` (default: `604800` = 7 Tage)
- `ASYNC_JOB_EVENTS_RETENTION_SECONDS` (default: `259200` = 3 Tage)
- `ASYNC_JOBS_STORE_FILE` (optional, Default: `runtime/async_jobs/store.v1.json`)

## Script Usage

### Dry-Run (empfohlen vor erstem produktiven Lauf)

```bash
./scripts/run_async_retention_cleanup.py \
  --store-file runtime/async_jobs/store.v1.json \
  --results-ttl-seconds 604800 \
  --events-ttl-seconds 259200 \
  --dry-run
```

### Produktiver Lauf mit JSON-Artefakt

```bash
./scripts/run_async_retention_cleanup.py \
  --store-file runtime/async_jobs/store.v1.json \
  --results-ttl-seconds 604800 \
  --events-ttl-seconds 259200 \
  --output-json artifacts/async/retention-latest.json
```

### Optionales Cron-Beispiel

```cron
*/30 * * * * cd /path/to/repo && ./scripts/run_async_retention_cleanup.py --output-json artifacts/async/retention-cron.json
```

## Betriebs-/Sicherheitsnotizen

- Einträge ohne validen Timestamp werden nicht gelöscht (sicherheitsorientiert).
- Läufe sind idempotent; ein zweiter Lauf ohne neue Alt-Daten führt zu `delete_count=0`.
- Bei `--dry-run` werden keine Persistenzänderungen geschrieben.

## Test-/Nachweis

- `tests/test_async_jobs_runtime_skeleton.py` (Retention-Grenzfälle + Idempotenz + Dry-Run)
- `tests/test_run_async_retention_cleanup.py` (Script-Ausführung und terminal-only Cleanup)
