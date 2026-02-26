# BL-20.1.d.wp2 — Human-readable API Field Reference (v1)

Stand: 2026-02-26

Diese Referenz ist die menschenlesbare Sicht auf den maschinenlesbaren Feldkatalog:

- Feldmanifest (Single Source of Truth): [`docs/api/field_catalog.json`](./field_catalog.json)
- Legacy-Referenzpayload: [`docs/api/examples/v1/location-intelligence.response.success.address.json`](./examples/v1/location-intelligence.response.success.address.json)
- Grouped-Referenzpayload (vollständig): [`docs/api/examples/current/analyze.response.grouped.success.json`](./examples/current/analyze.response.grouped.success.json)
- Grouped-Edge-Case (fehlende/deaktivierte Daten): [`docs/api/examples/current/analyze.response.grouped.partial-disabled.json`](./examples/current/analyze.response.grouped.partial-disabled.json)

## Notation

- `*` in einem Feldpfad steht für dynamische Keys (z. B. Source-Namen oder Feldnamen).
- `[*]` steht für Elemente innerhalb eines Arrays.
- **Pflicht = Ja** bedeutet: Feld ist im jeweiligen Shape vertraglich erwartet.
- **Pflicht = Bedingt** bedeutet: Feld ist vertraglich erwartet, wenn der zugehörige Modus aktiv ist.

## Modus-/Feature-Abhängigkeiten und Edge-Cases

- `intelligence_mode=extended|risk`: Intelligence-Felder dürfen nur in diesen Modi erwartet werden.
- Dynamische Maps (`*`) können unterschiedliche Schlüssel je Request/Quelle enthalten.
- Array-Felder (`[*]`) können leer sein; Feldpfad und Typ bleiben trotzdem vertraglich fix.
- `internal`-Felder sind nicht für externe Integrationslogik gedacht (nur observability/debug use-cases).

## Legacy-Shape (`response_shape=legacy`)

| Feldpfad | Typ | Pflicht | Stabilität | Modus/Feature | Bedeutung / Constraints | Beispiel |
|---|---|---|---|---|---|---|
| `ok` | `boolean` | Ja | `stable` | `alle` | Signalisiert erfolgreichen Request. | `true` |
| `request_id` | `string` | Ja | `stable` | `alle` | Korrelation-ID für Request/Logs. | `bl20-field-catalog-001` |
| `api_version` | `string` | Ja | `stable` | `alle` | Vertragsversion des v1-API-Namespaces. | `v1` |
| `result.entity_id` | `string` | Ja | `stable` | `alle` | Stabile Entity-ID des analysierten Objekts. | `ch:egid:1029384` |
| `result.input_mode` | `string` | Ja | `stable` | `alle` | Input-Modus (address\|point). | `address` |
| `result.as_of` | `string` | Ja | `stable` | `alle` | Zeitstempel der fachlichen Datensicht. | `2026-02-26T18:35:00Z` |
| `result.confidence` | `number` | Ja | `stable` | `alle` | Gesamt-Confidence (0..1) im legacy Shape. | `0.84` |
| `result.building_profile.egid` | `string` | Ja | `stable` | `alle` | EGID des Gebäudes. | `1029384` |
| `result.building_profile.build_year` | `number` | Ja | `beta` | `alle` | Baujahr im legacy Building-Profil. | `1998` |
| `result.building_profile.heating_type` | `string` | Ja | `beta` | `alle` | Primärer Heiztyp im legacy Profil. | `Fernwärme` |
| `result.context_profile.pt_access_score` | `number` | Ja | `beta` | `alle` | ÖV-Zugangs-Score (context profile). | `77` |
| `result.context_profile.noise_risk` | `string` | Ja | `beta` | `alle` | Lärmrisiko-Klassifikation. | `medium` |
| `result.suitability_light.traffic_light` | `string` | Ja | `beta` | `alle` | Ampelurteil der Eignung. | `yellow` |
| `result.suitability_light.score` | `number` | Ja | `beta` | `alle` | Numerischer Suitability-Score. | `63` |
| `result.suitability_light.reasons[*]` | `string` | Ja | `beta` | `alle` | Liste der Hauptgründe zum Suitability-Urteil. (`[*]` = Array-Element(e)) | `Gute ÖV-Anbindung` |
| `result.explainability.sources[*].source` | `string` | Ja | `stable` | `alle` | Name der Datenquelle pro Explainability-Eintrag. (`[*]` = Array-Element(e)) | `geoadmin_gwr` |
| `result.explainability.sources[*].as_of` | `string` | Ja | `stable` | `alle` | Standdatum der jeweiligen Quelle. (`[*]` = Array-Element(e)) | `2026-02-20` |
| `result.explainability.sources[*].confidence` | `number` | Ja | `stable` | `alle` | Confidence pro Explainability-Quelle. (`[*]` = Array-Element(e)) | `0.93` |
| `result.explainability.sources[*].license` | `string` | Ja | `beta` | `alle` | Lizenz-/Nutzungshinweis je Quelle. (`[*]` = Array-Element(e)) | `ODbL` |
| `result.explainability.*.factors[*].key` | `string` | Ja | `beta` | `alle` | Faktor-Key in Explainability v2 (`*` = `base` oder `personalized`). (`[*]` = Array-Element(e)) | `noise` |
| `result.explainability.*.factors[*].raw_value` | `number` | Ja | `beta` | `alle` | Rohwert des Faktors vor Normalisierung. (`*` = `base` oder `personalized`) | `68` |
| `result.explainability.*.factors[*].normalized` | `number` | Ja | `beta` | `alle` | Normalisierter Faktorwert. (`*` = `base` oder `personalized`) | `0.68` |
| `result.explainability.*.factors[*].weight` | `number` | Ja | `beta` | `alle` | Faktor-Gewichtung im jeweiligen Profil. (`*` = `base` oder `personalized`) | `0.35` |
| `result.explainability.*.factors[*].contribution` | `number` | Ja | `beta` | `alle` | Gewichteter Beitragswert zum (Teil-)Score. (`*` = `base` oder `personalized`) | `-0.238` |
| `result.explainability.*.factors[*].direction` | `string` | Ja | `beta` | `alle` | Wirkungsrichtung des Faktors (`pro\|contra\|neutral`). (`*` = `base` oder `personalized`) | `contra` |
| `result.explainability.*.factors[*].reason` | `string` | Ja | `beta` | `alle` | Maschinenlesbare Begründung für den Faktorbeitrag. (`*` = `base` oder `personalized`) | `Hohe Nachtlärm-Exposition entlang Hauptverkehrsachse.` |
| `result.explainability.*.factors[*].source` | `string` | Ja | `beta` | `alle` | Primäre Datenquelle des Faktors. (`*` = `base` oder `personalized`) | `laermkataster_ch` |

