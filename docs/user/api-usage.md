# API Usage Guide

Dieser Guide beschreibt die HTTP-API des Webservice (`src/web_service.py`) inkl. Auth, Request-ID-Verhalten, Validierung und typische Fehlercodes.

## Base URL

Lokal:

```text
http://localhost:8080
```

Dev/Remote (Beispiel):

```text
https://<dein-endpoint>
```

## Endpoint-Referenz

| Methode | Pfad | Zweck | Auth |
|---|---|---|---|
| `GET` | `/health` | Liveness/Service-Erreichbarkeit | nein |
| `GET` | `/version` | Build-/Version-Metadaten | nein |
| `POST` | `/analyze` | Adressanalyse und Standort-Resultat | optional (`API_AUTH_TOKEN`) |

### Routing-Verhalten (wichtig)

Der Service normalisiert eingehende Pfade robust:

- trailing Slash wird toleriert (`/health/`, `/analyze/`)
- doppelte Slashes werden kollabiert (`//analyze//` → `/analyze`)
- Query/Fragment werden für Routing ignoriert (`/health?probe=1`)

---

## `GET /health`

### Beispiel

```bash
curl -sS "http://localhost:8080/health"
```

### Erfolgsantwort (200)

```json
{
  "ok": true,
  "service": "geo-ranking-ch",
  "ts": "2026-02-26T17:02:31.123456+00:00",
  "request_id": "req-3e5f0a1f0a87419d"
}
```

---

## `GET /version`

Liefert Build-Metadaten aus ENV:

- `APP_VERSION` (Default: `dev`)
- `GIT_SHA` (Default: `unknown`)

### Beispiel

```bash
curl -sS "http://localhost:8080/version"
```

### Erfolgsantwort (200)

```json
{
  "service": "geo-ranking-ch",
  "version": "dev",
  "commit": "unknown",
  "request_id": "req-5ac7d9c5f2b74835"
}
```

---

## `POST /analyze`

### Request-Body

| Feld | Typ | Pflicht | Default | Beschreibung |
|---|---|---|---|---|
| `query` | `string` | ja | – | Adresse/Suchtext; wird getrimmt; leer/whitespace-only ist ungültig |
| `intelligence_mode` | `string` | nein | `basic` | Erlaubt: `basic`, `extended`, `risk` (trim + case-insensitive normalisiert) |
| `timeout_seconds` | `number` | nein | `ANALYZE_DEFAULT_TIMEOUT_SECONDS` (15) | Muss endliche Zahl > 0 sein; wird auf `ANALYZE_MAX_TIMEOUT_SECONDS` gecappt |

### Beispiel (ohne Auth)

```bash
curl -sS -X POST "http://localhost:8080/analyze" \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: api-guide-001" \
  -d '{
    "query":"Bahnhofstrasse 1, 8001 Zürich",
    "intelligence_mode":"extended",
    "timeout_seconds": 15
  }'
```

### Beispiel (mit Auth)

```bash
curl -sS -X POST "http://localhost:8080/analyze" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <API_AUTH_TOKEN>" \
  -d '{"query":"St. Gallen"}'
```

### Erfolgsantwort (200, verkürzt)

```json
{
  "ok": true,
  "result": {
    "query": "Bahnhofstrasse 1, 8001 Zürich"
  },
  "request_id": "api-guide-001"
}
```

---

## Authentifizierung

`POST /analyze` ist nur dann geschützt, wenn `API_AUTH_TOKEN` gesetzt ist.

### Verhalten

- `API_AUTH_TOKEN` **nicht gesetzt** → Endpoint ist offen.
- `API_AUTH_TOKEN` gesetzt → Header `Authorization: Bearer <token>` ist Pflicht.
- Fehlender/falscher Token → `401 unauthorized`.

---

## Request-ID-Korrelation

Jede Antwort enthält:

- JSON-Feld `request_id`
- Response-Header `X-Request-Id`

Falls kein gültiger Header mitgegeben wurde, erzeugt der Service automatisch eine ID (`req-<suffix>`).

### Unterstützte Header (Priorität)

1. `X-Request-Id`
2. `X_Request_Id`
3. `Request-Id`
4. `Request_Id`
5. `X-Correlation-Id`
6. `X_Correlation_Id`
7. `Correlation-Id`
8. `Correlation_Id`

### Validierungsregeln für Header-IDs

Ein Header-Wert wird nur akzeptiert, wenn er:

- nach Trim nicht leer ist
- keine Steuerzeichen enthält
- keinen Whitespace innerhalb der ID enthält
- keine Trennzeichen `,` oder `;` enthält
- ASCII-only ist
- maximal 128 Zeichen hat

Ungültige Kandidaten werden verworfen, danach greift der nächste Header in Prioritätsreihenfolge.

---

## Statuscodes und Fehlerbilder

| HTTP | `error` | Wann |
|---|---|---|
| `200` | – | erfolgreicher Request |
| `400` | `bad_request` | ungültiger Body, fehlendes `query`, ungültiges `intelligence_mode`, ungültiges `timeout_seconds` |
| `401` | `unauthorized` | Auth aktiv, aber fehlender/falscher Bearer-Token |
| `404` | `not_found` | unbekannter Endpoint |
| `422` | `address_intel` | fachlicher Fehler aus Address-Intelligence-Layer |
| `504` | `timeout` | Upstream/Analyse-Timeout |
| `500` | `internal` | unerwarteter interner Fehler |

### Fehlerantwort (Beispiel)

```json
{
  "ok": false,
  "error": "bad_request",
  "message": "timeout_seconds must be a finite number > 0",
  "request_id": "req-0a5e5c0f89e34713"
}
```

---

## Konfigurations-ENV (API-relevant)

| Variable | Default | Wirkung |
|---|---|---|
| `HOST` | `0.0.0.0` | Bind-Adresse des HTTP-Servers |
| `PORT` | – | Primärer Listen-Port |
| `WEB_PORT` | `8080` | Fallback-Port, falls `PORT` fehlt/leer |
| `API_AUTH_TOKEN` | leer | Aktiviert Bearer-Auth auf `POST /analyze` |
| `ANALYZE_DEFAULT_TIMEOUT_SECONDS` | `15` | Default für `timeout_seconds`, wenn im Request nicht gesetzt |
| `ANALYZE_MAX_TIMEOUT_SECONDS` | `45` | Obergrenze für effektiven Analyze-Timeout |
| `APP_VERSION` | `dev` | Ausgabe in `GET /version` |
| `GIT_SHA` | `unknown` | Ausgabe in `GET /version` |

Vollständige ENV-Referenz: **[Configuration / ENV Guide](./configuration-env.md)**.

---

## Schnell-Checks

```bash
# Health
curl -sS "http://localhost:8080/health"

# Version
curl -sS "http://localhost:8080/version"

# Analyze minimal
curl -sS -X POST "http://localhost:8080/analyze" \
  -H "Content-Type: application/json" \
  -d '{"query":"St. Gallen"}'
```

Nächste Seiten:

- **[Configuration / ENV Guide](./configuration-env.md)**
- Troubleshooting *(folgt in BL-19.5)*
