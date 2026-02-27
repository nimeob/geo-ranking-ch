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
- `preferences` (optional): Preference-Profile für personalisierte Bewertung
  - erlaubt sind nur bekannte Dimensionen (siehe Abschnitt „BL-20.4.c Preference-Profile Envelope“)
  - wenn `preferences` fehlt, greifen definierte Defaults (non-breaking)

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
    - inkl. `result.suitability_light.base_score`
    - inkl. `result.suitability_light.personalized_score`
  - `explainability.sources[]`
  - `explainability.base.factors[]`
  - `explainability.personalized.factors[]`

### Explainability v2 (BL-20.1.g.wp1)

Verbindliche Faktorstruktur für Legacy-Responses:
- `result.explainability.base.factors[*]`
- `result.explainability.personalized.factors[*]`
- Pflichtfelder je Faktor: `key`, `raw_value`, `normalized`, `weight`, `contribution`, `direction`, `reason`, `source`
- `direction` ist auf `pro|contra|neutral` begrenzt

Für den grouped-Shape liegt die gleiche Faktorlogik unter:
- `result.data.modules.explainability.base.factors[*]`
- `result.data.modules.explainability.personalized.factors[*]`

Darstellungs-/Integrationsregeln für Frontends (Sortierung, `direction`/`contribution`, Fallbacks, i18n):
- [`docs/user/explainability-v2-integrator-guide.md`](../user/explainability-v2-integrator-guide.md)

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
- Vollständig (legacy): [`docs/api/examples/v1/location-intelligence.response.success.address.json`](./examples/v1/location-intelligence.response.success.address.json)
- Vollständig (grouped): [`docs/api/examples/current/analyze.response.grouped.success.json`](./examples/current/analyze.response.grouped.success.json)
- Edge-Case (fehlende/deaktivierte Daten, grouped): [`docs/api/examples/current/analyze.response.grouped.partial-disabled.json`](./examples/current/analyze.response.grouped.partial-disabled.json)
- Additive Evolution (before/after, grouped): [`docs/api/examples/current/analyze.response.grouped.additive-before.json`](./examples/current/analyze.response.grouped.additive-before.json) / [`docs/api/examples/current/analyze.response.grouped.additive-after.json`](./examples/current/analyze.response.grouped.additive-after.json)
- Code-only Migration (before/after, grouped): [`docs/api/examples/current/analyze.response.grouped.code-only-before.json`](./examples/current/analyze.response.grouped.code-only-before.json) / [`docs/api/examples/current/analyze.response.grouped.code-only-after.json`](./examples/current/analyze.response.grouped.code-only-after.json)
- Fehler-Envelope: [`docs/api/examples/v1/location-intelligence.response.error.bad-request.json`](./examples/v1/location-intelligence.response.error.bad-request.json)

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
- grouped Referenzpayload (vollständig): [`docs/api/examples/current/analyze.response.grouped.success.json`](./examples/current/analyze.response.grouped.success.json)
- grouped Edge-Case-Payload (fehlende/deaktivierte Daten): [`docs/api/examples/current/analyze.response.grouped.partial-disabled.json`](./examples/current/analyze.response.grouped.partial-disabled.json)
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

## 12) Scoring Methodology Specification (BL-20.1.f)

Die dedizierte Methodik-Spezifikation für Bewertungs-/Risiko-/Confidence-Felder ist hier dokumentiert:

- [`docs/api/scoring_methodology.md`](./scoring_methodology.md)
- [`docs/api/address-intel-flow-deep-dive.md`](./address-intel-flow-deep-dive.md) (End-to-End Flow inkl. Source-Policy je `intelligence_mode` und Fehler-Mapping)

Inhalt (inkrementell):
- Vollständiger Score-Katalog (Pfad, Skala, Richtung, Stabilitätsstatus)
- Methodik-/Interpretationsregeln (inkl. Missing/Outlier-Handling)
- Worked Examples und Golden-Checks (in Folgeschritten)

## 13) BL-18.fc2 Forward-Compatible `options`-Envelope (`/analyze`)