## Grouped-Shape (`response_shape=grouped`)

| Feldpfad | Typ | Pflicht | Stabilität | Modus/Feature | Bedeutung / Constraints | Beispiel |
|---|---|---|---|---|---|---|
| `ok` | `boolean` | Ja | `stable` | `alle` | Signalisiert erfolgreichen Request. | `true` |
| `request_id` | `string` | Ja | `stable` | `alle` | Korrelation-ID für Request/Logs. | `bl20-field-catalog-001` |
| `result.status.quality.confidence.score` | `number` | Ja | `stable` | `alle` | Qualitäts-Confidence Score im grouped status-Block. | `92` |
| `result.status.quality.confidence.max` | `number` | Ja | `stable` | `alle` | Maximalwert des Confidence-Scores. | `100` |
| `result.status.quality.confidence.level` | `string` | Ja | `stable` | `alle` | Verbale Confidence-Klasse. | `high` |
| `result.status.quality.executive_summary.verdict` | `string` | Ja | `beta` | `alle` | Verdichtetes Fazit im quality-Block. | `ok` |
| `result.status.source_health.*.status` | `string` | Ja | `stable` | `alle` | Gesundheitsstatus je Quelle (dynamischer Source-Key). (`*` = dynamischer Key) | `ok` |
| `result.status.source_health.*.records` | `number` | Ja | `beta` | `alle` | Anzahl berücksichtigter Records je Quelle. (`*` = dynamischer Key) | `1` |
| `result.status.source_meta.source_classification.*.primary_source` | `string` | Ja | `beta` | `alle` | Primärquelle pro klassifiziertem Feld. (`*` = dynamischer Key) | `geoadmin_search` |
| `result.status.source_meta.source_attribution.*[*]` | `string` | Ja | `stable` | `alle` | Zugeordnete Quellen je Modulgruppe. (`[*]` = Array-Element(e)) | `osm_reverse` |
| `result.status.source_meta.field_provenance.*.primary_source` | `string` | Ja | `beta` | `alle` | Primärquelle im Feld-Provenance-Block. (`*` = dynamischer Key) | `geoadmin_search` |
| `result.status.source_meta.field_provenance.*.present` | `boolean` | Ja | `beta` | `alle` | Kennzeichnet, ob das Feld in den Rohdaten vorhanden war. (`*` = dynamischer Key) | `true` |
| `result.data.entity.query` | `string` | Ja | `stable` | `alle` | Eingangsquery im entity-Block. | `Bahnhofstrasse 1, 8001 Zürich` |
| `result.data.entity.matched_address` | `string` | Ja | `stable` | `alle` | Normalisierte/gematchte Adresse. | `Bahnhofstrasse 1, 8001 Zürich` |
| `result.data.entity.ids.egid` | `string` | Ja | `stable` | `alle` | EGID im grouped entity.ids-Block. | `123` |
| `result.data.entity.coordinates.lat` | `number` | Ja | `stable` | `alle` | Breitengrad des Entities. | `47.3769` |
| `result.data.entity.coordinates.lon` | `number` | Ja | `stable` | `alle` | Längengrad des Entities. | `8.5417` |
| `result.data.entity.administrative.gemeinde` | `string` | Ja | `beta` | `alle` | Gemeindezuordnung des Entities. | `Zürich` |
| `result.data.modules.match.selected_score` | `number` | Ja | `stable` | `alle` | Match-Score des gewählten Kandidaten. | `0.99` |
| `result.data.modules.match.candidate_count` | `number` | Ja | `stable` | `alle` | Anzahl geprüfter Match-Kandidaten. | `3` |
| `result.data.modules.building.baujahr` | `number` | Ja | `beta` | `alle` | Baujahr im grouped building-Modul. | `1999` |
| `result.data.modules.building.decoded.heizung[*].label` | `string` | Ja | `beta` | `alle` | Dekodierte Heizungsbezeichnung. (`[*]` = Array-Element(e)) | `Wärmepumpe` |
| `result.data.modules.energy.decoded_summary.heizung[*]` | `string` | Ja | `beta` | `alle` | Heizungszusammenfassung als Stringliste. (`[*]` = Array-Element(e)) | `Wärmepumpe` |
| `result.data.modules.cross_source.plz_layer.plz` | `number` | Ja | `beta` | `alle` | PLZ aus Cross-Source-Layer. | `8001` |
| `result.data.modules.explainability.*.factors[*].key` | `string` | Ja | `beta` | `alle` | Grouped Explainability-v2 Faktor-Key (`*` = `base` oder `personalized`). (`[*]` = Array-Element(e)) | `noise` |
| `result.data.modules.explainability.*.factors[*].raw_value` | `number` | Ja | `beta` | `alle` | Rohwert des Faktors vor Normalisierung. (`*` = `base` oder `personalized`) | `61` |
| `result.data.modules.explainability.*.factors[*].normalized` | `number` | Ja | `beta` | `alle` | Normalisierter Faktorwert. (`*` = `base` oder `personalized`) | `0.61` |
| `result.data.modules.explainability.*.factors[*].weight` | `number` | Ja | `beta` | `alle` | Faktor-Gewichtung im jeweiligen Profil. (`*` = `base` oder `personalized`) | `0.30` |
| `result.data.modules.explainability.*.factors[*].contribution` | `number` | Ja | `beta` | `alle` | Gewichteter Beitrag je Faktor. (`*` = `base` oder `personalized`) | `-0.183` |
| `result.data.modules.explainability.*.factors[*].direction` | `string` | Ja | `beta` | `alle` | Wirkungsrichtung (`pro\|contra\|neutral`). (`*` = `base` oder `personalized`) | `contra` |
| `result.data.modules.explainability.*.factors[*].reason` | `string` | Ja | `beta` | `alle` | Maschinenlesbare Faktorbegründung. (`*` = `base` oder `personalized`) | `Lärmbelastung im Radius 500m über Referenzmedian.` |
| `result.data.modules.explainability.*.factors[*].source` | `string` | Ja | `beta` | `alle` | Primäre Datenquelle des Faktors. (`*` = `base` oder `personalized`) | `laermkataster_ch` |
| `result.data.modules.intelligence.tenants_businesses.entities[*].name` | `string` | Bedingt (bei aktivem Modus) | `beta` | `intelligence_mode=extended\|risk` | Entity-Name im Intelligence-Modul. (`[*]` = Array-Element(e)) | `Muster AG` |
| `result.data.modules.field_provenance.*.primary_source` | `string` | Ja | `internal` | `alle` | Primärquelle je Feld in modules.field_provenance. (`*` = dynamischer Key) | `geoadmin_search` |
| `result.data.modules.field_provenance.*.present` | `boolean` | Ja | `internal` | `alle` | Presence-Flag je Feld in modules.field_provenance. (`*` = dynamischer Key) | `true` |
| `result.data.by_source.*.source` | `string` | Ja | `stable` | `alle` | Dynamischer Source-Key gespiegelt als Feldwert. (`*` = dynamischer Key) | `geoadmin_search` |
| `result.data.by_source.*.data.match.selected_score` | `number` | Ja | `beta` | `alle` | Match-Score innerhalb by_source-Projektion. (`*` = dynamischer Key) | `0.99` |
| `result.data.by_source.*.data.match.candidate_count` | `number` | Ja | `beta` | `alle` | Kandidatenzahl innerhalb by_source-Projektion. (`*` = dynamischer Key) | `3` |
| `result.data.by_source.*.data.intelligence.tenants_businesses.entities[*].name` | `string` | Bedingt (bei aktivem Modus) | `beta` | `intelligence_mode=extended\|risk` | Intelligence-Entityname innerhalb by_source-Projektion. (`*` = dynamischer Key; `[*]` = Array-Element(e)) | `Muster AG` |

