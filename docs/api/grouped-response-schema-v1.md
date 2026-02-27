# BL-20.1.j — Grouped Response-Schema v1 (stabil + additiv erweiterbar)

Stand: 2026-02-27  
Gilt für: `POST /analyze` grouped response (`result.status` + `result.data`)

## 1) Normatives Schema (maschinenlesbar)

- JSON Schema v1: [`docs/api/schemas/v1/analyze.grouped.response.schema.json`](./schemas/v1/analyze.grouped.response.schema.json)

Das Schema fixiert die **stabile Grundstruktur**:
- `ok`, `request_id`, `result`
- `result.status.{quality,source_health,source_meta}`
- additiver Dictionary-Envelope: `result.status.dictionary.{version,etag,domains?}`
- `result.data.{entity,modules,by_source}`

Gleichzeitig bleibt additive Evolution erlaubt (`additionalProperties: true` in erweiterbaren Objekten).

## 2) Single-Source-of-Truth für Kernpfade

- Kernpfad-Liste v1: [`docs/api/schemas/v1/analyze.grouped.core-paths.v1.json`](./schemas/v1/analyze.grouped.core-paths.v1.json)

Diese Liste ist der verbindliche Anker für zentrale Integrationsinformationen (u. a. Confidence, Entity-Koordinaten, Match-Score).

## 3) Kompatibilitäts-/Evolutionsregeln

- Additive Änderungen: neue Felder/Zweige sind erlaubt.
- Breaking Änderungen: Feldverschiebung, Umbenennung oder Semantikbruch bestehender Kernpfade.
- Breaking Changes erfordern neue Hauptversion (siehe Contract-Policy):
  - [`docs/api/contract-stability-policy.md`](./contract-stability-policy.md)

## 4) Response-Dedupe-Modi (`compact` default, `verbose` opt-in)

Ab BL-20.1.i kann die `by_source`-Darstellung in zwei Modi geliefert werden:

- `options.response_mode = "compact"` (Default)
  - `result.data.by_source.*.data` enthält primär Referenzen auf `result.data.modules` (`module_ref`/`module_refs`)
  - nur kleine Kompatibilitäts-Slices bleiben inline (z. B. `match.selected_score`, `match.candidate_count`)
  - Ziel: redundante Serialisierung deutlich reduzieren
- `options.response_mode = "verbose"` (opt-in)
  - liefert die bisherige vollständige `by_source`-Projektion (höhere Payload-Größe)

Die Kernpfade der grouped-Struktur bleiben stabil (`result.status`, `result.data.entity`, `result.data.modules`, `result.data.by_source`).

## 5) Vorher/Nachher-Beispiele (additive Erweiterung ohne Strukturbruch)

- Before: [`docs/api/examples/current/analyze.response.grouped.additive-before.json`](./examples/current/analyze.response.grouped.additive-before.json)
- After (nur additive Felder): [`docs/api/examples/current/analyze.response.grouped.additive-after.json`](./examples/current/analyze.response.grouped.additive-after.json)

## 6) Code-first/Dictionaries (WP1/WP3)

Für die Migration auf code-only Responses ist ein additiver Referenzpfad dokumentiert:
- before (label-lastig): [`docs/api/examples/current/analyze.response.grouped.code-only-before.json`](./examples/current/analyze.response.grouped.code-only-before.json)
- after (code-first + dictionary refs): [`docs/api/examples/current/analyze.response.grouped.code-only-after.json`](./examples/current/analyze.response.grouped.code-only-after.json)

Runtime-Stand (WP3):
- `result.status.dictionary` wird standardmäßig mitgeliefert.
- `result.data.modules.building.decoded` entfällt zugunsten von `building.codes`.
- `result.data.modules.energy.decoded_summary` entfällt zugunsten von `energy.codes`.

Die Beispiele zeigen denselben Case einmal mit inline-Labels und einmal mit `result.status.dictionary` + Codefeldern in `result.data.modules`.

## 7) Regression-Tests

- Schema-/Kernpfad-Guard: `tests/test_grouped_response_schema_v1.py`
- Semantik-/Separations-Guard: `tests/test_contract_compatibility_regression.py`, `tests/test_web_service_grouped_response.py`
