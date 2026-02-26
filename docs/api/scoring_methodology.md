# BL-20.1.f.wp1 — Scoring Methodology Specification (v1)

Stand: 2026-02-26
Status: Draft (Score-Katalog)

Diese Spezifikation dokumentiert alle aktuell vertraglich relevanten Bewertungs-/Risiko-/Confidence-Felder der API.

Quellen der Wahrheit:
- Feldkatalog: [`docs/api/field_catalog.json`](./field_catalog.json)
- API-Contract: [`docs/api/contract-v1.md`](./contract-v1.md)
- Human-readable Feldreferenz: [`docs/api/field-reference-v1.md`](./field-reference-v1.md)

> Scope dieses Work-Packages (#79): vollständiger **Score-Katalog** inkl. Feldpfad, Zielaussage, Skala, Richtung und Stabilitätsstatus.

## 1) Score-Katalog (legacy + grouped)

| Feldpfad | Shape | Typ | Ziel/Aussage | Wertebereich / Skala | Richtung | Stabilitätsstatus | Herkunft (lineage) |
|---|---|---|---|---|---|---|---|
| `result.confidence` | legacy | number | Gesamtvertrauen in das Legacy-Gesamtergebnis | `0.0 .. 1.0` (normiert) | höher = besser | `stable` | Scoring |
| `result.explainability.sources[*].confidence` | legacy | number | Vertrauenswert je Datenquelle im Explainability-Block | `0.0 .. 1.0` (normiert) | höher = besser | `stable` | Source Attribution |
| `result.context_profile.pt_access_score` | legacy | number | Zugänglichkeit ÖV aus Sicht des Umfeldprofils | `0 .. 100` (Index) | höher = besser | `beta` | Context Scoring |
| `result.context_profile.noise_risk` | legacy | string | Kategorisiertes Lärmrisiko am Standort | `low \| medium \| high` (ordinal) | höheres Risiko = schlechter | `beta` | Context Scoring |
| `result.suitability_light.score` | legacy | number | Verdichteter Eignungswert des Standorts | `0 .. 100` (Index) | höher = besser | `beta` | Suitability-Modul |
| `result.suitability_light.traffic_light` | legacy | string | Ampelklassifikation zur schnellen Eignungsbeurteilung | `green \| yellow \| red` (ordinal) | grüner = besser | `beta` | Suitability-Modul |
| `result.status.quality.confidence.score` | grouped | number | Qualitäts-Confidence als Score im grouped status-Block | `0 .. max` (aktuell `0 .. 100`) | höher = besser | `stable` | Scoring |
| `result.status.quality.confidence.max` | grouped | number | Obergrenze/Skalenmaximum für den grouped Confidence-Score | positive Zahl (aktuell `100`) | n/a (Skalenanker) | `stable` | Scoring |
| `result.status.quality.confidence.level` | grouped | string | Verbale Klassifikation des grouped Confidence-Scores | `low \| medium \| high` (ordinal) | höher = besser | `stable` | Scoring |
| `result.data.modules.match.selected_score` | grouped | number | Score des ausgewählten Match-Kandidaten | `0.0 .. 1.0` (normiert) | höher = besser | `stable` | Matching-Modul |
| `result.data.by_source.*.data.match.selected_score` | grouped | number | Source-spezifischer Match-Score in der by_source-Projektion | `0.0 .. 1.0` (normiert) | höher = besser | `beta` | by_source projection |

## 2) Integrator-Hinweise pro Stabilitätsstatus

- `stable`: kann als vertraglich belastbarer Integrationspunkt genutzt werden.
- `beta`: nur defensiv konsumieren (Fallbacks/Feature-Flags einplanen).
- `internal`: nicht Teil des externen Integrationsvertrags (im Score-Katalog aktuell kein Feld mit `internal`).

Details zur Stabilitäts- und Change-Policy:
- [`docs/api/contract-stability-policy.md`](./contract-stability-policy.md)

## 3) Konsistenzregel zum Feldkatalog

Der Score-Katalog muss 1:1 mit dem maschinenlesbaren Feldkatalog konsistent bleiben:
- Neue Score-/Risk-/Rating-/Confidence-Felder zuerst in `docs/api/field_catalog.json` ergänzen
- Danach `docs/api/scoring_methodology.md` synchronisieren
- Anschließend Contract-Checks laufen lassen

Verifikation:
- `python3 scripts/validate_field_catalog.py`
- `pytest -q tests/test_api_field_catalog.py`

## 4) Open Items (Folge-Work-Packages)

- #80: Berechnungslogik, Normalisierung, Gewichtung und Interpretationsbänder vertiefen
- #81: Reproduzierbare Worked Examples (Input -> Rechenschritte -> Endscore)
- #82: Golden-Tests + Methodik-Versionierung
