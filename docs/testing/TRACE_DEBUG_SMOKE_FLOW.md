# BL-422.4 — Trace-Debug E2E/Smoke (Analyze → request_id → Trace-View)

## Zweck
Reproduzierbarer Smoke-Nachweis für den End-to-End-Debug-Flow:

1. Analyze-Request erzeugt/echoed eine `request_id`
2. dieselbe `request_id` wird in der GUI als Debug-Einstieg verwendet
3. `GET /debug/trace` liefert die Timeline (`api.request.start` / `api.request.end` + ggf. Upstream-Events)

## Automatisierter Smoke-Test

```bash
pytest -q tests/test_trace_debug_smoke.py
```

Der Test startet lokal `src.web_service` mit:

- `TRACE_DEBUG_ENABLED=1`
- `TRACE_DEBUG_LOG_PATH=<temp>/structured-events.jsonl`

und validiert anschließend:

- Analyze-Response enthält die erwartete `request_id`
- Trace-Lookup für dieselbe ID ist `ok=true` / `state=ready`
- Timeline enthält mindestens `api.request.start` und `api.request.end`
- kein Secret-Leak des verwendeten Bearer-Strings im Trace-Payload

## Manueller Kurz-Flow

1. Service mit Trace-Debug-ENV starten:
   - `TRACE_DEBUG_ENABLED=1`
   - `TRACE_DEBUG_LOG_PATH=/pfad/zu/structured-events.jsonl`
2. In der GUI (`/gui`) eine Analyse auslösen
3. Im Result-Panel `Trace ansehen` klicken (oder `Copy ID` + Deep-Link nutzen)
4. Erwartung:
   - Trace-Panel zeigt `loading -> success|unknown|error`
   - Timeline chronologisch dargestellt
   - Unknown/Empty States verständlich erklärt

## Bekannte Limits

- Zeitfenster-Grenze über `lookback_seconds` (Default siehe API-ENV)
- Event-Limit über `max_events` (serverseitig begrenzt)
- `state=empty`/`reason=request_id_outside_window` bei zu alten Events
- `state=empty`/`reason=request_id_unknown_or_no_events` bei unbekannter oder noch nicht geloggter ID

## Security / Redaction

- Trace-API bleibt dev-only (`TRACE_DEBUG_ENABLED` Gate)
- Timeline basiert auf redacted structured logs (keine Klartext-Secrets/PII)
- GUI zeigt nur das bereits redacted Payload aus dem Trace-Endpoint

## Referenzen

- API: [`docs/testing/TRACE_DEBUG_API.md`](TRACE_DEBUG_API.md)
- GUI-Stateflow: [`docs/gui/GUI_MVP_STATE_FLOW.md`](../gui/GUI_MVP_STATE_FLOW.md)
- Smoke-Test: [`tests/test_trace_debug_smoke.py`](../../tests/test_trace_debug_smoke.py)
