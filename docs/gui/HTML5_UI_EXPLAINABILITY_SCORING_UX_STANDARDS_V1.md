# BL-30.4.wp4 — Explainability-/Scoring-UX-Standards v1 (Desktop + Tablet)

## Kontext und Ziel

Dieses Dokument definiert für **BL-30.4.wp4 / Issue #482** die verbindlichen UX-Standards für Explainability- und Scoring-Ansichten in der HTML5-UI.
Es baut auf den vorherigen BL-30.4-Work-Packages auf:

- Architektur/Boundary-Guardrails: [`docs/gui/HTML5_UI_ARCHITECTURE_V1.md`](./HTML5_UI_ARCHITECTURE_V1.md)
- Zustands-/Interaktions-Contract: [`docs/gui/HTML5_UI_STATE_INTERACTION_CONTRACT_V1.md`](./HTML5_UI_STATE_INTERACTION_CONTRACT_V1.md)
- Performance-/Caching-Leitplanken: [`docs/gui/HTML5_UI_PERFORMANCE_BUDGET_CACHING_V1.md`](./HTML5_UI_PERFORMANCE_BUDGET_CACHING_V1.md)

Referenzen:
- Parent: #108
- Dependencies: #474, #475
- Runtime-/Contract-Gates: #6, #127

## 1) UX-Grundsätze für Explainability und Scoring

1. **Decision-first Darstellung:** Nutzer sollen zuerst die zentrale Entscheidung sehen (Score/Status), dann die Begründungslayer.
2. **Nachvollziehbarkeit vor Dichte:** Pro Ansicht maximal 3 primäre Key-Faktoren „above the fold“, Details über progressive disclosure.
3. **Kontexttreue:** Score-Werte immer zusammen mit Referenzrahmen anzeigen (Skala, Bedeutung, Unsicherheit/Confidence).
4. **Keine UI-Eigenlogik:** Explainability und Scoring werden ausschließlich aus API-Feldern projiziert; keine lokale Neuberechnung.
5. **Fehlertransparenz:** Bei Teil-/Fehlpfaden klare User-Sprache mit technischem Diagnoseanker (`request_id`/Trace-Link).

## 2) Visualisierungsnorm (Score + Explainability)

### 2.1 Score-Komponente (kanonisch)

Pflichtfelder in der UI-Darstellung:
- `score_label` (z. B. „Eignung“)
- `score_value` (numerisch)
- `score_scale` (z. B. `0..100`)
- `confidence` (Band + verbale Einordnung)
- `as_of` (Datenstand)

Pflichtregeln:
1. Numerischer Score nie ohne Skala rendern.
2. Confidence immer sichtbar (Badge/Text), nicht nur im Tooltip.
3. Farbcode nie als einziges Signal verwenden (zusätzlich Icon/Text).

### 2.2 Explainability-Komponente (kanonisch)

Pflichtdarstellung je Hauptfaktor:
- Faktorname
- Richtung/Einfluss (`+`, `-`, neutral)
- relative Stärke (z. B. hoch/mittel/niedrig)
- Herkunft/Quelle (mindestens `source` oder `derived_from`)

Reihenfolge:
1. Top positive Faktoren
2. Top limitierende Faktoren
3. optional: weitere Faktoren (eingeklappt)

## 3) Progressive Disclosure + Fehlermeldungsrichtlinien

### 3.1 Progressive Disclosure

Verbindlicher 3-Layer-Aufbau:
- **Layer A (Summary):** Entscheidung + 2-3 Kernfaktoren
- **Layer B (Explain):** erweiterte Faktorenliste, Konfidenz, Quellenhinweise
- **Layer C (Trace/Details):** request_id, technische Details, Link auf Diagnose-View

