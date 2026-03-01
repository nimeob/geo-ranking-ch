# BL-340.4 — Upstream Trace Evidence

Stand: 2026-03-01

## Ziel

Nachvollziehbare Trace-Nachweise für API→Upstream-Logging mit Erfolg- und Fehlerpfad.

## Artefakte

- Erfolgspfad (Request + End + Summary):
  - `artifacts/bl340/20260301T011200Z-upstream-trace-success.jsonl`
- Fehlerpfad (Retry + Final Error):
  - `artifacts/bl340/20260301T011215Z-upstream-trace-failure.jsonl`

## Erwartete Event-Kette

### Success

1. `api.upstream.request.start`
2. `api.upstream.request.end` (`status=ok`)
3. `api.upstream.response.summary` (`status=ok`, `records>0`)

### Failure

1. `api.upstream.request.start`
2. `api.upstream.request.end` (`status=retrying`, `error_class=http_error`)
3. `api.upstream.request.end` (`status=error`, finaler Fehlversuch)

## Reproduzierbare Checks

```bash
pytest -q tests/test_address_intel_upstream_logging.py tests/test_web_service_request_logging.py
```

Die Tests validieren insbesondere:
- Presence der neuen Events `api.upstream.request.start|end|response.summary`
- Retry-/Error-Klassifikation (`retrying`, `error_class`)
- Durchreichung von `request_id`/`session_id` aus dem API-Request-Kontext
