# BL-20.1.f — Scoring Methodology Specification (v1)

Stand: 2026-02-26
Status: Draft (WP1 + WP2 + WP3)
Methodik-Version: `scoring-v1-draft`

Diese Spezifikation dokumentiert die aktuell vertraglich relevanten Bewertungs-/Risiko-/Confidence-Felder der API inkl. Berechnungslogik, Interpretationsrahmen und Integrationshinweisen.

Quellen der Wahrheit:
- Feldkatalog: [`docs/api/field_catalog.json`](./field_catalog.json)
- API-Contract: [`docs/api/contract-v1.md`](./contract-v1.md)
- Human-readable Feldreferenz: [`docs/api/field-reference-v1.md`](./field-reference-v1.md)

> Scope WP1 (#79): vollständiger **Score-Katalog**.
>
> Scope WP2 (#80): **Berechnungslogik + Interpretationsrahmen** inkl. Missing-/Outlier-Regeln und Bias-Hinweisen.

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

## 2) Berechnungslogik je Score-Familie

### 2.1 Confidence-Familie (`result.status.quality.confidence.*`, `result.confidence`)

Normativer grouped Hauptscore (`score`, `max`, `level`) basiert auf vier positiven Komponenten und zwei Penalties:

```text
score_raw
  = match_component              # 0..40
  + data_completeness            # 0..30
  + cross_source_consistency     # 0..20
  + required_source_health       # 0..10
  - mismatch_penalty             # 0..~14+
  - ambiguity_penalty            # 0..10

score = clamp(round(score_raw), 0, 100)
max   = 100
```

Komponenten-Definition (aktuelles v1-Verhalten):
- `match_component`: aus Match-Qualität (pre/detail), linear auf `0..40` skaliert.
- `data_completeness`: Verfügbarkeit zentraler IDs/Attribute (EGID/EGRID, Status, Baujahr etc.), gedeckelt auf `30`.
- `cross_source_consistency`: Konsistenz zwischen Kernquellen (u. a. GWR, PLZ-Layer, Admin-Boundary, optional OSM), gedeckelt auf `20`.
- `required_source_health`: Anteil erfolgreich verfügbarer Pflichtquellen, skaliert auf `0..10`.
- `mismatch_penalty`: Abzug bei harten Widersprüchen (z. B. Hausnummer-/Strassenabweichung).
- `ambiguity_penalty`: Abzug bei geringer Distanz zum nächstbesten Match.

Level-Mapping:
- `high`: `score >= 82`
- `medium`: `62 <= score < 82`
- `low`: `score < 62`

Legacy-Projektion:
- `result.confidence = round(score / max, 2)` (normiert `0..1`).
- `result.explainability.sources[*].confidence` bleibt quellenbezogen (`0..1`) und ist **kein** Ersatz für den globalen Qualitäts-Score.

### 2.2 Matching-Familie (`result.data.modules.match.selected_score`, by_source-Projection)

`selected_score` basiert auf einem zweistufigen Kandidatenscoring:

1) **Pre-Score** (Suchtreffer-Text/Metadaten)
- Street-/Hausnummer-/PLZ-/Ort-Matches (Bonus/Malus)
- `origin=address` Bonus
- Search-Rank-Bonus
- Feature-ID-/Label-Kohärenz-Bonus

2) **Detail-Score** (hydratisierte Adress-/GWR-Attribute)
- Abgleich Strasse/Hausnummer/PLZ/Ort mit GWR-Attributen
- Bonus für amtliche Adresse (`adr_official`)
- Bonus für plausiblen Gebäudestatus

```text
selected_score_internal = pre_score + detail_score
selected_score_contract = clamp(round(selected_score_internal / 100, 2), 0, 1)
```

Hinweis zur Interpretation:
- Der Match-Score ist ein Ranking-/Vergleichsscore innerhalb des Kandidaten-Sets.
- Der Contract-Wert wird als normierter Qualitätsindikator (`0..1`) bereitgestellt.
- Für das Endvertrauen muss er zusammen mit `result.status.quality.confidence.*` gelesen werden.
- `result.data.by_source.*.data.match.selected_score` ist eine projektionale Darstellung desselben Match-Ergebnisses für Source-Slices.

### 2.3 Legacy-Kontext/Suitability-Familie (`context_profile.*`, `suitability_light.*`)

Diese Felder bleiben als Legacy-Contract-Felder (`beta`) dokumentiert und folgen dem gleichen Richtungsverständnis wie grouped Scores:

- `pt_access_score` (`0..100`, höher = besser)
- `noise_risk` (`low|medium|high`, höher = schlechter)
- `suitability_light.score` (`0..100`, höher = besser)
- `suitability_light.traffic_light` (`green|yellow|red`)

