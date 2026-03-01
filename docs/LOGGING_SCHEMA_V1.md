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

## Implementierungsstand BL-340.1

- Shared Helper: `src/shared/structured_logging.py`
  - `build_event(...)`
  - `redact_mapping(...)`
  - `emit_event(...)`
- Erste Call-Sites im API-Service:
  - `service.startup`
  - `service.redirect_listener.enabled`
  - `api.health.response`

## Abgrenzung zu BL-340.2 / .3 / .4

BL-340.1 liefert bewusst nur das **Kernschema + Redaction + Logging-Baustein**.
Vollständige Request-Lifecycle-Instrumentierung und Upstream-/UI-Flows folgen in den Child-Issues:

- #411 (API Ingress/Egress)
- #412 (UI Interaktions-/Client-Logging)
- #413 (Upstream Provider Logging + Trace-Nachweise)
