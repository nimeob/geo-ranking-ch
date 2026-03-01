# BL-20.7.b — Go-to-Market Artefakte (MVP)

Stand: 2026-02-26
Bezug: #35

## 1) Value Proposition (MVP)

### Problem
Für Standort- und Gebäudeentscheidungen sind in der Schweiz relevante Daten über mehrere Quellen verteilt. Das führt zu hohem manuellen Aufwand, inkonsistenten Entscheidungsgrundlagen und schwer reproduzierbaren Abklärungen.

### Nutzenversprechen
**Geo Ranking CH liefert in wenigen Sekunden eine nachvollziehbare Standort-/Gebäudeeinschätzung pro Adresse oder Kartenpunkt — inklusive Quellen, Aktualität und Confidence.**

### Zielsegmente (MVP-fähig)
1. **Immobilienbewertung/Transaktionsvorbereitung**
   - Schneller Erst-Check für Objekt- und Standortqualität
2. **Projektentwicklung/Bauvorprüfung**
   - Frühindikatoren für Machbarkeit und Umfeldqualität
3. **Makler-/Beratungs-Workflows**
   - Strukturierte, kundenlesbare Kurzberichte statt manueller Datensammlung

### Kern-Differenzierung im MVP
- API + GUI getrennt konsumierbar (technisch und kommerziell)
- Explainability by default (`sources`, `as_of`, `confidence`, `derived_from`)
- Einheitlicher Flow für Adresse **und** Kartenpunkt

---

## 2) Scope (MVP) / Nicht-Scope

### In Scope (BL-20.7.b)
- GTM-Baseline für **Messaging, Angebotsrahmen und Demo-Storyline**
- Trennung der Angebotslogik in:
  - **API-only** (Integrations-/B2B-Fokus)
  - **GUI+API** (Endnutzer-/Beratungs-Fokus)
- Dokumentierte Risiken inkl. Follow-up-Issues

### Out of Scope (für diese Iteration)
- Finales Pricing-Modell und kommerzielle Freigabe
- Rechtliche Finalprüfung aller Datenlizenz-Claims
- Vollständiges Sales-Enablement (One-Pager, Deck, CRM-Prozess, etc.)

---

## 3) Packaging-Rahmen (MVP)

### Angebot A — API-only
- Für Teams mit eigener Oberfläche/Workflow
- Fokus: stabile Schnittstelle, Explainability-Felder, Integrationsfähigkeit
- Erfolgsmetrik: Time-to-first-integration, API-Reliability, reproduzierbare Ergebnisse

### Angebot B — GUI+API
- Für Teams, die direkt mit UI arbeiten wollen (ohne eigene Frontend-Integration)
- Fokus: schnelle Nutzbarkeit, nachvollziehbare Ergebnisdarstellung, Demo-Fähigkeit
- Erfolgsmetrik: Time-to-first-insight, Demo-Konversionsrate, Verständlichkeit der Ergebnisse

---

## 4) Demo-Flow / Storyline (10–12 Minuten)

### Setup (vorab)
- Demo-Datenset v1 nutzen: [`docs/DEMO_DATASET_CH.md`](DEMO_DATASET_CH.md) (DS-CH-01 bis DS-CH-05)
- Primärfall + Vergleichsfall aus dem Datenset auswählen (statt ad-hoc Live-Adressen)
- Optional zweiter Fall via Kartenklick (vergleichender Standort)
- API- und GUI-Zugang verifizieren (`/health`, `/version`, Demo-URL)

### Storyline
1. **Aufhänger (1 min):** Ausgangsproblem erklären (fragmentierte Daten, manuelle Abklärungen)
2. **Adresse eingeben (2 min):** Standort-/Gebäudeprofil live abrufen
3. **Explainability zeigen (2 min):** Herkunft + Aktualität + Confidence transparent machen
4. **Kartenpunkt-Fall (2 min):** alternativen Standort via Klick analysieren
5. **Vergleich/Entscheidung (2 min):** zwei Standorte gegenüberstellen (Stärken/Risiken)
6. **Produktisierung (1–2 min):** API-only vs GUI+API Einsatzbild und nächster Pilot-Schritt

### Demo-Erfolgskriterien
- Antwort in stabiler Zeit ohne manuelle Nacharbeit
- Ergebnis ist für Nicht-Entwickler verständlich erklärbar
- Quellen-/Confidence-Felder beantworten Rückfragen im Termin

---

## 5) Offene Risiken (als Follow-up-Issues)

- **✅ #36 — Lizenzgrenzen für GTM-Artefakte verifiziert**
  - Ergebnis: GTM-Claim-Gate inkl. kommerzieller Nutzbarkeit/Attributionspflichten dokumentiert in [`docs/GTM_DATA_SOURCE_LICENSES.md`](GTM_DATA_SOURCE_LICENSES.md)
  - Regel: unspezifische Quellenclaims sind als „Claim nicht verwenden“ markiert
  - Referenz auf Quelleninventar: #24 (BL-20.2.a)
- **✅ #37 — Reproduzierbares Demo-Datenset definiert**
  - Ergebnis: v1-Datenset mit 5 CH-Standorten, erwarteten Kernaussagen und Confidence-/Unsicherheitsnotizen in [`docs/DEMO_DATASET_CH.md`](DEMO_DATASET_CH.md)
- **✅ #38 — Packaging-/Pricing-Hypothesen mit Zielsegmenten validiert**
  - Ergebnis: segmentierte Kaufkriterien + testbare Pricing-/Packaging-Hypothesen inkl. Entscheidungsvorlage und BL-30-Gates dokumentiert in [`docs/PACKAGING_PRICING_HYPOTHESES.md`](PACKAGING_PRICING_HYPOTHESES.md).

Die GTM-Basis ist damit für den nächsten Validierungssprint vollständig dokumentiert; weitere Iterationen laufen als eigene Follow-up-Issues.

---

## 6) Nächster Schritt nach BL-20.7.b

1. GTM-Baseline mit erstem Pilot-Run gegentesten (unter Nutzung des Datensets v1)
2. Interview-/Signalsammlung aus `docs/PACKAGING_PRICING_HYPOTHESES.md` mit dem operativen Template aus [`docs/testing/GTM_VALIDATION_SPRINT_TEMPLATE.md`](testing/GTM_VALIDATION_SPRINT_TEMPLATE.md) durchführen und Entscheidung (API-only vs GUI+API vs Dual) treffen
3. Entscheidung transparent im [`docs/testing/GTM_VALIDATION_DECISION_LOG.md`](testing/GTM_VALIDATION_DECISION_LOG.md) dokumentieren
4. Abgeleitete BL-30.1/30.2-Folge-Issues mit konkreten Entitlement-/Pricing-DoD anlegen