Regeln:
1. Layer A muss ohne Scroll auf Desktop und Tablet erreichbar sein.
2. Layer B/C sind per klarer UI-Aktion erreichbar („Details anzeigen“, „Trace ansehen").
3. UI-Status `loading/success/error` aus #480 bleibt durchgängig konsistent.

### 3.2 Fehlermeldungen (user-nah + diagnosetauglich)

Mindestbestandteile jeder Fehlerkarte:
- verständliche Kurzmessage (z. B. Timeout, temporärer API-Fehler)
- konkrete Next Action (erneut versuchen, Eingabe anpassen)
- technische Korrelation (`request_id`, optional Trace-Link)

Verboten:
- reine Roh-Exception ohne Nutzertext
- „silent fail“ ohne visuelles Feedback

## 4) Accessibility-Mindestkriterien (v1)

Pflichtkriterien für Explainability-/Scoring-Ansichten:

1. **Tastatur-Bedienbarkeit:** alle Disclosure- und Tab-Komponenten per Keyboard (`Tab`, `Enter`, `Space`) bedienbar.
2. **Semantik/Labels:** interaktive Elemente mit klaren `aria-label`/`aria-expanded`-Zuständen.
3. **Live-Feedback:** Statuswechsel (`loading -> success/error`) über `aria-live` für Screenreader signalisieren.
4. **Kontrast:** Text-/UI-Kontrast mindestens WCAG AA; Score-Badges nicht nur über Farbe unterscheiden.
5. **Fokusführung:** bei Fehlern Fokus auf Fehlermeldung oder primäre Recovery-Aktion setzen.

## 5) Responsiveness-Mindestkriterien (Desktop + Tablet)

### 5.1 Breakpoint-Policy

- **Desktop:** >= 1024px
- **Tablet:** 768px bis 1023px

### 5.2 Layout-Regeln

Desktop:
- Zwei-Spalten-Layout erlaubt (Result-Summary + Faktorpanel)
- Trace-/Detailbereich als Sidepanel oder expandierbarer Bereich

Tablet:
- Einspaltiger Stack mit priorisiertem Summary-Block
- Disclosure-Elemente touch-freundlich (ausreichende Touch-Ziele)

Für beide Formfaktoren gilt:
- keine horizontale Scrollpflicht für Kerninhalte
- Score/Confidence/Top-Faktoren innerhalb des initialen Viewports sichtbar

## 6) Abnahmecheckliste für UX-Review (v1)

### 6.1 Verständlichkeit
- [ ] Score inkl. Skala und Confidence ohne zusätzliche Erklärung verständlich
- [ ] Mindestens 3 Hauptfaktoren klar benannt und in Wirkung/Richtung erkennbar
- [ ] Datenstand (`as_of`) und Quellenhinweise vorhanden

### 6.2 Interaktion
- [ ] Progressive Disclosure von Summary -> Explain -> Trace funktioniert deterministisch
- [ ] Fehlerzustände zeigen Next Action + request_id
- [ ] Retry/Neustart folgt dem State-Contract aus #480

### 6.3 Accessibility/Responsiveness
- [ ] Keyboard-Navigation deckt alle interaktiven Explainability-Controls ab
- [ ] `aria-live`-Statusmeldungen für Loading/Fehler/Efolg vorhanden
- [ ] Desktop-/Tablet-Layouts erfüllen Mindestkriterien ohne horizontales Scrolling

### 6.4 Nachweisartefakte
- [ ] UX-Review-Protokoll verlinkt
- [ ] Screenshots für Desktop und Tablet hinterlegt
- [ ] Test-/Doku-Checks im Issue/PR dokumentiert

## 7) Nicht-Ziele (wp4)

- Keine Einführung neuer fachlicher Score-Modelle (nur UX-Standardisierung bestehender Outputs).
- Kein visuelles Final-Branding/Theme-System für alle zukünftigen Produktmodule.
- Keine Änderung des `/analyze`-Contracts über additive Darstellungsregeln hinaus.

## 8) Definition-of-Done-Check (#482)

- [x] UX-Standarddoku für Explainability/Scoring liegt vor
- [x] Accessibility-/Responsiveness-Mindestkriterien dokumentiert
- [x] Abnahmecheckliste für UX-Review ergänzt
- [x] Regressionstest für Pflichtsektionen/Verlinkungen ergänzt
