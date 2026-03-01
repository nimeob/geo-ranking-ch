# Request-Trace Debug API (BL-422.1)

## Zweck
Dev-internes, read-only Lookup für strukturierte Request-Timelines per `request_id`.

Endpoint:
- `GET /debug/trace?request_id=<id>[&lookback_seconds=<n>&max_events=<n>]`

## Sicherheits-/Scope-Gates
Der Endpoint ist standardmäßig **deaktiviert** und nur per ENV verfügbar:

- `TRACE_DEBUG_ENABLED=1` aktiviert die Route
- `TRACE_DEBUG_LOG_PATH=/pfad/zu/structured-events.jsonl` definiert die Quelle

Wenn deaktiviert, liefert die Route `403 debug_trace_disabled`.

## Query-Parameter
- `request_id` (required): valide ASCII-ID (max 128, keine Whitespaces/`,`/`;`)
- `lookback_seconds` (optional): Default via `TRACE_DEBUG_LOOKBACK_SECONDS` oder 48h, Range `60..604800`
- `max_events` (optional): Default via `TRACE_DEBUG_MAX_EVENTS` oder `200`, Range `1..500`

## Response-Form (MVP)
```json
{
  "ok": true,
  "request_id": "<api-request-id>",
  "trace_request_id": "<lookup-request-id>",
  "trace": {
    "ok": true,
    "state": "ready|empty",
    "reason": "",
    "found": true,
    "event_count": 3,
    "events": [
      {
        "ts": "2026-03-01T00:00:00Z",
        "event": "api.request.start",
        "phase": "start",
        "summary": "POST /analyze started",
        "details": { "route": "/analyze" }
      }
    ]
  }
}
```

## Empty States
- `state=empty, reason=request_id_unknown_or_no_events`
- `state=empty, reason=request_id_outside_window`

## Redaction
Timeline-Details werden vor Auslieferung redacted (u. a. `authorization`, `token`, `secret`, `password`, `cookie`, E-Mail-Maskierung).

## Tests
- `tests/test_debug_trace.py`
- `tests/test_web_service_debug_trace_api.py`