Bezug: [#3](https://github.com/nimeob/geo-ranking-ch/issues/3), [#107](https://github.com/nimeob/geo-ranking-ch/issues/107), [#127](https://github.com/nimeob/geo-ranking-ch/issues/127)

Für den bestehenden `/analyze`-Endpoint gilt ergänzend (rückwärtskompatibel):

- Optionaler Request-Namespace `options` ist für additive Erweiterungen reserviert.
- `options` muss (falls vorhanden) ein JSON-Objekt sein, sonst `400 bad_request`.
- Unbekannte optionale Keys werden als No-Op ignoriert (keine 500/Crash-Pfade).
- `options.response_mode` (optional): `compact|verbose`
  - `compact` (Default): deduplizierte `result.data.by_source`-Projektion mit `module_ref`/`module_refs`
  - `verbose`: vollständige (redundanzreiche) `by_source`-Projektion für Legacy-Integratoren

Die übergreifende Policy dazu ist im Stability-Guide dokumentiert:
- [`docs/api/contract-stability-policy.md`](./contract-stability-policy.md)

## 14) BL-20.1.h Capability-/Entitlement-Envelope (BL-30-ready)

Bezug: [#105](https://github.com/nimeob/geo-ranking-ch/issues/105), [#106](https://github.com/nimeob/geo-ranking-ch/issues/106), [#107](https://github.com/nimeob/geo-ranking-ch/issues/107), [#18](https://github.com/nimeob/geo-ranking-ch/issues/18)

Ziel: optionale Produkt-/Freischaltungs-Metadaten explizit vom fachlichen Ergebnis trennen und **additiv** einführbar halten.

Request (optional, additiv):
- `options.capabilities` (Objekt, optional)
- `options.entitlements` (Objekt, optional)
- Fehlt der Envelope, bleibt das Verhalten unverändert.

Response (optional, additiv):
- `result.status.capabilities` (Objekt, optional)
- `result.status.entitlements` (Objekt, optional)
- Fachdaten bleiben unter `result.data`/`result.*` (Domain), Produkt-/Freischaltungs-Meta bleibt in `status`.

Stabilitäts-/Semantikrahmen (Mindeststandard):
- **Envelope selbst** (`options.capabilities`, `options.entitlements`, `result.status.capabilities`, `result.status.entitlements`): `stable`
- **Feature-Flags / experimentelle Capability-Keys innerhalb des Envelopes**: standardmäßig `beta` oder `internal` bis zur Produktfreigabe
- Integratoren dürfen nur `stable` hart voraussetzen; `beta/internal` defensiv konsumieren (Fallback/Graceful Degradation)

Einführungsstrategie (non-breaking):
1. Zuerst Envelope leer/optional ausrollen (keine Pflichtfelder).
2. Danach additive Schlüssel innerhalb des Envelopes ergänzen.
3. Legacy-Clients ohne Envelope-Unterstützung bleiben lauffähig; Minimalprojektion darf sich nicht ändern.

## 15) BL-20.4.c Preference-Profile Envelope

Bezug: [#85](https://github.com/nimeob/geo-ranking-ch/issues/85)

Ziel: Optionales, klar validierbares Request-Profil für personalisierte Umfeldauswertung bereitstellen,
ohne den bestehenden Request-Contract zu brechen.

Request (optional, additiv):
- `preferences` (Objekt, optional)
- Erlaubte Enum-Felder:
  - `lifestyle_density`: `rural|suburban|urban`
  - `noise_tolerance`: `low|medium|high`
  - `nightlife_preference`: `avoid|neutral|prefer`
  - `school_proximity`: `avoid|neutral|prefer`
  - `family_friendly_focus`: `low|medium|high`
  - `commute_priority`: `car|pt|bike|mixed`
- Optionale Gewichte unter `preferences.weights` (Objekt, Wertebereich je Key `0..1`)

Default-Verhalten (wenn `preferences` fehlt):
- `lifestyle_density=suburban`
- `noise_tolerance=medium`
- `nightlife_preference=neutral`
- `school_proximity=neutral`
- `family_friendly_focus=medium`
- `commute_priority=mixed`
- `weights={}`

Validierung:
- `preferences` muss (falls vorhanden) ein JSON-Objekt sein, sonst `400 bad_request`.
- Unbekannte Keys unter `preferences` oder `preferences.weights` werden als Vertragsfehler behandelt (`400 bad_request`).
- Gewichte müssen endliche Zahlen (keine Booleans) im Bereich `0..1` sein.

Dokumentierte Beispielprofile (3-5 reale Integrationsmuster):
- [`docs/api/preference-profiles.md`](./preference-profiles.md)

## 16) BL-20.4.d.wp2 Zweistufige Suitability-Score-Felder

Bezug: [#181](https://github.com/nimeob/geo-ranking-ch/issues/181)

Für Legacy-Responses unter `result.suitability_light` sind zwei klar getrennte Score-Felder vorgesehen:

- `result.suitability_light.base_score`
- `result.suitability_light.personalized_score`

Semantik (WP2-Stand):
- `base_score`: neutraler, datengetriebener Basiswert.
- `personalized_score`: personalisierte Sicht auf denselben Faktorenraum.
- Solange kein Präferenzsignal im Laufzeitpfad aktiv angewendet wird, gilt explizit der Fallback:
  - `personalized_score == base_score`

Kompatibilität:
- Felder sind additiv im bestehenden `suitability_light`-Objekt.
- Vorhandene Clients bleiben kompatibel; neue Clients können bereits auf die separaten Felder migrieren.

## 17) BL-20.4.d.wp7 Runtime-Fallback-Status für Personalisierung

Bezug: [#191](https://github.com/nimeob/geo-ranking-ch/issues/191)

Für transparente Laufzeit-Herkunft wird optionaler Status unter `result.status.personalization` geführt:

- `result.status.personalization.state` (`active|partial|deactivated`)
- `result.status.personalization.source` (z. B. `personalized_reweighting`, `base_score_fallback`, `base_score_default`)
- `result.status.personalization.fallback_applied` (`boolean`)
- `result.status.personalization.signal_strength` (`number >= 0`)

Semantik:
- `active`: wirksames Präferenzsignal wurde angewendet.
- `partial`: Präferenzprofil vorhanden, aber kein wirksames Signal (Fallback auf Basisscore).
- `deactivated`: kein Präferenzprofil im Request; Basisscore-Pfad aktiv.

Kompatibilität:
- `result.status.personalization` ist additiv/optional.
- Legacy-Clients ohne Auswertung dieses Statuspfads bleiben vollständig lauffähig.

## 18) BL-20.1.j Stabiles grouped Response-Schema v1 (für `/analyze`)

Bezug: [#279](https://github.com/nimeob/geo-ranking-ch/issues/279), [#278](https://github.com/nimeob/geo-ranking-ch/issues/278)

Für den produktionsnahen grouped Response-Shape ist ein eigenes, versioniertes Stabilitätspaket definiert:

- Normatives Schema: [`docs/api/schemas/v1/analyze.grouped.response.schema.json`](./schemas/v1/analyze.grouped.response.schema.json)
- Kernpfad-SSOT: [`docs/api/schemas/v1/analyze.grouped.core-paths.v1.json`](./schemas/v1/analyze.grouped.core-paths.v1.json)
- Human-readable Guide: [`docs/api/grouped-response-schema-v1.md`](./grouped-response-schema-v1.md)

Kompatibilitätsprinzip:
- Feste Grundstruktur bleibt stabil (`result.status` + `result.data`).
- Erweiterungen sind additiv (neue Felder/Zweige), bestehende Kernpfade bleiben unverändert.
- Vorher/Nachher-Beispiele für additive Erweiterung ohne Strukturbruch:
  - [`docs/api/examples/current/analyze.response.grouped.additive-before.json`](./examples/current/analyze.response.grouped.additive-before.json)
  - [`docs/api/examples/current/analyze.response.grouped.additive-after.json`](./examples/current/analyze.response.grouped.additive-after.json)

## 19) BL-20.1.k.wp1 Contract: Code-only Response + Dictionary-Referenzfelder

Bezug: [#286](https://github.com/nimeob/geo-ranking-ch/issues/286), [#287](https://github.com/nimeob/geo-ranking-ch/issues/287)

Ziel dieses Work-Packages ist ein **additiver Contract-Diff** für den Übergang auf code-first Antworten.

Normative Contract-Felder (optional/additiv in beiden Response-Shapes unter `result.status.dictionary`):
- `result.status.dictionary.version` (`string`, required wenn `dictionary` vorhanden ist)
- `result.status.dictionary.etag` (`string`, required wenn `dictionary` vorhanden ist)
- `result.status.dictionary.domains` (`object`, optional)
  - pro Domain: `version` + `etag` (required), optional `path` für den Dictionary-Endpoint

Regelwerk code-first:
- Fachliche Werte in `result.data.modules` dürfen als **codes/raw values** geliefert werden.
- Redundante Klartext-Labels im Result werden perspektivisch abgebaut; Auflösung erfolgt über Dictionary-Endpoints.
- Der neue Dictionary-Envelope ist additiv und bricht bestehende Integrationen nicht.

Schema-Stand (WP1):
- grouped: [`docs/api/schemas/v1/analyze.grouped.response.schema.json`](./schemas/v1/analyze.grouped.response.schema.json)
- legacy v1: [`docs/api/schemas/v1/location-intelligence.response.schema.json`](./schemas/v1/location-intelligence.response.schema.json)

Referenzbeispiele (before/after, gleiches Request-Szenario):
- before (label-lastig): [`docs/api/examples/current/analyze.response.grouped.code-only-before.json`](./examples/current/analyze.response.grouped.code-only-before.json)
- after (code-first + dictionary refs): [`docs/api/examples/current/analyze.response.grouped.code-only-after.json`](./examples/current/analyze.response.grouped.code-only-after.json)

## 20) BL-20.1.k.wp2 Dictionary-Endpoints (versioniert + cachebar)

Bezug: [#286](https://github.com/nimeob/geo-ranking-ch/issues/286), [#288](https://github.com/nimeob/geo-ranking-ch/issues/288)

Ziel: Klartext-Mappings über dedizierte Endpoints ausliefern, damit `POST /analyze` code-first bleiben kann.

Normative GET-Endpunkte:
- `GET /api/v1/dictionaries`
  - liefert globalen Dictionary-Index mit `version`, `etag`, `domains`
  - `domains.<name>` enthält mindestens `version`, `etag`, `path`
- `GET /api/v1/dictionaries/<domain>`
  - liefert pro Domain vollständige Mapping-Tabellen (`tables`) inkl. Domain-`version` und Domain-`etag`

Caching-Vertrag (beide Endpunkte):
- Response enthält `ETag` Header (stark, zitierter Token)
- Response enthält `Cache-Control` für clientseitiges Caching
- Bei `If-None-Match` Treffer wird `304 Not Modified` ohne Body zurückgegeben (inkl. `ETag` + `Cache-Control`)

Kompatibilität:
- Endpunkte sind additiv und verändern bestehendes `/analyze`-Routing nicht.
- Dictionary-Versionierung und ETag sind entkoppelt von Request-Parametern und stabil reproduzierbar.
