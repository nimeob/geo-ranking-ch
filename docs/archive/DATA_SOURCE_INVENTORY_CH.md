# BL-20.2.a — Quelleninventar CH + Lizenzmatrix

Stand: 2026-02-26

## Zweck

Dieses Dokument führt die aktuell vorgesehenen CH-Datenquellen für BL-20 zusammen und macht pro Quelle transparent:

- **Wofür** die Quelle im Produkt genutzt wird
- **Welche fachliche/räumliche Abdeckung** vorhanden ist
- **Welche Lizenz-/Nutzungsgrenzen** für MVP und Betrieb relevant sind
- **Welche offenen Rechts-/Betriebsfragen** vor produktiver Skalierung geklärt werden müssen

> Scope dieses Dokuments: Produkt-/Delivery-Sicht für API+GUI-MVP. Keine Rechtsberatung.

## Quellenliste inkl. Zweck/Abdeckung

| Quelle | Primärer Zweck im Produkt | Räumliche Abdeckung | Fachliche Abdeckung (MVP) | Aktualität/Verfügbarkeit (Planungsstand) |
|---|---|---|---|---|
| **swisstopo / geo.admin.ch** | Geobasis-Layer, Referenzgeometrien, Standortkontext | Schweizweit (CH) | Basiskontext für Standort-/Gebäudeauswertung | Datensatz- und Service-abhängig; pro Layer separat zu prüfen |
| **BFS GWR (Gebäude- und Wohnungsregister)** | Gebäude-/Adressnahe Registerattribute für Gebäudeprofil | Schweizweit (CH) | Gebäudegrunddaten und strukturierte Registerinfos | Datensatz-/Exportabhängig; Versionsstand muss pro Pipeline mitgeführt werden |
| **OpenStreetMap (OSM)** | Ergänzende Open-Datenebenen (POI/Umfeldindikatoren) | Global, für CH nutzbar | Umfeldprofil (POI/Context) und ergänzende Kontextmetriken | Kontinuierliche Community-Updates; Snapshot-/Zeitstand muss versioniert werden |
| **Weitere öffentliche Quellen (domänenspezifisch)** | Optional für spätere Verticals (z. B. Lärm, Mobilität, Infrastruktur) | Quelle-spezifisch | Phase-2-Erweiterungen außerhalb des MVP-Kerns | Noch nicht final ausgewählt; Freigabe nur je konkret benannter Quelle |

## Lizenzmatrix inkl. Nutzungsgrenzen

| Quelle | Nutzbarkeit für kommerzielles Produkt | Pflichtauflagen (MVP-relevant) | Nutzungsgrenzen / Risiken | Aktueller Freigabestatus |
|---|---|---|---|---|
| **swisstopo / geo.admin.ch** | **Bedingt ja** (pro Datensatz/Service) | Quellenangabe und Einhaltung der datensatzspezifischen Nutzungsbedingungen | Keine pauschale Freigabe über alle Layer hinweg; Einschränkungen je Service möglich | ✅ Nutzbar mit Auflagen |
| **BFS GWR** | **Bedingt ja** (pro Datensatz/Publikation) | Quellenangabe und Übernahme datensatzspezifischer Hinweise/Bedingungen | Datensatzspezifische Bedingungen können je Feld/Export differieren | ✅ Nutzbar mit Auflagen |
| **OpenStreetMap (ODbL)** | **Ja**, unter ODbL-Bedingungen | Korrekte OSM-Attribution; ODbL-Pflichten bei Datenbank-/Derived-Data-Szenarien beachten | Risiko bei unklarer Trennung zwischen interner Verarbeitung und veröffentlichter Datenbank | ✅ Nutzbar mit Auflagen |
| **Weitere öffentliche Quellen** | **Unklar**, bis Einzelprüfung abgeschlossen | Keine | Ohne konkrete Quelle keine belastbare Lizenz-/Claim-Aussage möglich | ⛔ Vor Einzelfreigabe nicht in GTM-Claims nutzen |

## Offene Rechtsfragen (zu markieren vor breiter Skalierung)

1. **swisstopo-Layerliste finalisieren:**
   - Welche konkreten Layer/Services sind im MVP produktiv vorgesehen?
   - Sind für diese Layer zusätzliche Bedingungen (Attribution, Weitergabe, Caching) zu erfüllen?
2. **GWR-Feldnutzung präzisieren:**
   - Welche konkreten Registerfelder werden im API-Output exponiert?
   - Gibt es feldspezifische Einschränkungen für Weitergabe/Publikation?
3. **OSM-Weitergabemodell sauber festlegen:**
   - Welche Daten bleiben intern (Analyse), welche gehen in externe Artefakte/Exports?
   - Wo greifen ODbL-Pflichten bei abgeleiteten Datensätzen konkret?

## Offene Betriebsfragen (für reproduzierbaren Betrieb)

1. **Attribution-Mechanik standardisieren:**
   - Einheitliches Attribution-Format für API/GUI/Exports definieren.
2. **Versionierung & Reproduzierbarkeit sichern:**
   - Für jede Quelle `as_of`/Version/Snapshot im Datenpipeline-Metadatenmodell verankern.
3. **Update- und Drift-Management aufsetzen:**
   - Monitoring für Quellenänderungen (Schema, Lizenztext, Endpoint-Änderungen) etablieren.

## Mindestanforderungen für „Done“ je neue Quelle (ab sofort)

Eine neue Quelle gilt erst als BL-20.2-konform integriert, wenn alle Punkte erfüllt sind:

- [ ] Quelle namentlich mit Link auf Primärdokumentation erfasst
- [ ] Zweck + fachliche/räumliche Abdeckung dokumentiert
- [ ] Lizenz-/Nutzungsbedingungen inkl. Auflagen dokumentiert
- [ ] Offene Rechts-/Betriebsfragen explizit markiert oder als geklärt referenziert
- [ ] Geplante Attribution im Produkt benannt

## Referenzen

- Produktvision (BL-20): [`docs/../VISION_PRODUCT.md`](../VISION_PRODUCT.md)
- Feld-Mapping (BL-20.2.b): [`docs/../DATA_SOURCE_FIELD_MAPPING_CH.md`](../DATA_SOURCE_FIELD_MAPPING_CH.md)
- GTM Claim-Gate: [`docs/GTM_DATA_SOURCE_LICENSES.md`](GTM_DATA_SOURCE_LICENSES.md)
- Konsolidierter Backlog: [`docs/../BACKLOG.md`](../BACKLOG.md)
