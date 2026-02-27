# BL-20.1.d.wp4 — Stability Guide + Contract-Change-Policy

Stand: 2026-02-26  
Gültig für: API-Vertrag [`docs/api/contract-v1.md`](./contract-v1.md) und Feldmanifest [`docs/api/field_catalog.json`](./field_catalog.json)

## 1) Ziel

Diese Richtlinie definiert, welche API-Felder Integratoren robust voraussetzen dürfen und wie Contract-Änderungen als **Breaking** oder **Non-Breaking** klassifiziert werden.

## 2) Stabilitätsklassen (verbindlich)

| Klasse | Bedeutung | Integrator-Regel |
|---|---|---|
| `stable` | Vertraglich stabil im Rahmen von `/api/v1`; Änderungen nur rückwärtskompatibel. | Darf fest konsumiert werden. |
| `beta` | Vorläufiges Feld; Struktur/Semantik kann sich ändern. | Nur defensiv konsumieren (Feature-Flag/Fallback). |
| `internal` | Internes Spiegel-/Diagnosefeld ohne externen Stabilitätsanspruch. | Nicht als Integrationsvertrag verwenden. |

### Stabile Felder für Integratoren

- Die stabile Integrationsbasis wird über `stability: "stable"` im Feldmanifest `docs/api/field_catalog.json` festgelegt.
- Felder mit `stable` dürfen Integratoren als vertraglich belastbar behandeln.
- Felder mit `beta` oder `internal` dürfen **nicht** als harte Abhängigkeit modelliert werden.

## 3) Contract-Change-Policy

### 3.1 Non-Breaking (innerhalb `/api/v1` erlaubt)

Beispiele:

- Neues **optionales** Feld wird ergänzt.
- Neue, optionale Struktur in einem bestehenden Objekt wird ergänzt.
- Präzisere Dokumentation ohne Verhaltensänderung.
- Stabilitätsstufe `beta -> stable` (Aufwertung).

### 3.2 Breaking (für `/api/v1` unzulässig, nur via neue Hauptversion)

Beispiele:

- Entfernen oder Umbenennen eines bestehenden Felds.
- Typänderung eines bestehenden Felds (z. B. `string -> object`).
- Ein bislang optionales Feld wird verpflichtend.
- Semantikänderung, die bestehende Integrationen fachlich bricht.
- Stabilitätsstufe `stable -> beta/internal` (Abwertung).

### 3.3 Versionsregel bei Breaking Changes

Breaking Changes werden **nicht** still in `/api/v1` ausgerollt. Sie erfordern:

1. neue Hauptversion (z. B. `/api/v2`),
2. dokumentierte Migration,
3. klaren Release-Hinweis.

## 4) BL-18.fc1 Regression-Guardrails (Forward-Compatibility)

