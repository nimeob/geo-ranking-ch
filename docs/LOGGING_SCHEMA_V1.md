# Logging Schema v1 (BL-340.1)

Stand: 2026-03-01

## Ziel

Ein minimales, stabiles JSON-Event-Schema für korrelierbares Logging über UI/API/Upstream.
Der Fokus von v1 liegt auf **Debugbarkeit**, **Korrelation** und **sicherer Redaction**.

## Event-Format (normativ)

Jedes Log-Event ist ein JSON-Objekt (1 Zeile pro Event / JSONL) mit mindestens diesen Pflichtfeldern:

- `ts` — UTC-Timestamp (ISO-8601, z. B. `2026-03-01T00:31:59.123456Z`)
- `level` — `debug|info|warn|error`
- `event` — stabiler Eventname (z. B. `service.startup`, `api.health.response`)
- `trace_id` — Flow-Korrelation über Komponenten hinweg
- `request_id` — Request-Korrelation für API-Interaktionen
- `session_id` — Client-/Session-Korrelation (falls vorhanden, sonst leer)

Optionale, aber empfohlene Kontextfelder:

- `component` — Quelle (z. B. `api.web_service`, später `ui.client`, `api.upstream`)
- `direction` — Richtung (`ui->api`, `api->upstream`, `api->client`, `internal`)
- `status` — Kurzstatus (`ok`, `error`, `timeout`, `enabled`, `listening`, ...)
- `route`, `method`, `status_code`, `duration_ms`
- `error_class`, `error_message` (redacted/sanitized)

## Redaction-Regeln (verbindlich)

Die folgenden Schlüssel/Feldnamen werden key-basiert vollständig maskiert (`[REDACTED]`), case-insensitive und auch für verschachtelte Objekte:

- enthält `authorization`
- enthält `token`
- enthält `secret`
- enthält `password`
- enthält `api_key` / `apikey`
- enthält `cookie` / `set-cookie`

Zusätzlich werden pattern-basiert maskiert:

- `Bearer <token>` → `Bearer [REDACTED]`
- E-Mail-Adressen → `n***@domain.tld` (Best-Effort, nicht reversibel)

## Beispiele

### 1) Service-Startup

```json
{
  "ts": "2026-03-01T00:32:10.123456Z",
  "level": "info",
  "event": "service.startup",
  "trace_id": "",
  "request_id": "",
  "session_id": "",
  "component": "api.web_service",
  "direction": "internal",
  "status": "listening",
  "listen_url": "http://0.0.0.0:8080"
}
```

### 2) API-Health-Response (minimal instrumentiert)

```json
{
  "ts": "2026-03-01T00:32:21.009901Z",
  "level": "info",
  "event": "api.health.response",
  "trace_id": "req-1234567890abcdef",
  "request_id": "req-1234567890abcdef",
  "session_id": "",
  "component": "api.web_service",
  "direction": "api->client",
  "status": "ok",
  "route": "/health",
  "method": "GET"
}
```

### 3) API Request-Start (Ingress, BL-340.2)

```json
{
  "ts": "2026-03-01T01:36:11.125991Z",
  "level": "info",
  "event": "api.request.start",
  "trace_id": "req-abc123",
  "request_id": "req-abc123",
  "session_id": "sess-42",
  "component": "api.web_service",
  "direction": "client->api",
  "status": "received",
  "route": "/analyze",
  "method": "POST"
}
```

### 4) API Request-Ende (Egress inkl. Fehlerklassifikation, BL-340.2)

```json
{
  "ts": "2026-03-01T01:36:11.241120Z",
  "level": "warn",
  "event": "api.request.end",
  "trace_id": "req-abc123",
  "request_id": "req-abc123",
  "session_id": "sess-42",
  "component": "api.web_service",
  "direction": "api->client",
  "status": "client_error",
  "route": "/analyze",
  "method": "POST",
  "status_code": 401,
  "duration_ms": 115.129,
  "error_code": "unauthorized",
  "error_class": "unauthorized"
}
```

### 5) UI->API Request-Lifecycle (BL-340.3)

```json
{
  "ts": "2026-03-01T01:55:44.103Z",
  "level": "info",
  "event": "ui.api.request.start",
  "trace_id": "req-m7vyrj-9f31a6c2",
  "request_id": "req-m7vyrj-9f31a6c2",
  "session_id": "sess-m7vyr5-8c22a9b1",
  "component": "ui.gui_mvp",
  "direction": "ui->api",
  "status": "sent",
  "route": "/analyze",
  "method": "POST",
  "input_kind": "query",
  "auth_present": true
}
```

