# Produktvision — Geo Intelligence Portal Schweiz

Stand: 2026-02-26

## Zielbild

Ein Portal, in dem Nutzer:innen eine Adresse in der Schweiz eingeben (oder einen Punkt auf der Karte auswählen) und sofort belastbare Standort- und Gebäudeinformationen erhalten.

Der technische Unterbau besteht aus:

1. **Webservice/API** (maschinenlesbar, für Integrationen/B2B)
2. **Weboberfläche (GUI)** (für Endnutzer:innen)

Beide sollen **unabhängig vermarktbar und nutzbar** sein.

---

## Problem, das gelöst wird

Heute sind relevante Daten über viele Quellen verteilt (z. B. swisstopo, GWR/Gebäude- und Wohnungsregister, OSM, öffentliche Datensätze). Für fundierte Entscheidungen zu Wohnen, Kauf, Bau und Entwicklung fehlen oft einheitliche, schnell zugängliche Antworten pro Standort.

---

## Kernnutzen (User Value)

Für eine Adresse/einen Punkt sollen u. a. schnell sichtbar werden:

- Was für ein Gebäude dort steht
- Baujahr / Renovationshinweise (soweit verfügbar)
- Energieträger / Heizungsindikatoren
- Lärmquellen in der Nähe
- ÖV-Anbindung
- Nahversorgung (Supermärkte, Schulen, etc.)
- Standort-Einschätzung für Bauvorhaben (z. B. Untergrund, Hangneigung, Erschliessung/Strassenzugang)

---

## Scope-Module (fachlich)

### M1 — Gebäudeprofil
- Adress-Geocoding + Parzellen-/Gebäudebezug
- Gebäudetyp, Baujahr, Renovations-/Mutationshinweise, Energieträger

### M2 — Umfeldprofil
- ÖV-Erreichbarkeit
- Points of Interest (Supermärkte, Schulen, Basis-Infrastruktur)
- Lärm- und Belastungsindikatoren

### M3 — Bau-Eignung am Punkt
- Kartenklick in CH → Standortanalyse
- Topografie/Hangneigung, Untergrundindikatoren, Zugänglichkeit per Strasse
- Distanz-/Erschliessungsmetriken

### M4 — Explainability
- Für jedes Ergebnis: Quelle, Aktualität, Vertrauensniveau
- Trennung von „harte Fakten“ vs. „indikative Ableitungen"

### M5 — Produktoberflächen
- API-first Webservice
- GUI mit Karten-Interaktion und Ergebnis-Panel

---

## Datenquellen (Startpunkt)

- **Bund/CH:** swisstopo / GeoAdmin, GWR und weitere öffentliche Register
- **Community/Open:** OpenStreetMap
- **Weitere öffentliche Quellen:** je nach Thema (Lärm, Mobilität, Infrastruktur)

Hinweis: Quelle, Lizenz und Nutzungsbedingungen sind je Datendomäne explizit zu dokumentieren (GTM-Claim-Gate: [`docs/GTM_DATA_SOURCE_LICENSES.md`](GTM_DATA_SOURCE_LICENSES.md); vollständiges Quelleninventar in #24 / BL-20.2.a).

---

## Delivery-Prinzipien

1. **API-first:** Jede GUI-Funktion basiert auf stabilen API-Endpunkten.
2. **Reproduzierbarkeit:** Ergebnisse sind mit Request-ID und Quellen nachvollziehbar.
3. **Incremental Shipping:** kleine, nutzbare Verticals statt Big-Bang.
4. **Testen mit Fokus:** genug für Stabilität, aber Priorität auf Produkt-/Service-Funktionen.
5. **Kundentrennung:** API und GUI als separat konsumierbare Angebote.

---

## Priorität für die nächsten Iterationen

1. Webservice-Funktionalität ausbauen (Gebäudeprofil + Umfeldprofil als erste Verticals)
2. API-Verträge stabilisieren (Versionierung, Fehlerbilder, Explainability-Felder)
3. GUI-MVP aufbauen (Adresseingabe + Kartenklick + Ergebnisdarstellung)
4. Test-Skripte im Maintenance-Mode halten (kein endloses Hardening ohne neuen Nutzen)

## GTM-MVP-Artefakte

- Für die erste Go-to-Market-Basis siehe [`docs/GO_TO_MARKET_MVP.md`](GO_TO_MARKET_MVP.md).
- Enthält Value Proposition, Scope-Rahmen, Demo-Storyline und offene GTM-Risiken als Follow-up-Issues.

---

## Nicht-Ziele (vorerst)

- Vollständige CH-Abdeckung aller Spezialdatensätze im ersten Wurf
- Perfekte Bauprognose/Expertensystem im MVP
- Komplexe Multi-Tenant-Billing-Features in der Frühphase
