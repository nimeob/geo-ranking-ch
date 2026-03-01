# BL-30.5.wp2 — Datenquellen-/Lizenzmatrix für Map- und Bau-/Zufahrtslayer

Stand: 2026-03-01  
Bezug: #495 (Parent #110, Epic #128)

## Kontext und Ziel

Für BL-30.5 liegt mit #494 bereits der Karten-Workflow vor. Dieses Work-Package (#495) fixiert nun den belastbaren Daten-/Lizenzrahmen, damit die nächste Iteration (#496, Response-Modell) auf klaren Quellen- und Compliance-Entscheiden aufbaut.

## Entscheidungsrahmen (v1)

- **GO:** Quelle kann im MVP additiv genutzt werden, sofern dokumentierte Auflagen eingehalten werden.
- **NEEDS_CLARIFICATION:** fachlich nutzbar, aber vor produktiver Skalierung ist ein konkreter Betriebs-/Lizenzentscheid erforderlich.
- **BLOCKED:** aktuell keine belastbare Quelle/Regel für produktive Nutzung vorhanden.

## 1) Datenklassen-Matrix (Map + Bau-/Zufahrtskontext)

| Datenklasse | Primärquelle (v1) | Fallback-Quelle (v1) | Lizenz-/Nutzungsauflagen (Kurzfassung) | Betriebs-/Qualitätsgrenzen | Entscheid |
|---|---|---|---|---|---|
| **Basemap (Kartenrendering)** | OpenStreetMap (OSM) Tiles / OSM-basierte Kachelquelle | swisstopo/geo.admin.ch WMTS-Layer (konfigurierbar pro Umgebung) | OSM: ODbL + Attribution verpflichtend; swisstopo: datensatzspezifische Nutzungsbedingungen + Quellenangabe | Öffentliche OSM-Tile-Endpunkte nicht als unlimitierter Produktionspfad verwenden; Caching-/Rate-Policy muss explizit festgelegt werden | **NEEDS_CLARIFICATION** |
| **Gebäude-/Parzellennähe** | swisstopo/geo.admin.ch (amtliche Building-/Parcel-nahe Layer) + BFS GWR-Registerkontext | OSM Building-Polygone für degradierten Kontextpfad | Amtliche Quellen i. d. R. nutzbar mit Auflagen (Attribution, datensatzspezifische Bedingungen); OSM-Fallback unter ODbL-Auflagen | Feld-/Layer-Verfügbarkeit kann regional/versionsabhängig schwanken; `as_of`/Version muss pro Run mitgeführt werden | **GO** |
| **Topografie/Hangneigung** | swisstopo Höhen-/Geländelayer (z. B. Height/Relief-Derivate über geo.admin.ch) | Öffentliche DEM-Derivate mit niedrigerer Auflösung (nur degradiert) | swisstopo-Nutzung mit Quellenpflicht; Fallback nur mit dokumentierter Qualitätskennzeichnung | Slope-Berechnung ist auf gewählte Rasterauflösung sensitiv; Ergebnis muss Confidence-/Precision-Hinweis tragen | **GO** |
| **Straßentyp/Zufahrtsrelevanz** | OSM Highway-/Access-/Surface-Tags (Klassifikation) | swisstopo Verkehrs-/Straßenkontextlayer für Plausibilisierung | OSM unter ODbL mit Attribution; amtliche Layer gemäß jeweiligen Nutzungsbedingungen | Tags sind community-getrieben und nicht flächendeckend konsistent; für Kran-/Schwertransport-Eignung nur indikativ ohne Rechtszusicherung | **NEEDS_CLARIFICATION** |
| **Kran-/Schwerlast-Zufahrtsfreigabe (rechtsverbindlich)** | _Keine belastbare Open-Primary im aktuellen Scope_ | Manuelle Prüfung / kantonale Detailprozesse außerhalb MVP | Keine pauschale Rechtsableitung aus OSM/swisstopo-Basisschichten zulässig | Ohne rechtsverbindliche Quelle kein automatisiertes „freigegeben“-Signal im Produkt | **BLOCKED** |

## 2) Compliance-Mindeststandard für BL-30.5

1. **Attribution sichtbar und reproduzierbar:**
   - UI: Datenquellenhinweis im Karten-/Ergebnisbereich
   - API: `result.status.source_meta` enthält Quelle + License-Hinweis
   - Exporte: Quellenblock mit Stand (`as_of`) und Lizenzhinweis
2. **Keine stillen Lizenzannahmen:**
   - Jede neue Karten-/Bauquelle wird erst nach dokumentierter Matrix-Erweiterung aktiviert.
3. **Degraded-Pfade transparent:**
   - Fallback-Nutzung muss als reduzierte Qualität erkennbar sein (Status/Confidence).

## 3) Offene Risiken / Follow-ups

- **#498** — OSM-Tile-/ODbL-Compliance-Entscheid für produktiven Kartenbetrieb (Tile-Strategie, Caching, Share-Alike-Trigger).
- **#496** — Response-Modell v1 muss pro Datenklasse source-/confidence-/license-nahe Felder additiv aufnehmen.
- Für rechtsverbindliche Zufahrtsfreigaben bleibt der Scope im MVP bewusst **blocked**; nur indikative Klassifikation wird unterstützt.

## 4) Definition-of-Done-Check (#495)

- [x] Basemap, Gebäude-/Parzellennähe, Topografie und Straßentyp mit Primär-/Fallback-Quelle dokumentiert.
- [x] Lizenz-/Nutzungsauflagen sowie Betriebsgrenzen je Datenklasse transparent gemacht.
- [x] Decision-Frame `GO / NEEDS_CLARIFICATION / BLOCKED` inkl. Folge-Issues verankert.
- [x] Doku-Regression ergänzt (`tests/test_bl30_osm_data_license_matrix_docs.py`).
- [x] Backlog-/Parent-Sync vorbereitet (Issue #110 / `docs/BACKLOG.md`).
