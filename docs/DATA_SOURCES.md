# DATA_SOURCES.md — Datenquellen, Lizenzen & Feld-Mapping (kanonisch)

> Dieses Dokument ist der **kanonische Ort** für alle Datenquellen-Inhalte.
> Konsolidiert aus: `DATA_SOURCE_INVENTORY_CH.md` (BL-20.2.a), `GTM_DATA_SOURCE_LICENSES.md` (BL-20.7.r1).
> Feld-Mapping-Spezifikation: [`docs/DATA_SOURCE_FIELD_MAPPING_CH.md`](DATA_SOURCE_FIELD_MAPPING_CH.md) (BL-20.2.b, kanonisch).

Stand: 2026-03-01

---

## 1) Quelleninventar CH

*Quelle: `docs/archive/DATA_SOURCE_INVENTORY_CH.md` — BL-20.2.a*

| Quelle | Zweck im Produkt | Räumliche Abdeckung | Fachliche Abdeckung (MVP) | Aktualität |
|---|---|---|---|---|
| **swisstopo / geo.admin.ch** | Geobasis-Layer, Referenzgeometrien, Standortkontext | Schweizweit | Basiskontext für Standort-/Gebäudeauswertung | Datensatz-/Service-abhängig |
| **BFS GWR (Gebäude- und Wohnungsregister)** | Gebäude-/Adressnahe Registerattribute | Schweizweit | Gebäudegrunddaten und strukturierte Registerinfos | Export-/Versionsabhängig |
| **OpenStreetMap (OSM)** | Ergänzende Open-Datenebenen (POI/Umfeldindikatoren) | Global (für CH genutzt) | Umfeldprofil, POI/Context, Kontextmetriken | Kontinuierliche Community-Updates, Snapshot versionieren |
| **Weitere öffentliche Quellen** | Phase-2-Erweiterungen (Lärm, Mobilität, Infrastruktur) | Quelle-spezifisch | Noch nicht final ausgewählt | Vor Nutzung: Einzelfreigabe erforderlich |

---

## 2) Lizenz- & GTM-Claim-Matrix (MVP)

*Quelle: `docs/archive/GTM_DATA_SOURCE_LICENSES.md` — BL-20.7.r1*

| Quelle | Kommerziell nutzbar | Pflichtauflagen | Erlaubter GTM-Claim | Status |
|---|---|---|---|---|
| **swisstopo / geo.admin.ch** | Bedingt ja (pro Datensatz) | Quellenangabe + datensatzspezifische Bedingungen | „Nutzt offizielle CH-Geodatenquellen inkl. swisstopo/geo.admin.ch mit nachvollziehbarer Quellenangabe." | ✅ Freigegeben mit Auflagen |
| **BFS GWR** | Bedingt ja (pro Datensatz) | Quellenangabe + allfällige Datensatzhinweise | „Integriert öffentliche Registerdaten (z. B. GWR) mit dokumentierter Herkunft." | ✅ Freigegeben mit Auflagen |
| **OpenStreetMap (ODbL)** | Ja, mit ODbL-Auflagen | OSM-Attribution + ODbL-Anforderungen bei Datenbank-Weitergabe | „Ergänzt amtliche Daten um OSM-Daten unter ODbL inkl. erforderlicher Attribution." | ✅ Freigegeben mit Auflagen |
| **Weitere öffentliche Quellen (unspezifisch)** | Unklar bis Einzelfallprüfung | Keine pauschale Aussage | **Nicht verwenden.** Keine pauschalen Claims für nicht konkret benannte Quellen. | ⛔ Claim nicht verwenden |

### Verbindliche GTM-Guardrails

1. Keine Aussage „alle Daten kommerziell frei nutzbar".
2. Nur konkret benannte Quellen kommunizieren (swisstopo, GWR, OSM).
3. OSM-Attribution in Demo-/Marketing-Material einplanen.
4. Unspezifische Sammelbegriffe nur technisch, nicht lizenzrechtlich vermarkten.
5. Bei Unsicherheit: Claim streichen und als Follow-up dokumentieren.

---

## 3) Feld-Mapping (kanonisch)

**Detaillierte technische Spezifikation:** [`docs/DATA_SOURCE_FIELD_MAPPING_CH.md`](DATA_SOURCE_FIELD_MAPPING_CH.md) — BL-20.2.b

### Transform-Regeln (Überblick)

| Regel-ID | Beschreibung |
|---|---|
| `TR-01` | `trim_to_null`: Strings trimmen; leere Werte → `null` |
| `TR-02` | `html_strip`: HTML-Markup aus Label-/Description-Feldern |
| `TR-03` | `numeric_parse`: Numerische Felder robust parsen, bei Fehler `null` |
| `TR-04` | `code_decode_gwr`: GWR-Codes → Klartext via `gwr_codes.py` |
| `TR-05` | `enum/status_normalize`: Status → `ok|partial|error|disabled|not_used` |
| `TR-06` | `confidence_clamp`: Werte auf `0..1` bzw. `0..100` begrenzen |
| `TR-07` | `policy_rank_map`: Quellenautorität → Policy-Rang (`official > licensed > community > web > local_mapping > unknown`) |

**Mapping-Artefakte:** `docs/mapping/source-field-mapping.ch.v1.json`

---

## 4) Offene Rechtsfragen (vor breiter Skalierung)

1. **swisstopo-Layerliste finalisieren:** Welche Layer/Services sind im MVP produktiv vorgesehen? Zusätzliche Attribution-/Weitergabebedingungen?
2. **GWR-Feldnutzung präzisieren:** Welche Registerfelder werden exponiert? Feldspezifische Einschränkungen?
3. **OSM-Weitergabemodell:** Welche Daten bleiben intern, welche gehen in externe Artefakte/Exports? Wo greifen ODbL-Pflichten?

---

## 5) Mindestanforderungen für neue Quellen (ab sofort)

Eine neue Quelle gilt als BL-20.2-konform, wenn:
- [ ] Quelle namentlich mit Link auf Primärdokumentation erfasst
- [ ] Zweck + räumliche/fachliche Abdeckung dokumentiert
- [ ] Lizenz-/Nutzungsbedingungen inkl. Auflagen dokumentiert
- [ ] Offene Rechts-/Betriebsfragen explizit markiert oder als geklärt referenziert
- [ ] Geplante Attribution im Produkt benannt

---

## 6) Verweise

- Feld-Mapping-Spezifikation (kanonisch): [`docs/DATA_SOURCE_FIELD_MAPPING_CH.md`](DATA_SOURCE_FIELD_MAPPING_CH.md)
- GUI OSM-Lizenz-Matrix: [`docs/gui/OSM_MAP_DATA_SOURCE_LICENSE_MATRIX_V1.md`](gui/OSM_MAP_DATA_SOURCE_LICENSE_MATRIX_V1.md)
- GUI OSM-Compliance-Entscheid: [`docs/gui/OSM_TILE_ODBL_COMPLIANCE_DECISION_V1.md`](gui/OSM_TILE_ODBL_COMPLIANCE_DECISION_V1.md)
- Archivierte Quelldoks: `docs/archive/DATA_SOURCE_INVENTORY_CH.md`, `docs/archive/GTM_DATA_SOURCE_LICENSES.md`