Normative Kopplungsregel für Integratoren:
- Suitability darf **nicht** isoliert interpretiert werden.
- Mindestens folgende Kontexte zusammen lesen: Match-Qualität, Confidence-Level, `noise_risk` und Explainability.

## 3) Interpretationsbänder (inkl. Richtung und Grenzen)

### 3.1 Confidence (`result.status.quality.confidence.score`)

| Band | Range | Bedeutung |
|---|---:|---|
| low | `0..61` | Unsicheres Resultat; manuelle Prüfung empfohlen |
| medium | `62..81` | Nutzbar mit Vorsicht; mögliche Ambiguitäten prüfen |
| high | `82..100` | Gute Daten-/Konsistenzlage, regulär nutzbar |

### 3.2 Legacy-Confidence (`result.confidence`)

| Band | Range |
|---|---:|
| low | `< 0.62` |
| medium | `0.62 .. < 0.82` |
| high | `>= 0.82` |

### 3.3 Noise-/Suitability-Ampel

| Feld | Grün | Gelb | Rot |
|---|---:|---:|---:|
| `suitability_light.score` | `>= 72` | `52 .. < 72` | `< 52` |
| `noise_risk` (ordinal) | `low` | `medium` | `high` |

Richtungsregel (verbindlich):
- Numerische Scores: höher = besser, **außer** explizit als Risikoindex gekennzeichnet.
- Risiko-Ordinals (`noise_risk`): `high` ist fachlich ungünstiger als `low`.

## 4) Missing Values, Outlier und Determinismus

### 4.1 Missing Values

- Fehlende Pflichtquellen senken `required_source_health` direkt.
- Fehlende Kernattribute reduzieren `data_completeness`.
- Bei unvollständigen Inputs werden betroffene Komponenten defensiv bewertet statt implizit positiv imputed.
- Bei niedriger Gesamtqualität wird eine Warnung gesetzt (`manuelle Prüfung empfohlen`).

### 4.2 Outlier-/Grenzbehandlung

- Komponenten werden auf definierte Teilbereiche begrenzt (z. B. `0..40`, `0..30`, `0..20`, `0..10`).
- Gesamtscore wird auf `0..100` geclamped und auf ganze Zahl gerundet.
- Normierte Legacy-Werte bleiben innerhalb `0..1`.

### 4.3 Determinismus

- Gleiche Inputs + gleiche Upstream-Datenstände müssen zu identischen Scores führen.
- Rounding ist explizit Teil der Methodik (reproduzierbare Vergleichbarkeit).
- Änderungen an Schwellen/Gewichtung gelten als methodische Änderung und müssen versioniert dokumentiert werden.

## 5) Unsicherheit, Bias und sichere Nutzung

Typische Unsicherheitsquellen:
- Datenlücken einzelner Quellen (Coverage, Aktualität, Teil-Ausfälle)
- Regional unterschiedliche Datenqualität (urban/rural)
- Ambige Adressen (kleine Score-Abstände zwischen Kandidaten)
- Unterschiedliche Semantik zwischen offiziellen/Community-Quellen

Bias-Hinweise:
- Quellen mit hoher Verfügbarkeit können in Randregionen überrepräsentieren/unterrepräsentieren.
- Risiko-/Eignungsindikatoren sind heuristisch und keine behördliche Einzelbewilligungsentscheidung.

Integrationsregel:
- Für automatisierte Entscheidungen immer mindestens Confidence-Level + Explainability + Source-Status gemeinsam auswerten.
- Bei `confidence.level=low` oder Ambiguitätswarnungen Fallback/Manual-Review vorsehen.

## 6) Integrator-Hinweise pro Stabilitätsstatus

- `stable`: kann als vertraglich belastbarer Integrationspunkt genutzt werden.
- `beta`: defensiv konsumieren (Fallbacks/Feature-Flags einplanen).
- `internal`: nicht Teil des externen Integrationsvertrags (im Score-Katalog aktuell kein Feld mit `internal`).

Details zur Stabilitäts- und Change-Policy:
- [`docs/api/contract-stability-policy.md`](./contract-stability-policy.md)

## 7) Konsistenzregel zum Feldkatalog

Die Methodik muss 1:1 mit dem maschinenlesbaren Feldkatalog konsistent bleiben:
- Neue Score-/Risk-/Rating-/Confidence-Felder zuerst in `docs/api/field_catalog.json` ergänzen.
- Danach `docs/api/scoring_methodology.md` synchronisieren.
- Anschließend Contract-Checks laufen lassen.

Verifikation:
- `python3 scripts/validate_field_catalog.py`
- `pytest -q tests/test_api_field_catalog.py tests/test_scoring_methodology_golden.py`

## 8) Reproduzierbare Worked Examples (WP3)