```json
{
  "ts": "2026-03-01T01:55:44.281Z",
  "level": "info",
  "event": "ui.api.request.end",
  "trace_id": "req-m7vyrj-9f31a6c2",
  "request_id": "req-m7vyrj-9f31a6c2",
  "session_id": "sess-m7vyr5-8c22a9b1",
  "component": "ui.gui_mvp",
  "direction": "api->ui",
  "status": "ok",
  "route": "/analyze",
  "method": "POST",
  "status_code": 200,
  "duration_ms": 178.221
}
```

### 6) API->Upstream Request-Start (BL-340.4)

```json
{
  "ts": "2026-03-01T02:05:11.004Z",
  "level": "info",
  "event": "api.upstream.request.start",
  "trace_id": "req-bl340-413",
  "request_id": "req-bl340-413",
  "session_id": "sess-bl340",
  "component": "api.address_intel",
  "direction": "api->upstream",
  "status": "sent",
  "source": "geoadmin_search",
  "target_host": "api3.geo.admin.ch",
  "target_path": "/rest/services/api/SearchServer",
  "attempt": 1,
  "max_attempts": 3,
  "retry_count": 0,
  "timeout_seconds": 15.0
}
```

### 7) API->Upstream Request-Ende mit Retry (BL-340.4)

```json
{
  "ts": "2026-03-01T02:05:11.451Z",
  "level": "warn",
  "event": "api.upstream.request.end",
  "trace_id": "req-bl340-413",
  "request_id": "req-bl340-413",
  "session_id": "sess-bl340",
  "component": "api.address_intel",
  "direction": "upstream->api",
  "status": "retrying",
  "source": "geoadmin_search",
  "status_code": 503,
  "duration_ms": 447.312,
  "attempt": 1,
  "max_attempts": 3,
  "retry_count": 0,
  "retryable": true,
  "error_class": "http_error",
  "error_message": "HTTP-Fehler (503)"
}
```

### 8) Upstream-Response Summary (BL-340.4)

```json
{
  "ts": "2026-03-01T02:05:12.009Z",
  "level": "info",
  "event": "api.upstream.response.summary",
  "trace_id": "req-bl340-413",
  "request_id": "req-bl340-413",
  "session_id": "sess-bl340",
  "component": "api.address_intel",
  "direction": "upstream->api",
  "status": "ok",
  "source": "geoadmin_search",
  "target_host": "api3.geo.admin.ch",
  "target_path": "/rest/services/api/SearchServer",
  "cache": "miss",
  "records": 5,
  "payload_kind": "dict",
  "attempt": 2,
  "max_attempts": 3,
  "retry_count": 1
}
```

## Implementierungsstand BL-340.1 + BL-340.2 + BL-340.3 + BL-340.4

- Shared Helper: `src/shared/structured_logging.py`
  - `build_event(...)`
  - `redact_mapping(...)`
  - `emit_event(...)`
- API-Call-Sites im Service:
  - `service.startup`
  - `service.redirect_listener.enabled`
  - `api.health.response`
  - `api.request.start` (Ingress, `GET/POST/OPTIONS`)
  - `api.request.end` (Egress inkl. `status_code`, `duration_ms`, `error_class`)
- UI-Call-Sites im GUI-MVP (`src/shared/gui_mvp.py`):
  - `ui.session.start`
  - `ui.interaction.form.submit`
  - `ui.interaction.map.analyze_trigger`
  - `ui.input.accepted`
  - `ui.state.transition` (`idle/loading/success/error`)
  - `ui.api.request.start`
  - `ui.api.request.end` (inkl. `status_code`, `duration_ms`, `error_code/error_class`)
  - `ui.validation.error`
  - `ui.output.map_status`
- Upstream-Call-Sites BL-340.4:
  - API-Koordinatenauflösung in `src/api/web_service.py` (`wgs84tolv95`, `gwr_identify`)
  - Address-Intel-JSON-Provider in `src/api/address_intel.py` (`HttpClient.get_json`)
  - RSS-Provider in `src/api/address_intel.py` (`fetch_google_news_rss`)

## BL-340.4 Nachweise

- Traces (Erfolg + Fehler): `docs/testing/BL-340_UPSTREAM_TRACE_EVIDENCE.md`
- Regressionstests:
  - `tests/test_address_intel_upstream_logging.py`
  - `tests/test_web_service_request_logging.py`
