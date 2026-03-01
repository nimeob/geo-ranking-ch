# BL-30.3.wp2.r2 — Deep-Mode Trace-Evidence Runbook

Stand: 2026-03-01

## Ziel

Reproduzierbar nachweisen, dass Deep-Mode-Telemetrie im `/analyze`-Flow die Pflicht-Events und Pflichtfelder liefert.

## Pflicht-Events

- `api.deep_mode.gate_evaluated`
- `api.deep_mode.execution.start`
- `api.deep_mode.execution.retry`
- `api.deep_mode.execution.abort`
- `api.deep_mode.execution.end`

## Pflichtfelder

- Envelope: `ts`, `level`, `event`, `trace_id`, `request_id`, `session_id`
- Deep-Mode: `deep_requested`, `deep_effective`, `deep_profile`
- Budget: `deep_budget_ms`, `deep_budget_tokens_effective`
- Lifecycle: `retry_count`
- Optional je nach Event: `fallback_reason`, `duration_ms`

## Schnellcheck (Regression)

```bash
./.venv-test/bin/python -m pytest -q tests/test_bl30_deep_mode_telemetry_events.py
```

Erwartung: `3 passed`.

## Beispiel-Evidence (Repository)

- JSONL-Beispiel mit Success- + Abort-Flow:
  `docs/testing/deep-mode-trace-evidence-sample.jsonl`

Enthält alle Pflicht-Events inklusive Retry-Fall (`retry_count=1`) und Abort-Fall (`fallback_reason=not_entitled`).

## Operative Interpretation

1. **Gate-Event prüfen**: zeigt, ob Anfrage Deep-Mode wollte und ob Gate erfolgreich war.
2. **Execution-Events prüfen**:
   - `start`/`end` bei erfolgreichem Deep-Lauf
   - `abort` bei Fallback ohne Deep-Ausführung
   - `retry` nur falls ein Retry stattfindet
3. **Korrelation sicherstellen**: `request_id` muss in allen Deep-Events eines Flows identisch sein.
4. **Fehlerursache lesen**: bei `abort` ist `fallback_reason` verpflichtend gesetzt.

## Referenzen

- Logging-Schema: `docs/LOGGING_SCHEMA_V1.md`
- Orchestrierungs-Design: `docs/api/deep-mode-orchestration-guardrails-v1.md`
- Runtime-Implementierung: `src/api/web_service.py`