Die folgenden Referenzfälle sind so aufgebaut, dass Integratoren die Methodik 1:1 nachrechnen können (Input -> Rechenschritte -> Endscore):

| Beispiel | Zielprofil | Input-Artefakt | Output-Artefakt |
|---|---|---|---|
| Beispiel A | hoher Confidence-Case (klarer Match, geringe Penalties) | [`docs/api/examples/scoring/worked-example-01-high-confidence.input.json`](./examples/scoring/worked-example-01-high-confidence.input.json) | [`docs/api/examples/scoring/worked-example-01-high-confidence.output.json`](./examples/scoring/worked-example-01-high-confidence.output.json) |
| Beispiel B | mittlerer Confidence-Case (teilweise Lücken, moderate Penalties) | [`docs/api/examples/scoring/worked-example-02-medium-confidence.input.json`](./examples/scoring/worked-example-02-medium-confidence.input.json) | [`docs/api/examples/scoring/worked-example-02-medium-confidence.output.json`](./examples/scoring/worked-example-02-medium-confidence.output.json) |
| Beispiel C | niedriger Confidence-Case (hohe Ambiguität + Mismatch-Risiko) | [`docs/api/examples/scoring/worked-example-03-low-confidence.input.json`](./examples/scoring/worked-example-03-low-confidence.input.json) | [`docs/api/examples/scoring/worked-example-03-low-confidence.output.json`](./examples/scoring/worked-example-03-low-confidence.output.json) |

### 8.1 Rechenweg (verbindliches Muster)

Für alle drei Fälle gilt derselbe deterministische Ablauf:

```text
match_component = selected_score * 40
score_raw = match_component + data_completeness + cross_source_consistency + required_source_health - mismatch_penalty - ambiguity_penalty
score = clamp(round(score_raw), 0, 100)
legacy_confidence = round(score / 100, 2)
```

Level-Mapping bleibt identisch zu Abschnitt 2.1 / 3.1:
- `high`: `score >= 82`
- `medium`: `62 <= score < 82`
- `low`: `score < 62`

### 8.2 Kurzresultate je Referenzfall

| Beispiel | `score_raw` | `score` | `level` | `result.confidence` |
|---|---:|---:|---|---:|
| A | `91.4` | `91` | `high` | `0.91` |
| B | `64.6` | `65` | `medium` | `0.65` |
| C | `34.4` | `34` | `low` | `0.34` |

## 9) Methodik-Versionierung und Migrationsregeln

Die Methodik-Version ist ein vertraglich relevantes Steuerungsfeld und muss in Doku **und** Referenzartefakten synchron geführt werden.

### 9.1 Versionierungsschema

Aktueller Stand: `scoring-v1-draft`

Änderungsklassen:
- **Patch** (z. B. `scoring-v1-draft.1`): rein redaktionelle Klarstellungen ohne Änderungen an Rechenlogik, Schwellen oder Referenzwerten.
- **Minor** (z. B. `scoring-v1.1`): rückwärtskompatible methodische Erweiterungen (zusätzliche optionale Felder/Bänder), bestehende Score-Semantik bleibt stabil.
- **Major** (z. B. `scoring-v2`): Breaking Change bei Rechenlogik, Schwellen, Feldsemantik oder Contract-Projektion.

### 9.2 Verbindlicher Change-Prozess

Bei jeder methodischen Änderung sind folgende Schritte Pflicht:
1. Methodik-Version in diesem Dokument aktualisieren (`Methodik-Version: ...`).
2. `methodology_version` in allen Worked-Example-Artefakten (`*.input.json`, `*.output.json`) synchron anpassen.
3. Golden-Tests aktualisieren (inkl. erwarteter Referenzwerte) und lokal ausführen.
4. Migrationshinweise für Integratoren ergänzen (Scope, Risiko, notwendige Consumer-Anpassungen).

### 9.3 Migrationshinweise (Integrator-Checkliste)

- **Patch:** keine Consumer-Änderung nötig; Re-Read der Doku empfohlen.
- **Minor:** Consumer sollten neue optionale Felder defensiv behandeln (Feature-Flag/Fallback).
- **Major:** verpflichtende Migrationsplanung inkl. Parallelbetrieb/Abnahme gegen neue Golden-Cases.

Verifikation:
- `pytest -q tests/test_api_field_catalog.py tests/test_scoring_methodology_golden.py`
- `python3 scripts/validate_field_catalog.py`

## 10) Open Items (Folge-Work-Packages)

- Der Scope von BL-20.1.f.wp1–wp4 (#79, #80, #81, #82) ist abgeschlossen.
- Folgearbeiten laufen in separaten Backlog-Issues (z. B. Explainability v2, personalisierte Scores).
