# BL-30.4.wp1 — HTML5-UI-Architektur v1 (ADR + Boundary-Guardrails)

## Kontext und Entscheidungsziel

BL-30.4 (#108) adressiert eine hochdynamische HTML5-UI als Produktschicht über der bestehenden API-first Architektur.
Der Parent-Scope war für eine sichere Iteration zu breit und wurde deshalb in atomare Work-Packages #479/#480/#481/#482 zerlegt.

Dieses Dokument fixiert für wp1 die verbindliche Architekturentscheidung (v1), damit die Folgepakete (State-/Interaktionsvertrag, Performance/Caching, UX-Standards) auf einer stabilen Basis aufsetzen können.

## Architektur-Entscheidung (v1)

Wir setzen auf eine **schrittweise Evolution** des bestehenden GUI-MVP statt auf einen Rebuild:

1. **UI-Shell bleibt serverseitig ausgeliefert** über den bestehenden UI-Service (`src/ui/service.py`).
2. **Clientseitige Feature-Module** erweitern die Interaktion additiv (Map, Results, Explainability, Trace).
3. **State-Orchestrierung im Browser** bleibt deterministisch über klar definierte Phasen (`idle/loading/success/error`) und späteren Event-Contract (wp2).
4. **API bleibt Single Source of Truth** für fachliche Ergebnisse (`POST /analyze`), UI enthält keine versteckte Fachlogik.

## Modulgrenzen und Ownership

### `src/ui`
- Verantwortlich für Auslieferung der UI-Shell und statischer Assets.
- Darf keine fachliche Bewertungslogik implementieren.

### `src/shared`
- Enthält wiederverwendbare GUI-Bausteine und Präsentationslogik.
- Muss API-Contract-kompatibel bleiben und additive Erweiterungen bevorzugen.

### `src/api`
- Bleibt alleiniger Ort für Analyse-/Scoring-/Entitlement-Entscheidungen.
- Liefert strukturierte Responses, die UI-seitig nur projiziert/visualisiert werden.

### Boundary-Regel
- Kein direkter Importpfad von UI-Komponenten in API-Fachmodule.
- Keine Duplizierung von API-Validierungsregeln im Browser.

## State-Ownership und Render-Pfad (v1)

- **State-Owner:** Browser-Client (UI Runtime) für Interaktionszustand und Anzeigezustand.
- **Domain-Owner:** API für fachliche Ergebnisse und Capability-/Entitlement-Signale.
- **Render-Pfad:** Input/Kartenaktion -> Request-Build (UI) -> `POST /analyze` -> normalisierte Response-Projektion -> UI-Rendering.

Verbindliche Leitplanken:
- Requests sind abbrechbar (Timeout/Cancel), UI endet immer in terminalem Zustand (`success` oder `error`).
- Explainability-/Scoring-Darstellung bleibt tolerant gegenüber additiven Response-Feldern.
- Trace-/Debug-Funktionalität ist Diagnosehilfe und kein Hard-Dependency-Pfad für Kern-UX.

## Forward-Compatibility-Guardrails (#6, #127)

Die folgenden Constraints sind für BL-30.4 verbindlich:

1. **Additive Contract-Evolution only:** keine breaking Änderungen am bestehenden Analyze-Contract.
2. **API-first Erweiterung:** neue UI-Fähigkeiten müssen über dokumentierte API-Felder anschließbar sein.
3. **Keine Rebuild-Abkürzungen:** BL-20/BL-31-Basis wird erweitert, nicht ersetzt.
4. **Packaging-/Entitlement-Kompatibilität:** UI zeigt Capability-/Entitlement-Signale konsistent, ohne lokale Geschäftsregeln zu erfinden.

## Nicht-Ziele (wp1)

- Keine endgültige Festlegung aller UI-Events/Transitions (kommt in #480).
- Keine Performance-Budgetzahlen oder Cache-Messmethodik (kommt in #481).
- Keine vollständige UX-/Accessibility-Checkliste für Explainability-Views (kommt in #482).

## Nachgelagerte Work-Packages

- #480 — Zustandsmodell + Interaktions-Contract
- #481 — Performance-Budget + Browser-Caching-Strategie
- #482 — Explainability-/Scoring-UX-Standards

## Definition-of-Done-Check (#479)

- [x] Zielbild/Entscheid dokumentiert
- [x] Modulgrenzen und Ownership festgelegt
- [x] Guardrails #6/#127 explizit referenziert
- [x] Folgeschritte für BL-30.4 verankert