Bezug:
- Parent-/Kontext-Issue: [#3](https://github.com/nimeob/geo-ranking-ch/issues/3)
- Folgeabhängigkeit: [#127](https://github.com/nimeob/geo-ranking-ch/issues/127)

Für additive Contract-Evolution in `/api/v1` gelten zusätzlich folgende dauerhafte Regression-Guards:

1. **Legacy-Minimalprojektion bleibt stabil:**
   - additive optionale Felder dürfen die Auswertung einer bestehenden Minimal-Client-Sicht nicht verändern.
2. **Semantische Trennung bleibt strikt:**
   - `result.status` enthält Qualitäts-/Source-Meta,
   - `result.data` enthält Entity-/Moduldaten,
   - status-artige Schlüssel dürfen nicht nach `result.data` durchrutschen.
3. **Smoke-Kompatibilität bleibt robust:**
   - zusätzliche optionale Felder dürfen den Smoke-Mindestcheck (`ok=true`, `result` vorhanden) nicht brechen.

Automatisierter Nachweis im Repo:
- `tests/test_contract_compatibility_regression.py`
- `tests/test_web_service_grouped_response.py`
- `tests/test_remote_smoke_script.py`

### 4.1 BL-18.fc2 Request-Options-Envelope (additiv, no-op by default)

Bezug:
- Parent-/Kontext-Issue: [#3](https://github.com/nimeob/geo-ranking-ch/issues/3)
- Folgeabhängigkeiten: [#107](https://github.com/nimeob/geo-ranking-ch/issues/107), [#127](https://github.com/nimeob/geo-ranking-ch/issues/127)

Regel für den aktuellen `/analyze`-Request-Contract:
- Optionaler Top-Level-Namespace `options` ist für additive Erweiterungen reserviert.
- Fehlt `options`, bleibt das Laufzeitverhalten unverändert (voll rückwärtskompatibel).
- Ist `options` vorhanden, muss es ein JSON-Objekt sein; sonst `400 bad_request`.
- Aktive Standard-Keys im Envelope:
  - `response_mode` (`compact|verbose`, Default `compact`)
  - `include_labels` (`boolean`, Default `false`, temporäre Legacy-Migrationsbrücke)
- Unbekannte Keys unter `options` werden als **No-Op** behandelt (ignoriert statt Crash/500), um spätere Deep-Mode-Felder ohne Breaking Change ergänzen zu können.
- Der `include_labels`-Pfad ist explizit sunset-gebunden und darf nur als Übergangsmodus bestehen (siehe Contract Abschnitt 22).

Automatisierter Nachweis im Repo:
- `tests/test_web_e2e.py::TestWebServiceE2E::test_analyze_ignores_unknown_options_keys_as_additive_noop`
- `tests/test_web_e2e.py::TestWebServiceE2E::test_bad_request_options_must_be_object_when_provided`
- `tests/test_web_e2e.py::TestWebServiceE2E::test_bad_request_include_labels_rejects_non_boolean_values`

### 4.2 BL-20.1.h Capability-/Entitlement-Envelope (BL-30-ready, additiv)

Bezug:
- Follow-up-Issues: [#105](https://github.com/nimeob/geo-ranking-ch/issues/105), [#106](https://github.com/nimeob/geo-ranking-ch/issues/106), [#107](https://github.com/nimeob/geo-ranking-ch/issues/107)
- Kontext: [#18](https://github.com/nimeob/geo-ranking-ch/issues/18)

Regelset:
- Request-Meta läuft optional über `options.capabilities` und `options.entitlements`.
- Response-Meta läuft optional über `result.status.capabilities` und `result.status.entitlements`.
- Envelope-Felder sind `stable` (Integrationsanker); innere, produktnahe Keys können `beta`/`internal` bleiben.
- Legacy-Clients ohne Envelope-Unterstützung müssen weiterhin gültige Responses konsumieren können (keine Pflicht-/Typänderungen an bestehenden Domainfeldern).

Automatisierter Nachweis im Repo:
- `tests/test_api_contract_v1.py::TestApiContractV1::test_capability_entitlement_envelope_is_additive_for_legacy_clients`
- `tests/test_contract_compatibility_regression.py::TestContractCompatibilityRegression::test_legacy_minimal_projection_survives_additive_optional_fields`

### 4.3 BL-20.4.c Preference-Profile Envelope (additiv, default-stabil)

Bezug:
- Work-Package: [#85](https://github.com/nimeob/geo-ranking-ch/issues/85)

Regelset:
- Request-Feld `preferences` ist optional und additiv.
- Fehlt `preferences`, gilt der dokumentierte Default-Satz (non-breaking Verhalten).
- Bei Presence muss `preferences` ein Objekt sein und darf nur bekannte Dimensionen enthalten.
- `preferences.weights` ist optional; erlaubte Keymenge entspricht den bekannten Dimensionen; Werte müssen numerisch im Bereich `0..1` liegen.
- Ungültige Enum-/Range-/Unknown-Key-Kombinationen führen deterministisch zu `400 bad_request`.

Automatisierter Nachweis im Repo:
- `tests/test_web_e2e.py::TestWebServiceE2E::test_analyze_accepts_valid_preferences_profile`
- `tests/test_web_e2e.py::TestWebServiceE2E::test_bad_request_preferences_reject_invalid_enums_and_weights`
- `tests/test_api_contract_v1.py::TestApiContractV1::test_preference_profile_is_additive_with_defined_defaults`

### 4.4 BL-20.1.j Grouped Response-Schema v1 (Pfadstabilität + additive Erweiterung)

Bezug:
- Work-Package: [#279](https://github.com/nimeob/geo-ranking-ch/issues/279)
- Folgeabhängigkeit: [#278](https://github.com/nimeob/geo-ranking-ch/issues/278)

Regelset:
- Der grouped Response-Shape hat eine feste Grundstruktur (`result.status` + `result.data`) mit stabilen Kernpfaden.
- Kernpfade sind als Single-Source-of-Truth explizit versioniert und maschinenlesbar.
- Neue Informationen werden ausschließlich additiv ergänzt (neue Felder/Zweige), ohne bestehende Kernpfade zu verschieben/umzubenennen.
- Feldpfad-/Semantikänderungen bestehender Kernpfade gelten als Breaking und erfordern eine neue Hauptversion.

Normative Artefakte:
- Schema: `docs/api/schemas/v1/analyze.grouped.response.schema.json`
- Kernpfade: `docs/api/schemas/v1/analyze.grouped.core-paths.v1.json`
- Human-readable Referenz: `docs/api/grouped-response-schema-v1.md`

Automatisierter Nachweis im Repo:
- `tests/test_grouped_response_schema_v1.py`
- `tests/test_contract_compatibility_regression.py`

## 5) Changelog-/Release-Hinweisprozess

Bei jeder Contract-Änderung:

1. Änderung klassifizieren (**Non-Breaking** oder **Breaking**).
2. `docs/api/field_catalog.json` aktualisieren (`stability`, Typ, Required-Status, Shape-Zuordnung).
3. Relevante Beispielpayloads unter `docs/api/examples/**` aktualisieren.
4. Validierung lokal ausführen:
   - `python3 scripts/validate_field_catalog.py`
   - `pytest -q tests/test_api_contract_v1.py tests/test_api_field_catalog.py`
5. Änderungsnotiz in [`CHANGELOG.md`](../../CHANGELOG.md) unter `[Unreleased]` ergänzen.
6. Bei Breaking-Änderung zusätzlich explizite Migrationshinweise (alt -> neu) in den Release-Notes dokumentieren.

## 6) Referenzen

- API-Vertrag: [`docs/api/contract-v1.md`](./contract-v1.md)
- Feldmanifest: [`docs/api/field_catalog.json`](./field_catalog.json)
- Changelog: [`CHANGELOG.md`](../../CHANGELOG.md)
