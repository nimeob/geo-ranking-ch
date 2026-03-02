> **Diese Datei wurde konsolidiert.** Aktuelle kanonische Version: [DATA_SOURCES.md](DATA_SOURCES.md)

---

# BL-20.2.b — Feld-Mapping Quelle -> Domain (CH, v1)

Stand: 2026-02-26

## Zweck

Dieses Dokument definiert das **technische Feld-Mapping pro Datenquelle** für BL-20.2.b:

- Quelle-Felder (`swisstopo/geo.admin`, `BFS GWR`, `OSM`, freie Web-Quellen)
- Zielpfade im Domain-Objekt (`build_report`)
- verbindliche Transform-/Normalisierungsregeln
- bekannte Gaps inkl. Follow-up-Issues

> Scope: Mapping-/Transform-Spezifikation für den aktuellen API-MVP (`/analyze`) und die gruppierte API-Response-Struktur (`result.status` + `result.data`).

## 1) Ziel-Domainmodell (Kurzreferenz)

### 1.1 Primäres Domain-Objekt (`build_report`)

Hauptpfade:

- `query`, `matched_address`, `match.*`
- `ids.*`, `coordinates.*`, `administrative.*`
- `building.*`, `energy.*`, `address_registry.*`
- `cross_source.*`
- `intelligence.*`
- `sources`, `source_classification`, `source_attribution`, `field_provenance`

### 1.2 API-Projektion im Webservice

Der Webservice projiziert auf:

- `result.status.quality` (Confidence + Executive Summary)
- `result.status.source_health` (aus `sources`)
- `result.status.source_meta` (Classification/Attribution/Provenance)
- `result.data.entity` (Query/Adresse/IDs/Koordinaten/Administratives)
- `result.data.modules` (fachliche Module)
- `result.data.by_source` (quellenbezogene Gruppierung)

## 2) Verbindliche Transform-/Normalisierungsregeln

| Regel-ID | Regel | Beschreibung |
|---|---|---|
| `TR-01` | `trim_to_null` | Strings trimmen; leere/whitespace-only Werte als `null` behandeln. |
| `TR-02` | `html_strip` | HTML-Markup aus Label-/Description-Feldern entfernen (`strip_html`). |
| `TR-03` | `numeric_parse` | Numerische Felder robust in `float`/`int` parsen; bei Parse-Fehler `null`. |
| `TR-04` | `code_decode_gwr` | GWR-Codefelder per `gwr_codes.py` in Klartext zusammenführen (`building.decoded`, `energy.decoded_summary`). |
| `TR-05` | `enum/status_normalize` | Quellenstatus auf kontrolliertes Set normalisieren (`ok`, `partial`, `error`, `disabled`, `not_used`). |
| `TR-06` | `confidence_clamp` | Konfidenz-/Score-Werte auf gültige Bereiche begrenzen (`0..1` bzw. `0..100`). |
| `TR-07` | `policy_rank_map` | Quellenautorität in Policy-Rang überführen (`official > licensed > community > web > local_mapping > unknown`). |
| `TR-08` | `observed_at_iso` | Zeitstempel für Evidenz auf ISO-8601 normalisieren (`UTC`). |

## 3) Feld-Mapping pro Quelle

## 3.1 `geoadmin_search` (swisstopo SearchServer)

| Quellfeld | Zielpfad(e) | Transformation |
|---|---|---|
| `results[].attrs.featureId` | `ids.feature_id`, `match.selected_feature_id` | `TR-01` |
| `results[].attrs.label` | `matched_address`, `match.candidates_preview[].label` | `TR-02` + `TR-01` |
| `results[].attrs.detail` | `match.candidates_preview[].detail` | `TR-02` + `TR-01` |
| `results[].attrs.lat`, `results[].attrs.lon` | `coordinates.lat`, `coordinates.lon` | `TR-03` |
| `results[].attrs.origin`, `results[].attrs.rank` | `match.candidates_preview[].origin/rank` | `TR-01` + `TR-03` |

## 3.2 `geoadmin_address` (amtliches Gebäudeadressverzeichnis)

| Quellfeld | Zielpfad(e) | Transformation |
|---|---|---|
| `adr_egaid` | `address_registry.adr_egaid` | `TR-01` |
| `adr_status` | `address_registry.adr_status` | `TR-01` |
| `adr_official` | `address_registry.adr_official` | bool-normalisiert |
| `adr_modified` | `address_registry.adr_modified` | `TR-01` |
| `bdg_category` | `address_registry.bdg_category` | `TR-01` |

## 3.3 `geoadmin_gwr` (BFS GWR über geo.admin)

