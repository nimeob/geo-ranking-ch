# Address-Intel Flow Deep Dive

> Scope: BL-YY.3.a / Issue #272

## Zweck
Diese Seite beschreibt den End-to-End-Flow für adressbasierte Analysen (`POST /analyze`) von der Anfrage bis zur gruppierten Response – inklusive Source-Policy je `intelligence_mode` und Fehler-Mapping.

## Einstiegspunkte
- HTTP-Entry (kanonisch): [`src/api/web_service.py`](../../src/api/web_service.py) (`Handler.do_POST` für `/analyze`)
- Legacy-Kompatibilität: [`src/web_service.py`](../../src/web_service.py) als Wrapper auf den kanonischen API-Entrypoint
- Domain-Entry: [`src/address_intel.py`](../../src/address_intel.py) (`build_report(...)`)

## End-to-End Ablauf

```text
/analyze request
  -> Input-/Mode-/Timeout-Validierung (web_service)
  -> build_report(query, intelligence_mode, timeout, retries, ...)
     -> search_candidates (SearchServer)
     -> build_candidate_list + hydrate_candidates (Address + GWR)
     -> heating/plz/admin/elevation + osm_reverse
     -> confidence + suitability_light
     -> build_intelligence_layers (mode-abhängig)
     -> source_health/source_meta + compact summary + report payload
  -> grouped response projection (status vs data)
  -> JSON response (ok/error + request_id)
```

## Pipeline-Details (Domain)

### 1) Candidate Discovery
- `search_candidates(...)` holt Kandidaten aus `geoadmin_search`.
- `build_candidate_list(...)` bewertet Kandidaten heuristisch.
- `hydrate_candidates(...)` lädt Kandidatendetails (`geoadmin_address`, `geoadmin_gwr`) und wählt den belastbarsten Treffer.

### 2) Datenanreicherung
Auf Basis des selektierten Kandidaten:
- Gebäude-/Adressattribute (GWR + Gebäudeadressverzeichnis)
- Heiz-Layer (`bfs_heating_layer`, falls EGID vorhanden)
- PLZ-/Boundary-Konsistenz (`plz_layer_identify`, `swissboundaries_identify`)
- Höhenwert (`swisstopo_height`)
- Reverse-Geocoding (`osm_reverse`, sofern nicht deaktiviert)
- Lokales Mapping (`gwr_codes`)
- Gebäudekernfeld-Aggregation (`build_building_core_profile`): priorisiert GWR-Kernwerte, nutzt bei Lücken robuste Fallbacks aus dekodierten Feldern und bereinigt Placeholder-/Invalid-Werte auf `null`.

### 3) Scoring & Intelligenz
- `compute_confidence(...)`: Match-/Konsistenz-/Quellen-Confidence
- `evaluate_suitability_light(...)`: Light-Eignungsheuristik
- `build_intelligence_layers(...)`: mode-abhängige Zusatzlayer (Tenants/Incidents/Noise/Executive Risk)

### 4) Response-Aufbau
`build_report(...)` liefert ein vollständiges Domain-Reportobjekt. `src/api/web_service.py` projiziert dieses anschließend in die API-Form:
- `result.status`: Qualität, Quellenzustand, Metadaten, Personalisierungsstatus
- `result.data`: Entity-, Modul- und by_source-Daten

Siehe auch:
- [`docs/api/contract-v1.md`](contract-v1.md)
- [`docs/api/address-resolution-strategy.md`](address-resolution-strategy.md)
- [`docs/api/scoring_methodology.md`](scoring_methodology.md)
- [`docs/testing/WEB_SERVICE_RESULT_PATH_COVERAGE.md`](../testing/WEB_SERVICE_RESULT_PATH_COVERAGE.md)

## Source-Policy je `intelligence_mode`

Grundsatz: `official > licensed > community > web > local_mapping > unknown` (siehe `SOURCE_POLICY_ORDER` in `src/address_intel.py`).

| Mode | Externe Signallayer (`osm_poi_overpass`, `google_news_rss`) | Charakteristik |
|---|---|---|
| `basic` | deaktiviert (`disabled_by_mode`) | Fokus auf amtliche Kernquellen + robuste Basisanalyse |
| `extended` | aktiviert | breitere Kontextsignale (POI/Incidents), moderat |
| `risk` | aktiviert (größere Limits, konservativer) | stärkere Risiko-Betrachtung und höhere Sensitivität |

Implementierung: `intelligence_mode_settings(mode)` + Verzweigung in `build_intelligence_layers(...)`.

### POI-Fallback bei dünner Datenlage (adaptiver Radius)

Problem: In manchen Regionen ist die OSM-POI-Datenlage im Default-Radius sehr dünn. Damit `environment_profile`/Noise-/Tenant-Layer nicht auf einer quasi-leeren Stichprobe basieren, wird ein kleiner, deterministischer Fallback angewendet.

**Trigger:** Wenn `poi_count < poi_fallback_min_pois`.

**Fallback-Strategie:** bis zu `poi_fallback_max_steps` zusätzliche Overpass-Abfragen mit wachsendem Radius (`poi_fallback_radius_growth` pro Schritt), gedeckelt durch `poi_fallback_max_radius_m`.

**Signal im Result:** Wenn Fallback aktiv war *oder* das Fallback-Limit erreicht wurde, setzt der Service in `intelligence.environment_profile`:
- `low_confidence: true`
- `low_confidence_reason: <string>`
- `fallback: { threshold_min_pois, max_steps, radius_growth, max_radius_m, attempts[], ... }`

**Default-Parameter (Stand März 2026):**
- `risk`: `poi_fallback_min_pois=24`, `poi_fallback_max_steps=2`, `poi_fallback_radius_growth=1.6`, `poi_fallback_max_radius_m=900`
- `extended`: `poi_fallback_min_pois=18`, `poi_fallback_max_steps=2`, `poi_fallback_radius_growth=1.6`, `poi_fallback_max_radius_m=900`
- `basic`: Fallback deaktiviert (`poi_fallback_min_pois=0`, `poi_fallback_max_steps=0`)

## Fehler-Mapping (Service)

`src/api/web_service.py` mappt Fehler deterministisch auf HTTP-Codes:

| Fehlerklasse | HTTP | `error`-Feld |
|---|---:|---|
| `TimeoutError` | 504 | `timeout` |
| `AddressIntelError` (inkl. `NoAddressMatchError`, `ExternalRequestError`) | 422 | `address_intel` |
| `ValueError` / `JSONDecodeError` | 400 | `bad_request` |
| sonstige Exception | 500 | `internal` |

Dadurch bleibt zwischen Eingabe-/Domain-/Runtime-Fehlern klar unterscheidbar.

## Betriebs- und Diagnosehinweise
- Die gruppierte Response trennt strikt `status` (Qualität/Source-Health) und `data` (Fachdaten).
- Für Reproduzierbarkeit kann `X-Request-Id` gesetzt werden; die ID wird in Header + JSON gespiegelt.
- Für mode-bezogene Fehlersuche zuerst `result.status.source_health` und `result.status.quality` prüfen.
