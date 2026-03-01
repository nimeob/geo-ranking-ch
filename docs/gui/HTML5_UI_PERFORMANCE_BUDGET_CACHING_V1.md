# BL-30.4.wp3 — Performance-Budget + Browser-Caching-Strategie v1

## Kontext und Ziel

Dieses Dokument spezifiziert für **BL-30.4.wp3 / Issue #481** die verbindlichen Performance- und Caching-Leitplanken für die dynamische HTML5-UI.
Es baut auf der Architektur- und Event-Basis aus [`docs/gui/HTML5_UI_ARCHITECTURE_V1.md`](./HTML5_UI_ARCHITECTURE_V1.md) und [`docs/gui/HTML5_UI_STATE_INTERACTION_CONTRACT_V1.md`](./HTML5_UI_STATE_INTERACTION_CONTRACT_V1.md) auf.

Referenzen:
- Parent: #108
- Abhängigkeit: #480
- Runtime-/Contract-Gates: #6, #127

## 1) Performance-Budget v1 (LCP/TTI/Input-Latency/Request-Limits)

Die v1-Budgets sind produktionsnah, aber konservativ, damit spätere UX-Erweiterungen (#482) innerhalb einer stabilen Leitplanke passieren.

| Metrik | Zielwert (p75) | Hard-Fail-Grenze | Messkontext |
|---|---:|---:|---|
| LCP | <= 2.5s | > 3.5s | Initiales Laden der GUI (`/gui`) |
| TTI | <= 3.0s | > 4.0s | Erste interaktive Analyse-Aktion ohne Blockade |
| Input-Latency | <= 100ms | > 200ms | Submit/Map-Interaktion bis visuelles Feedback |
| API Request-Dauer (`/analyze`) | <= 2.0s (`basic`) / <= 3.0s (`extended`) / <= 4.0s (`risk`) | jeweilig +1.0s | UI→API Request-Lifecycle |
| Gleichzeitige aktive Analyze-Requests | 1 | > 1 | Single-Flight-Regel aus wp2 |

Normative Regeln:
1. `loading` muss innerhalb des mode-spezifischen Budgets deterministisch in `success` oder `error` enden.
2. UI darf keinen zweiten Analyze-Request starten, solange ein laufender Request aktiv ist.
3. Budget-Verletzungen sind Telemetrie-relevant und müssen in der Diagnosekette sichtbar werden.

## 2) Messmethode + Telemetrie-Mindeststandard

### 2.1 Web-Performance-Messung

- Core-Metriken im Browser werden über `PerformanceObserver` erfasst (LCP) und um Interaktionsmessungen für TTI/Input-Latency ergänzt.
- Für Analyze-Läufe gelten `ui.api.request.start` und `ui.api.request.end` als kanonische Messanker.

### 2.2 Pflichtfelder je Analyze-Lauf

Jeder Lauf muss mindestens folgende Korrelation enthalten:
- `request_id` (Header `X-Request-Id`)
- `session_id` (Header `X-Session-Id`)
- `mode` (`basic|extended|risk`)
- `phase_from` / `phase_to` aus `ui.state.transition`
- `duration_ms`
- `status` (`ok|error|timeout|network_error`)

### 2.3 Messfenster und Bewertungsregel

- Primäre Steuergröße ist p75 über ein gleitendes Fenster von mindestens 200 Analyze-Ereignissen.
- Hard-Fail-Grenzen dürfen in keinem Release-Gate überschritten werden.
- p95 wird ergänzend dokumentiert, ist aber in v1 kein harter Gate-Blocker.

## 3) Browser-Caching-Strategie nach Datenklasse

| Datenklasse | Beispiel | Strategie | TTL | Storage |
|---|---|---|---|---|
| API Analyze-Responses (gleiche Eingabe + gleiche Optionen) | `POST /analyze` Ergebnisprojektion | Kurzzeit-Cache (SWR) mit Schlüssel aus normalisierter Query/Coordinates + Mode + relevanten Options | 60s soft / 120s hard | In-Memory (Session-gebunden) |
| Capability-/Entitlement-nahe Statusfelder | `result.status.capabilities`, `result.status.entitlements` | Immer an frischem API-Resultat ausrichten (kein persistenter Browser-Cache) | 0s | kein persistenter Cache |
| Karten-Tiles | OSM/Tiles | HTTP-Caching gemäß Server-Header (`Cache-Control`, `ETag`) mit `stale-while-revalidate` wenn vorhanden | nach Header | Browser HTTP Cache |
| Statische UI-Assets | JS/CSS/Fonts | Fingerprint-basierter Asset-Cache (`Cache-Control: immutable`) | langlaufend | Browser HTTP Cache |
| Trace-/Debug-Antworten | `/debug/trace` | Kein langlebiger Client-Cache, nur kurzzeitige Session-Wiederverwendung | <= 30s | In-Memory |

Normative Regeln:
1. Keine lokale Dauerpersistenz fachlicher Analyze-Ergebnisse (`localStorage`/`IndexedDB`) in v1.
2. Cache-Key für Analyze darf keine instabilen Zufallsfelder enthalten.
3. Entitlement-relevante Informationen dürfen nicht aus veraltetem Persistent-Cache gerendert werden.

## 4) Invalidation-/Revalidation-Regeln

### 4.1 Trigger für Invalidation

- Wechsel von `mode`, `options.response_mode`, `preferences` oder Entitlement-/Capability-Kontext invalidiert Analyze-Cache sofort.
- Neue User-Interaktion (`ui.input.accepted`) mit anderer Query/Koordinate invalidiert vorherigen Analyze-Key.
- API-Fehlerantworten werden nicht als positive Cache-Treffer wiederverwendet.

### 4.2 Revalidation-Mechanik

- Analyze-Cache nutzt `stale-while-revalidate`: sofortige Anzeige nur bei frischem Short-TTL-Treffer, im Hintergrund Re-Fetch zur Drift-Minimierung.
- Tile-/Asset-Caches folgen Server-Vorgaben (`ETag`, `Cache-Control`) und nutzen Conditional Requests.
- Bei unklarer Cache-Frische hat API-Frischdatenabruf Vorrang vor UI-Reaktivität.

### 4.3 Sicherheits-/Konsistenz-Guardrails

- Kein Caching von Auth-/Secret-Headern oder sensitiven Debug-Details.
- Timeout-/Error-Runs dürfen keinen „success“-Cacheeintrag überschreiben.
- Bei Schema-/Version-Drift wird Cache-Key-Version erhöht und Altbestand verworfen.

## 5) Auswertungsablauf (Perf-/UX-Diagnostik)

Verbindlicher Diagnoseablauf pro Auffälligkeit:
1. Betroffene `request_id` identifizieren (UI-Result/Trace-Link).
2. `ui.state.transition` + `ui.api.request.start/end` auf Laufzeit und Fehlerklasse prüfen.
3. Korrelation mit API-Upstream-Timeline (`api.upstream.request.*`) herstellen.
4. Cache-Hit/Miss-Rate sowie Revalidation-Verhalten für die betroffene Datenklasse auswerten.
5. Ergebnis als Kurzbefund dokumentieren: Ursache, betroffener Budgetwert, nächster Fix-Schritt.

## 6) Nicht-Ziele (wp3)

- Keine finale UX-Mikrointeraktionsnorm und kein vollständiger Accessibility-Katalog (kommt in #482).
- Keine Einführung neuer Client-Persistenzspeicher für Offline-Betrieb.
- Keine Änderung des Backend-Contracts über additive Telemetrie-/Header-Korrelation hinaus.

## 7) Definition-of-Done-Check (#481)

- [x] Performance-Zielwerte und Messmethode dokumentiert
- [x] Caching-/Invalidation-Regeln pro Datenklasse dokumentiert
- [x] Telemetrie-Mindestfelder und Auswertungsablauf beschrieben
- [x] Regressionstest für Pflichtsektionen/Begriffe ergänzt