| Quellfeld | Zielpfad(e) | Transformation |
|---|---|---|
| `egid`, `egaid`, `egrid`, `esid`, `edid` | `ids.*` | `TR-01` |
| `gkode`, `gkodn` | `coordinates.lv95_e`, `coordinates.lv95_n` | `TR-03` |
| `strname_deinr`, `plz_plz6`, `dplzname`, `ggdename`, `ggdenr`, `gdekt` | `administrative.*` | `TR-01` + `TR-03` |
| `gbez`, `gbauj`, `gbaup`, `garea`, `gastw`, `ganzwhg` | `building.*` | `TR-01` + `TR-03` |
| `gwaerzh1/genh1/gwaerzh2/genh2/gwaerzw1/genw1/gwaerzw2/genw2` | `energy.raw_codes.*` | `TR-01` |

## 3.4 `bfs_heating_layer`

| Quellfeld | Zielpfad(e) | Transformation |
|---|---|---|
| `gwaerzh1_de`, `genh1_de`, `gwaersceh1_de`, `gwaerdath1`, `gexpdat` | `energy.heating_layer.*` | `TR-01` + `TR-08` (wo anwendbar) |

## 3.5 `gwr_codes` (lokales Decoding)

| Eingabefelder | Zielpfad(e) | Transformation |
|---|---|---|
| `energy.raw_codes.*` + ausgewählte GWR-Felder | `building.decoded`, `energy.decoded_summary` | `TR-04` |

## 3.6 `plz_layer_identify` (swisstopo PLZ-Ortschaft)

| Quellfeld | Zielpfad(e) | Transformation |
|---|---|---|
| `plz`, `zusziff`, `langtext`, `status`, `modified` | `cross_source.plz_layer.*` | `TR-01` |

## 3.7 `swissboundaries_identify`

| Quellfeld | Zielpfad(e) | Transformation |
|---|---|---|
| `gemname`, `gde_nr`, `kanton`, `jahr`, `is_current_jahr` | `cross_source.admin_boundary.*` | `TR-01` + `TR-03` |

## 3.8 `swisstopo_height`

| Quellfeld | Zielpfad(e) | Transformation |
|---|---|---|
| `height` | `cross_source.elevation.height_m` | `TR-03` |

## 3.9 `osm_reverse`

| Quellfeld | Zielpfad(e) | Transformation |
|---|---|---|
| Nominatim Reverse-Response (adress-/kontextbezogen) | `cross_source.osm_reverse` | `TR-01` + passthrough-strukturiert |

## 3.10 `osm_poi_overpass`

| Quellfeld | Zielpfad(e) | Transformation |
|---|---|---|
| Overpass `elements[].tags`, Distanz/Koordinaten | `intelligence.tenants_businesses.*` | `TR-01` + `TR-03` + regelbasierte Kategoriezuordnung |
| Overpass `elements[]` (Signalgruppen) | `intelligence.environment_noise_risk.*` | gewichtete Heuristik + `TR-06` |

**Konfiguration (Overpass Query):**

- `OSM_POI_OVERPASS_TAG_KEYS` (CSV) – welche OSM-Tag-Keys abgefragt werden.
  Default: `shop,amenity,office,leisure,tourism,craft`
- `OSM_POI_OVERPASS_ELEMENT_TYPES` (CSV) – welche Element-Typen abgefragt werden.
  Default: `node,way,relation`

Ungültige Werte werden ignoriert; bei leerem Result fällt der Service auf Defaults zurück.

## 3.11 `google_news_rss` / `google_news_rss_city`

| Quellfeld | Zielpfad(e) | Transformation |
|---|---|---|
| RSS `item.title/link/source/pubDate/description` | `intelligence.incidents_timeline.events[]` / City-Ranking `city_safety.events[]` | `TR-01` + `TR-08` + heuristische Relevanz-/Konfidenzbewertung (`TR-06`) |

## 4) Source->Module-Zuordnung für `result.data.by_source`

| Source-Group | Quellen | Modulzuordnung |
|---|---|---|
| `match` | `geoadmin_search`, `geoadmin_address`, `geoadmin_gwr` | `match` |
| `building_energy` | `geoadmin_gwr`, `bfs_heating_layer`, `gwr_codes` | `building`, `energy` |
| `postal_consistency` | `plz_layer_identify`, `swissboundaries_identify`, `osm_reverse` | `cross_source` |
| `elevation_context` | `swisstopo_height` | `cross_source` |
| `intelligence` | `osm_poi_overpass`, `google_news_rss` | `intelligence` |

## 5) Gaps / Follow-up-Issues

Die folgenden Gaps wurden aus BL-20.2.b abgeleitet und als eigenständige Backlog-Issues angelegt:

