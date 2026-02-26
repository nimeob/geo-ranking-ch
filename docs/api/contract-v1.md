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
- [`docs/api/examples/current/analyze.response.grouped.success.json`](./examples/current/analyze.response.grouped.success.json)

## 6) CI-Check (verdrahtet)

- Workflow: [`.github/workflows/contract-tests.yml`](../../.github/workflows/contract-tests.yml)
- Trigger: Änderungen an `docs/api/**`, `tests/test_api_contract_v1.py`, `tests/test_api_field_catalog.py`, `tests/data/api_contract_v1/**`, `scripts/validate_field_catalog.py`
- Ausführung:
  - `pytest -q tests/test_api_contract_v1.py tests/test_api_field_catalog.py`
  - `python3 scripts/validate_field_catalog.py`
- Golden-Testdaten:
  - positiv: `tests/data/api_contract_v1/valid/*.json`
  - negativ: `tests/data/api_contract_v1/invalid/*.json`

## 7) Scope-Abgrenzung BL-20.1.a / BL-20.1.b

- **BL-20.1.a:** Versionierungspfad, Contract-Dokument, JSON-Schemas, Fehlercode-Matrix, Beispielpayloads
- **BL-20.1.b:** Golden-Case-Validierung (positive/negative Contract-Tests), Testdatenablage und CI-Verdrahtung

## 8) Maschinenlesbarer Feldkatalog (BL-20.1.e)

Für die laufende Response-Felddokumentation (legacy + grouped) ist der Feldkatalog die Single-Source-of-Truth:

- Feldmanifest: [`docs/api/field_catalog.json`](./field_catalog.json)
- Human-readable Referenz: [`docs/api/field-reference-v1.md`](./field-reference-v1.md)
- grouped Referenzpayload: [`docs/api/examples/current/analyze.response.grouped.success.json`](./examples/current/analyze.response.grouped.success.json)
- Validator: [`scripts/validate_field_catalog.py`](../../scripts/validate_field_catalog.py)

Der Validator prüft automatisiert:
- Manifest-Schema (Pflichtattribute, Feldtypen, Stabilitätsklassen)
- Vollständige Feldabdeckung gegenüber den Beispielpayloads je Response-Shape
- Typ-Konsistenz (Manifest vs. Beispiele)
- Required-Felder pro Shape

## 9) Pflegeprozess für neue/angepasste Response-Felder

Bei jeder Contract-Änderung an `legacy` oder `grouped` gilt:

1. Beispielpayload anpassen (`docs/api/examples/...`).
2. `docs/api/field_catalog.json` mit neuem/angepasstem Feldpfad aktualisieren.
3. `python3 scripts/validate_field_catalog.py` lokal ausführen.
4. Contract-Tests laufen lassen:
   - `pytest -q tests/test_api_contract_v1.py tests/test_api_field_catalog.py`
5. Änderungsnotiz in `CHANGELOG.md` ergänzen (Breaking vs. Non-Breaking klar markieren).

Nur wenn Manifest + Beispiele + Checks konsistent sind, gilt der Contract als aktualisiert.

## 10) Stability Guide + Contract-Change-Policy (BL-20.1.d.wp4)

Der verbindliche Leitfaden für Stabilitätsklassen (`stable`, `beta`, `internal`) sowie die Klassifizierung von Contract-Änderungen (Breaking vs. Non-Breaking) ist hier dokumentiert:

- [`docs/api/contract-stability-policy.md`](./contract-stability-policy.md)

Kurzregel:
- `stable`: darf von Integratoren fest vorausgesetzt werden.
- `beta`: nur defensiv konsumieren (Fallback/Feature-Flag).
- `internal`: kein externer Integrationsvertrag.
- Breaking Changes werden nicht in `/api/v1` ausgerollt, sondern über eine neue Hauptversion mit Migrationshinweisen.

## 11) Human-readable Feldreferenz (BL-20.1.d.wp2)

Die vollständige, menschenlesbare Feldreferenz für beide ausgelieferten Response-Shapes (`legacy`, `grouped`) ist hier dokumentiert:

- [`docs/api/field-reference-v1.md`](./field-reference-v1.md)

Inhalt der Referenz:
- Feldpfad pro Shape inkl. Semantik, Typ, Pflicht/Optionalität und Beispielwert
- Modus-/Feature-Abhängigkeiten (u. a. `intelligence_mode`)
- Edge-Case-Notation für dynamische Keys (`*`) und Arrays (`[*]`)
- Querverweis auf den maschinenlesbaren Katalog als Source-of-Truth
