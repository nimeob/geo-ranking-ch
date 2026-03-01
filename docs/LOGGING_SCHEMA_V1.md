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

## Implementierungsstand BL-340.1 + BL-340.2 + BL-340.3

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

## Abgrenzung zu BL-340.4

BL-340.1 bis BL-340.3 decken **Kernschema + Redaction + API- und UI-Lifecycle-Logging** ab.
Offen bleibt als nächster Child-Step:

- #413 (Upstream Provider Logging + Trace-/Retry-Nachweise)