1. **#63** — Machine-readable Feldmapping-Spezifikation (YAML/JSON)
2. **#64** — Normalisierungs-/Transform-Regeln als wiederverwendbare Functions + Tests
3. **#65** — Source-Schema-Drift-Checks für Mapping-relevante Felder

Diese Follow-ups sind im Parent-/Issue-Kontext von #25 zu verlinken und priorisiert weiterzuführen.

## 6) Machine-readable Spezifikation (Issue #63)

Für Pipeline-/Service-Checks liegt die Spezifikation zusätzlich maschinenlesbar vor:

- JSON-Schema: [`docs/mapping/source-field-mapping.schema.json`](mapping/source-field-mapping.schema.json)
- Konkrete CH-v1-Spezifikation: [`docs/mapping/source-field-mapping.ch.v1.json`](mapping/source-field-mapping.ch.v1.json)
- Struktureller Validator: [`scripts/validate_source_field_mapping_spec.py`](../scripts/validate_source_field_mapping_spec.py)

Validierung (lokal/CI):

```bash
python3 scripts/validate_source_field_mapping_spec.py
```

Versionierungsregel:

- Jede inhaltliche Mapping-Änderung aktualisiert `updated_at` in `source-field-mapping.ch.v1.json`.
- Breaking Changes im Format erfordern eine neue `spec_version` + Folgedatei (z. B. `...ch.v2.json`).

## 7) Implementierte Rule-Functions (Issue #64)

Die wiederverwendbaren Transform-/Normalisierungsfunktionen liegen in:

- [`src/mapping_transform_rules.py`](../src/mapping_transform_rules.py)

Abdeckung:

- `TR-01` `trim_to_null`
- `TR-02` `html_strip`
- `TR-03` `numeric_parse`
- `TR-05` `normalize_source_status`
- `TR-06` `confidence_clamp`
- `TR-07` `policy_rank_map`
- `TR-08` `normalize_observed_at_iso`

`TR-04` (`code_decode_gwr`) bleibt bewusst domänenspezifisch und läuft weiterhin über `src/gwr_codes.py` + Address-Flow.

Golden-Tests (inkl. Edge-Cases) liegen in:

- [`tests/data/mapping/transform_rules_golden.json`](../tests/data/mapping/transform_rules_golden.json)
- [`tests/test_mapping_transform_rules.py`](../tests/test_mapping_transform_rules.py)

Einsatzgrenzen/Hinweise:

- `numeric_parse` ist absichtlich konservativ und liefert bei uneindeutigen Formaten `null` statt stiller Fehlinterpretation.
- `normalize_observed_at_iso` akzeptiert ISO-Strings, RFC2822-Strings und Epoch-Timestamps; unklare Werte werden zu `null` normalisiert.
- `normalize_source_status` mappt nur auf das kontrollierte Set (`ok`, `partial`, `error`, `disabled`, `not_used`).

## 8) Source-Schema-Drift-Check (Issue #65)

Für reproduzierbare Drift-Erkennung liegt ein read-only Check vor:

- Script: [`scripts/check_source_field_mapping_drift.py`](../scripts/check_source_field_mapping_drift.py)
- Referenz-Samples: [`tests/data/mapping/source_schema_samples.ch.v1.json`](../tests/data/mapping/source_schema_samples.ch.v1.json)

Ausführung (lokal/CI):

```bash
python3 scripts/check_source_field_mapping_drift.py
```

Optional gezielt pro Source:

```bash
python3 scripts/check_source_field_mapping_drift.py --source geoadmin_search --source geoadmin_gwr --source bfs_heating_layer
```

Interpretation/Behebung (Runbook-Hinweis):

1. **Fehlermeldung lesen**: Der Check meldet Source + erwartetes Feld (z. B. `results[].attrs.lon`).
2. **Drift verifizieren**: Gegen aktuelle Upstream-Response prüfen, ob Feld entfernt/umbenannt/verschachtelt wurde.
3. **Entscheiden**:
   - Mapping-Spec anpassen, wenn Upstream-Änderung korrekt und gewollt ist.
   - Ingestion/Parser korrigieren, wenn nur unser Zugriffspfad falsch ist.
4. **Absichern**: Samples + Tests aktualisieren und Check erneut grün laufen lassen.

## 9) Referenzen

- Quelleninventar/Lizenzmatrix: [`docs/DATA_SOURCE_INVENTORY_CH.md`](DATA_SOURCE_INVENTORY_CH.md)
- Produktvision: [`docs/VISION_PRODUCT.md`](VISION_PRODUCT.md)
- API-Contract v1: [`docs/api/contract-v1.md`](api/contract-v1.md)
- Konsolidierter Backlog: [`docs/BACKLOG.md`](BACKLOG.md)
