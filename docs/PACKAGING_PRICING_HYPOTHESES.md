# BL-20.7.r3 - Packaging-/Pricing-Hypothesen mit Zielsegmenten

Stand: 2026-02-28
Bezug: #38 (Follow-up aus #35)

## Ziel

Eine testbare Entscheidungsgrundlage für den nächsten GTM-Sprint bereitstellen:

- Zielsegmente mit klaren Kaufkriterien
- pro Segment eine falsifizierbare Packaging-/Pricing-Hypothese
- klare Capability-Gates für BL-30.1/BL-30.2 (Pricing + Entitlements)

## Segmentprofil + Top-3 Kaufkriterien

### Segment A - Immobilienbewertung / Transaktionsvorbereitung

Top-3 Kaufkriterien:
1. **Zeitgewinn pro Objekt** (manuelle Abklärungen reduzieren)
2. **Nachvollziehbarkeit für Kundengespräche** (Explainability-Felder)
3. **Verlässliche Vergleichbarkeit über mehrere Objekte** (einheitlicher Analyse-Flow)

### Segment B - Projektentwicklung / Bauvorprüfung

Top-3 Kaufkriterien:
1. **Frühe Machbarkeitsindikatoren** (Gebäude-/Umfeldsignal ohne Vollgutachten)
2. **Risiko-Früherkennung** (Unsicherheiten/Confidence explizit sichtbar)
3. **Schnelle Szenario-Vergleiche** (Adresse vs. Kartenpunkt)

### Segment C - Makler-/Beratungs-Workflows

Top-3 Kaufkriterien:
1. **Sofort nutzbares Frontend** (ohne eigene Integrationsarbeit)
2. **Demo-/Meeting-Tauglichkeit** (in wenigen Minuten erklärbar)
3. **Standardisierte Ergebnisdarstellung** (konsistente Story pro Objekt)

## Testbare Packaging-/Pricing-Hypothesen

> Alle Preisangaben sind bewusst als **Hypothesen-Bandbreiten** formuliert (kein finales Preisblatt).

| Segment | Hypothese (falsifizierbar) | Angebotszuschnitt | Preisannahme (Hypothese) | Messgröße + Schwelle |
|---|---|---|---|---|
| A (Bewertung/Transaktion) | Wenn API-only planbar und nachvollziehbar ist, akzeptieren Teams ein monatliches Abo statt Pay-per-report. | **API-only** inkl. `/analyze`, Explainability, Basis-SLA | CHF **290-590** / Monat / Team | >= 3 von 5 Pilotgesprächen nennen Abo als bevorzugtes Modell und akzeptieren Bandbreite ohne Hard-Reject |
| B (Projektentwicklung) | Wenn Kartenpunkt + Adressfluss kombinierbar ist, wird ein höherer Preis für schnellere Vorprüfung akzeptiert. | **API-only Plus** (höhere Volumen-/Rate-Limits, Exportfähige Ergebnisstruktur) | CHF **590-1'200** / Monat / Team | >= 2 von 4 Pilotteams bestätigen, dass der Zeitgewinn den Preisrahmen rechtfertigt |
| C (Makler/Beratung) | Wenn GUI+API sofort einsatzbereit ist, ist Seat-/Workspace-Modell verständlicher als reiner API-Preis. | **GUI+API** inkl. Ergebnisdarstellung + Demo-Flow auf DS v1 | CHF **49-119** / Nutzer/Monat oder CHF **390-890** / Team/Monat | >= 60% der Interviews bevorzugen GUI-Paket gegenüber API-only bei gleichem Use Case |

## Validierungsdesign für den nächsten GTM-Sprint

Operative Ausführung (Template, Rollen, Outputpflichten):
- [`docs/testing/GTM_VALIDATION_SPRINT_TEMPLATE.md`](testing/GTM_VALIDATION_SPRINT_TEMPLATE.md)
- [`docs/testing/GTM_VALIDATION_DECISION_LOG.md`](testing/GTM_VALIDATION_DECISION_LOG.md)

### Stichprobe (MVP-tauglich)

- 10 strukturierte Discovery-/Pricing-Gespräche
  - 4x Segment A
  - 3x Segment B
  - 3x Segment C

### Standardisierte Fragen je Gespräch

1. Welcher Teil des heutigen Workflows kostet am meisten Zeit?
2. Welche drei Kriterien entscheiden über Kauf/Nichtkauf?
3. Welches Paket (API-only vs GUI+API) passt besser und warum?
4. Welche Preisbandbreite ist "prüfbar", "zu hoch", "zu niedrig"?

### Entscheidungsregel (Go/Adjust/Stop)

- **Go:** Hypothese trifft Schwellenwert und kein kritischer Capability-Blocker
- **Adjust:** Teiltreffer (Signal vorhanden, aber Preis/Paket-Form unklar)
- **Stop:** klare Ablehnung oder wiederholtes „kein Budget/kein Fit"
- Jede Sprint-Entscheidung wird verpflichtend im
  [`docs/testing/GTM_VALIDATION_DECISION_LOG.md`](testing/GTM_VALIDATION_DECISION_LOG.md)
  als nachvollziehbare BL-30-Priorisierungsableitung dokumentiert.

## Capability-Gates (Forward-Compatibility BL-30.1 / BL-30.2)

| Gate | Bedeutung | Heute verfügbar | Relevanz für Angebot |
|---|---|---|---|
| G1 API Baseline | Stabiler API-Kern (`/analyze`, Explainability, reproduzierbarer Contract) | Ja (BL-20.1/20.3/20.4/20.5) | Voraussetzung für alle API-only-Pakete |
| G2 GUI Baseline | GUI-MVP mit Adresse + Kartenklick + Ergebnispanel | Ja (BL-20.6) | Voraussetzung für GUI+API-Pakete |
| G3 Entitlement-Layer | Feingranulare Feature-/Quota-Steuerung je Plan/Tenant | Noch nicht (BL-30.1/30.2) | Erforderlich für produktive Staffelpreise/Feature-Grenzen |

## Upgrade-Pfade zu BL-30.1 / BL-30.2

1. **Von Hypothesen zu Pricing-Modell (BL-30.1):**
   - Interviewdaten in 2-3 belastbare Preis-/Packaging-Kandidaten überführen
   - Kandidaten entlang Segment A/B/C mit klaren Unit-Economics markieren
2. **Von Angebotszuschnitt zu Entitlements (BL-30.2):**
   - Paketgrenzen in technische Entitlements überführen (Quota, Feature-Flags, Rollen)
   - API-only vs GUI+API als getrennte Capability-Sets im Contract verankern

## Entscheidungsvorlage für den nächsten GTM-Sprint

Nach Abschluss der 10 Interviews wird genau eine Primärentscheidung getroffen:

- **Option 1:** API-only zuerst (Segment A/B dominiert)
- **Option 2:** GUI+API zuerst (Segment C dominiert)
- **Option 3:** Dualer Soft-Launch (wenn Signale ähnlich stark und operativ tragbar)

Pflichtausgabe für die Entscheidung:
- favorisierte Option + Begründung
- verworfene Optionen + Gegenargumente
- konkrete Folge-Issues für BL-30.1/30.2 mit DoD
