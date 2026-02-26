# BL-20.1.a — API Contract v1 (Schemas + Fehlercodes)

Stand: 2026-02-26
Status: **v1-Contract spezifiziert** (Implementierung erfolgt inkrementell in BL-20.x)

## 1) Versionierungspfad (verbindlich)

- Öffentlicher Namespace für neue Produkt-API: **`/api/v1`**
- Start-Endpunkt für das Produktobjekt: **`POST /api/v1/location-intelligence`**
- Kompatibilitätsregel:
  - bestehender MVP-Endpunkt `/analyze` bleibt vorerst bestehen
  - neue BL-20-Funktionalität wird unter `/api/v1/...` aufgebaut
  - Breaking Changes erfolgen ausschließlich über neue Hauptversion (`/api/v2`)

Versionierungsprinzip:
- **Minor-/Patch-Änderungen** innerhalb `v1` sind rückwärtskompatibel
- **Major-Änderungen** (inkompatible Feldänderungen/Removals) erhalten neue Pfadversion

## 2) JSON-Schemas (Quelle der Wahrheit)

- Request-Schema:
  - [`docs/api/schemas/v1/location-intelligence.request.schema.json`](./schemas/v1/location-intelligence.request.schema.json)
- Erfolgs-Response-Schema:
  - [`docs/api/schemas/v1/location-intelligence.response.schema.json`](./schemas/v1/location-intelligence.response.schema.json)
- Fehler-Envelope-Schema:
  - [`docs/api/schemas/v1/error.response.schema.json`](./schemas/v1/error.response.schema.json)

## 3) Request-/Response-Kurzprofil

### Request (`POST /api/v1/location-intelligence`)

- `input.mode`: `address` oder `point`
- bei `address`: `input.address` erforderlich
- bei `point`: `input.point.{lat,lon}` erforderlich
- `requested_modules`: mindestens ein Modul aus:
  - `building_profile`
  - `context_profile`
  - `suitability_light`
  - `explainability`

### Success Response

Top-Level:
- `ok=true`
- `api_version` (z. B. `v1`)
- `request_id`
- `result` mit:
  - `entity_id`, `input_mode`, `as_of`, `confidence`
  - `building_profile`
  - `context_profile`
  - `suitability_light`
  - `explainability.sources[]`

### Error Response

Top-Level:
- `ok=false`
- `api_version`
- `request_id`
- `error` mit `code`, `message`, optional `details`

## 4) Fehlercode-Matrix (v1)

| HTTP | `error.code` | Bedeutung |
|---|---|---|
| `400` | `bad_request` | Request formal ungültig (Schema/Typ/Pflichtfeld) |
| `401` | `unauthorized` | Auth fehlt/ungültig |
| `404` | `not_found` | Ressource/Route nicht vorhanden |
| `422` | `validation_failed` | Fachliche Validierung fehlgeschlagen |
| `429` | `rate_limited` | Rate-Limit erreicht |
| `502` | `upstream_error` | Externe Datenquelle/Upstream fehlerhaft |
| `504` | `timeout` | Verarbeitung/Upstream Timeout |
| `500` | `internal` | Unerwarteter interner Fehler |

## 5) Beispielpayloads im Repo

Requests:
- [`docs/api/examples/v1/location-intelligence.request.address.json`](./examples/v1/location-intelligence.request.address.json)
- [`docs/api/examples/v1/location-intelligence.request.point.json`](./examples/v1/location-intelligence.request.point.json)

Responses:
- [`docs/api/examples/v1/location-intelligence.response.success.address.json`](./examples/v1/location-intelligence.response.success.address.json)
- [`docs/api/examples/v1/location-intelligence.response.error.bad-request.json`](./examples/v1/location-intelligence.response.error.bad-request.json)

## 6) Abgrenzung zu BL-20.1.b

BL-20.1.a liefert die **Versionierung + Schemas + Fehlercodes + Beispielpayloads**.

BL-20.1.b erweitert auf **Golden-Case-Validierungstests** (automatisierte Contract-Checks gegen Positiv-/Negativfälle).