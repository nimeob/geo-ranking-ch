# BL-30.5.wp1 — Karten-Workflow-Spec v1 (Map-Pick -> Analyze -> Result)

## Kontext und Ziel

BL-30.5 (#110) adressiert einen vollständigen OSM-Map-Intelligence-Flow, ist im Parent jedoch zu breit für eine risikoarme Einzeliteration.
Dieses Work-Package (#494) fixiert deshalb zuerst den verbindlichen Workflow-Rahmen (UI + API-Verknüpfung), damit Folgepakete für Daten/Lizenzen (#495) und Response-Modell (#496) sauber anschließen können.

## 1) End-to-End Workflow (v1)

1. **Map ready (`idle`)**  
   UI zeigt Basemap + Interaktionshinweis („Punkt wählen").
2. **Map pick (`input_selected`)**  
   Nutzer klickt auf Karte; UI übernimmt `coordinates.lat/lon` (WGS84).
3. **Analyze request (`loading`)**  
   UI sendet `POST /analyze` mit Karten-Input (ohne Breaking-Änderung bestehender Address-Flows).
4. **Analyze response (`success`)**  
   UI rendert Kernresultate (Standort-/Bauindikatoren) inkl. Quellen-/Confidence-Hinweisen.
5. **Error/Timeout (`error`)**  
   UI zeigt deterministischen Fehlerzustand mit Retry-Option; Loading endet immer terminal.

## 2) Request-/Response-Handshake (additiver Kartenpfad)

### Request-Envelope (relevant für Map-Pick)

- `query`: optional (Map-first kann ohne freie Adresse laufen)
- `coordinates.lat` / `coordinates.lon`: Pflicht im Kartenpfad
- `options.intelligence_mode`: optional (`basic|extended|risk`)
- `options.timeout_seconds`: optional, finite Zahl > 0
- `options.response_mode`: optional (`compact|verbose`)

### Erwartete Response-Pfade (v1)

- `ok=true` + `result.status` + `result.data` im grouped Contract
- `result.status.source_health` und `result.status.source_meta` für Quellen-/Verfügbarkeitskontext
- `result.data.entity`/`result.data.modules` als UI-Renderquelle

## 3) UI-State- und Fehlerpfad-Regeln

### Verbindliche States
- `idle`
- `loading`
- `success`
- `error`

### Fehler-/Degraded-Pfade
- **Timeout (504):** UI meldet „Analyse dauert zu lange", bietet Retry und optional Mode-Wechsel (`extended -> basic`).
- **Bad Request (400):** UI zeigt validierungsnahe Meldung (z. B. ungültige Koordinaten).
- **Auth (401):** UI zeigt Access-Hinweis ohne Roh-Tokeninformationen.
- **Upstream partial/degraded:** UI zeigt Resultat weiterhin, markiert reduzierte Datentiefe transparent über Statusfelder.

## 4) Additive Kompatibilität zu `POST /analyze`

- Kein Breaking-Change am bestehenden Address-Flow.
- Kartenpfad bleibt ein **zusätzlicher Input-Pfad** über bestehende Contract-Mechanik.
- Bestehende grouped Response-Konventionen (`result.status` vs. `result.data`) bleiben unverändert.
- Existing Request-ID-/Correlation-Mechanik bleibt aktiv für Traceability.

## 5) Telemetrie-/Trace-Mindestanforderungen

- UI-seitig: `ui.api.request.start`, `ui.api.request.end`
- API-seitig: `api.request.start`, `api.request.end`
- Bei Kartenpfad zusätzlich erkennbar: Input-Typ `coordinates` + Request-ID-Korrelation

## 6) Offene Folgepunkte (explizit nicht Teil von wp1)

- #495 — Datenquellen-/Lizenzmatrix für Map-/Bau-/Zufahrtslayer
- #496 — Response-Modell v1 für Bau-/Zufahrtseignung

## 7) Definition-of-Done-Check (#494)

- [x] End-to-end Workflow für Map-Pick dokumentiert
- [x] Additive Contract-Kompatibilität festgehalten
- [x] State-/Error-Regeln inkl. Retry/Degraded beschrieben
- [x] Folgepakete #495/#496 klar abgegrenzt
