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
- Zieladresse in der Schweiz vorbereiten
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

## 5) Risiken & Follow-ups

- **✅ #36 — Lizenzgrenzen für GTM-Artefakte verifiziert**
  - Ergebnis: GTM-Claim-Gate inkl. kommerzieller Nutzbarkeit/Attributionspflichten dokumentiert in [`docs/GTM_DATA_SOURCE_LICENSES.md`](GTM_DATA_SOURCE_LICENSES.md)
  - Regel: unspezifische Quellenclaims sind als „Claim nicht verwenden“ markiert
  - Referenz auf Quelleninventar: #24 (BL-20.2.a)
- **#37 — Reproduzierbares Demo-Datenset definieren**
  - Risiko: inkonsistente Live-Demo durch Datenänderungen
- **#38 — Packaging-/Pricing-Hypothesen mit Zielsegmenten validieren**
  - Risiko: fehlende Entscheidungsbasis für Angebotsmodell

Die verbleibenden Risiken werden separat bearbeitet, damit BL-20.7.b als MVP-Basis erhalten bleibt und Folgeaufgaben klar nachverfolgbar sind.

---

## 6) Nächster Schritt nach BL-20.7.b

1. BL-20.7.a (Packaging-Basis Build/Run/Config) finalisieren (#34)
2. Offene Risiken #37/#38 priorisieren und in den nächsten Sprint übernehmen
3. Parallel #24 (BL-20.2.a) als vollständiges Quelleninventar/Lizenzmatrix ausbauen
4. Danach GTM-Baseline mit erstem Pilot-Run gegentesten
