# Minimum-Compliance-Set — Hold-Governance v1

_Status: freigegeben (Repo-Baseline)_  
_Gültig ab: 2026-03-01_  
_Bezug: Issue #517_

## Zweck

Diese Richtlinie definiert verbindlich, **wer Hold-Flags setzen und aufheben darf**, welche Freigaben dafür notwendig sind und wie der Entscheidungsweg auditierbar dokumentiert wird.

Ziel ist, unbeabsichtigte Freigaben oder unkontrollierte Sperren zu verhindern und gleichzeitig eine schnelle Reaktion in Rechts-, Compliance- und Sicherheitsfällen zu ermöglichen.

## Geltungsbereich

- Alle Dokumente/Artefakte im Minimum-Compliance-Set (BL-342), die von Aufbewahrung, Löschung, Export oder Korrektur betroffen sein können.
- Gilt für `dev`, `staging` und `prod` als inhaltlicher Governance-Standard.
- Ergänzt `docs/compliance/POLICY_STANDARD_V1.md` und `docs/compliance/KORREKTUR_RICHTLINIE_V1.md`.

## Rollen- und Berechtigungsmatrix

| Rolle | Hold setzen | Hold aufheben | Bedingungen |
|---|---|---|---|
| `Compliance Lead` | ja | ja | Standardrolle für fachliche Entscheidung |
| `Legal Counsel` | ja | ja | Bei regulatorischem/rechtlichem Bezug verpflichtend einzubinden |
| `Security Lead` | ja (sicherheitsbezogen) | ja (sicherheitsbezogen) | Nur für Security-Incidents/Forensik-Scope |
| `IT Product Owner` | nein (nur Antrag) | nein (nur Antrag) | Darf Cases vorbereiten, aber keine finale Entscheidung |
| `Operations` | nein (nur technische Ausführung) | nein (nur technische Ausführung) | Umsetzung erst nach formaler Freigabe |

## Verbindliche Entscheidungsregeln

1. **Vier-Augen-Prinzip**
   - Setzen oder Aufheben eines Holds erfordert immer zwei Freigaben:
     - eine fachliche Freigabe (`Compliance Lead` oder `Legal Counsel`)
     - eine technische/operative Gegenprüfung (`Security Lead` oder `IT Product Owner`)
2. **Legal-Pflicht bei Rechtsbezug**
   - Wenn ein Case rechtliche Risiken (z. B. Verfahren, Auskunftspflichten, Sperrverfügungen) betrifft, ist `Legal Counsel` obligatorisch.
3. **Scope-Minimierung**
   - Hold gilt nur für den kleinstmöglichen Scope (Dokument, Datensatzgruppe, Zeitraum), nicht pauschal systemweit.
4. **Zeitliche Befristung**
   - Jeder Hold hat ein `review_due_at` (spätestens 30 Tage) und muss aktiv bestätigt oder aufgehoben werden.
5. **Keine stille Aufhebung**
   - Hold-Aufhebung ohne dokumentierten Aufhebungsgrund und Freigaben ist unzulässig.

## Entscheidungswege (Setzen/Aufheben)

### A) Standardfall — Hold setzen

1. Antrag erfassen (`requested_by_role`, `hold_reason`, Scope, Risiko)
2. Fachliche Entscheidung durch `Compliance Lead` (oder `Legal Counsel`)
3. Gegenprüfung durch `Security Lead` oder `IT Product Owner`
4. Technische Umsetzung durch `Operations`
5. Nachweis im Ticket/Decision-Log verlinken

### B) Standardfall — Hold aufheben

1. Aufhebungsantrag mit Begründung (`release_reason`) erfassen
2. Prüfung, ob regulatorische/rechtliche Gründe entfallen sind
3. Zwei Freigaben gemäß Vier-Augen-Prinzip
4. Technische Aufhebung durch `Operations`
5. Abschlussnachweis inkl. Zeitstempel und Referenz

### C) Eilfall (Incident/Forensik)

- `Security Lead` darf einen **temporären Sofort-Hold** setzen.
- Pflicht: Nachgelagerte Bestätigung durch `Compliance Lead` oder `Legal Counsel` innerhalb von 24h.
- Ohne Bestätigung wird der Sofort-Hold als Governance-Verstoß markiert und eskaliert.

## Pflicht-Nachweise pro Hold-Entscheidung

| Feld | Pflicht | Regel |
|---|---|---|
| `hold_id` | ja | Eindeutige Referenz (`HOLD-<YYYY>-<laufnummer>`) |
| `hold_reason` | ja | Konkreter Anlass inkl. Risikoaussage |
| `scope` | ja | Betroffene Objekte + Grenzen |
| `requested_by_role` | ja | Antragsstellende Rolle |
| `approved_by_roles` | ja | Zwei Freigaben gemäß Vier-Augen-Prinzip |
| `effective_at` | ja | Zeitpunkt der Aktivierung (ISO-8601) |
| `review_due_at` | ja | Re-Assessment spätestens in 30 Tagen |
| `release_reason` | ja (bei Aufhebung) | Nachvollziehbarer Grund für Aufhebung |
| `evidence_ref` | ja | Link auf Issue/Decision/Review |

## RACI (Kurzform)

- **Responsible (R):** Compliance Lead / Legal Counsel / Security Lead (je nach Fall)
- **Accountable (A):** Compliance Lead
- **Consulted (C):** Legal Counsel, IT Product Owner, Operations
- **Informed (I):** Stakeholder gemäß Incident-/Compliance-Verteiler

## Abgrenzung / Nicht-Ziele

- Diese Richtlinie beschreibt Governance, nicht die technische Hold-Implementierung.
- Runtime-Umsetzung und technische Enforcement liegen in separaten Work-Packages (u. a. #523, #525, #531).

## Nachweis

- Backlog-Sync: `docs/BACKLOG.md`
- Umsetzung/Claim-Historie: `https://github.com/nimeob/geo-ranking-ch/issues/517`
