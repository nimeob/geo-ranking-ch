# GTM-Validierungssprint — Operating Template (BL-341.wp5)

Stand: 2026-03-01  
Bezug: #448, #418, `docs/PACKAGING_PRICING_HYPOTHESES.md`

## Ziel

Den GTM-Lernzyklus als festen Priorisierungs-Input operationalisieren:

1. Interviews reproduzierbar durchführen
2. Signale strukturiert dokumentieren
3. Entscheidungen transparent in BL-30-Priorisierung überführen

## Sprint-Rahmen (MVP)

- **Cadence:** 1 Sprint = 10 Interviews (4x Segment A, 3x Segment B, 3x Segment C)
- **Dauer:** 2 Wochen
- **Output-Pflicht:**
  - Interview-Rohdaten
  - Sprint-Summary
  - Entscheidungslog-Eintrag(e)

## Rollen & Verantwortlichkeiten

| Rolle | Verantwortung | Pflicht-Output |
|---|---|---|
| GTM Sprint Owner | Scope, Terminierung, Review-Freigabe | Sprint-Plan + Abschlussfreigabe |
| Interview Lead | Durchführung + Erstprotokoll | Vollständige Interview-Templates pro Gespräch |
| Synthese Owner | Segment-Synthese + Schwellenprüfung | Sprint-Summary + Signal-Score |
| Product/Backlog Owner | Übersetzung in BL-30-Priorisierung | Decision-Log-Eintrag + Issue-Updates |

## Interview-/Discovery-Template (pro Gespräch)

> Datei-Konvention: `reports/testing/gtm-validation/<sprint_id>/interviews/<interview_id>.md`

### Metadaten

- `interview_id`:
- `datum_utc`:
- `segment` (A/B/C):
- `rolle_firma`:
- `interviewer`:
- `confidence` (low/medium/high):

### Kernfragen (Pflicht)

1. Welcher Teil des heutigen Workflows kostet am meisten Zeit?
2. Welche drei Kriterien entscheiden über Kauf/Nichtkauf?
3. Welches Paket passt besser und warum? (`api_only` / `gui_api` / `unklar`)
4. Welche Preisbandbreite ist **prüfbar**, **zu hoch**, **zu niedrig**?
5. Welche Capability fehlt für einen Kaufentscheid? (z. B. Entitlements, Quotas, Export, Rollen)

### Signale (normalisiert)

- `package_preference`: `api_only | gui_api | unklar`
- `pricing_signal`: `fit | zu_hoch | zu_niedrig | unklar`
- `critical_blocker`: `none | entitlement | trust | integration | other`
- `buy_signal`: `go | adjust | stop`

## Sprint-Synthese-Format

> Datei-Konvention: `reports/testing/gtm-validation/<sprint_id>/summary.md`

Pflichtinhalt:

1. **Coverage:** Anzahl Interviews je Segment (Soll/Ist)
2. **Signal-Matrix:** aggregierte Signale (`go/adjust/stop`) je Segment
3. **Hypothesencheck:** Status je Hypothese aus `docs/PACKAGING_PRICING_HYPOTHESES.md`
4. **Capability-Gates:** G1/G2/G3-Status + neue Blocker
5. **Priorisierungsvorschlag:** Option 1/2/3 + Begründung

## Entscheidungslog für BL-30-Priorisierung (verbindlich)

Entscheidungen werden in `docs/testing/GTM_VALIDATION_DECISION_LOG.md` dokumentiert.

Jeder Eintrag muss enthalten:

- verwendete Evidenz (Sprint-ID + Kernzahlen)
- gewählte Option (API-only / GUI+API / Dual)
- abgeleitete BL-30-Reihenfolge
- verworfene Optionen + Gegenargumente
- Owner + Review-Status

## Mapping-Regel: Sprint-Signale -> BL-30-Reihenfolge

- **Option 1 (API-only zuerst):** BL-30.1 vor BL-30.2
- **Option 2 (GUI+API zuerst):** BL-30.2 als priorisiertes Enabler-Paket + BL-30.1 parallel
- **Option 3 (Dual Soft-Launch):** BL-30.1 und BL-30.2 parallel, aber mit explizitem Capacity-Limit

Unabhängig von Option gilt:

- G3 (Entitlement-Layer) muss als Risiko transparent im Decision Log markiert bleiben, solange nicht umgesetzt.

## DoD für einen abgeschlossenen GTM-Sprint

- [ ] 10 Interviews vollständig im Template dokumentiert
- [ ] Sprint-Summary mit Hypothesenstatus vorhanden
- [ ] Mindestens ein neuer Decision-Log-Eintrag erstellt
- [ ] BL-30-Priorisierung aus der Entscheidung nachvollziehbar aktualisiert
