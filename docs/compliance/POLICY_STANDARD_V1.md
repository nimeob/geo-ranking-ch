# Minimum-Compliance-Set — Policy-Standard v1

_Status: freigegeben (Repo-Baseline)_  
_Gültig ab: 2026-03-01_  
_Bezug: Issue #515_

## Zweck

Dieser Standard definiert die **verbindliche Policy-Vorlage** für Aufbewahrung/Löschung im Projekt `geo-ranking-ch`.
Jede neue oder geänderte Policy muss die Pflichtfelder für **Version**, **Begründung**, **Wirksam-ab** und **Impact** vollständig ausfüllen.

## Geltungsbereich

- Compliance-/Governance-Policies mit Auswirkungen auf Datenaufbewahrung, Löschung, Export, Korrektur und Hold.
- Gilt für produktive und vorproduktive Umgebungen (`dev`, `staging`, `prod`) als inhaltlicher Referenzstandard.

## Pflicht-Metadaten pro Policy

| Feld | Pflicht | Format / Regel | Zweck |
|---|---|---|---|
| `policy_id` | ja | `POL-<bereich>-<laufnummer>` | Eindeutige Referenz |
| `version` | ja | `v<major>.<minor>` (z. B. `v1.0`) | Nachvollziehbare Versionierung |
| `begruendung` | ja | Klarer Anlass + Risiko/Problem | Auditierbare Änderungsbegründung |
| `wirksam_ab` | ja | ISO-Datum (`YYYY-MM-DD`) | Verbindlicher Startzeitpunkt |
| `impact_summary` | ja | Kurztext (fachlich + technisch) | Sichtbarer Änderungs-Impact |
| `impact_referenz` | ja | Link auf Entscheidungs-/Ticket-Artefakt | Prüfbare Nachweisführung |
| `owner_role` | ja | Rolle, nicht Person (z. B. `Compliance Lead`) | Verantwortlichkeit |
| `approved_by_role` | ja | Rolle, nicht Person | Freigabeverantwortung |
| `review_intervall` | ja | `quarterly`/`half-yearly`/`yearly` | Revisionssicherheit |

## Mindestregeln für Policy-Änderungen

1. **Keine wirksame Policy ohne vollständige Pflichtfelder.**
2. **Versionserhöhung ist obligatorisch**:
   - `minor`: Klarstellungen ohne Prozessänderung
   - `major`: Änderungen mit operativem/technischem Impact
3. **Begründungspflicht**: Jede Änderung enthält nachvollziehbaren Anlass inkl. Risikoaussage.
4. **Wirksam-ab darf nicht fehlen**; Rückdatierung ist nur mit expliziter Begründung zulässig.
5. **Impact-Pflicht**: Jede Änderung beschreibt Auswirkungen auf Prozesse, Systeme und Nachweise.

## Freigabe-Workflow (v1)

1. Entwurf erstellen (inkl. aller Pflichtfelder)
2. Fachreview durch `Compliance Lead`
3. Technischer Impact-Check durch `IT Product Owner`/`IT Security` (je nach Scope)
4. Formale Freigabe durch `approved_by_role`
5. Veröffentlichung im Repo + Verlinkung im Backlog/Issue

## Referenzvorlage (Copy/Paste)

```yaml
policy_id: POL-RETDEL-001
version: v1.0
begruendung: "Regulatorische Mindestanforderungen für Aufbewahrung und Löschung konsolidieren"
wirksam_ab: "2026-03-01"
impact_summary: "Neue Pflichtfelder und Freigabeschritte für alle Retention/Deletion-Policies"
impact_referenz: "https://github.com/nimeob/geo-ranking-ch/issues/515"
owner_role: "Compliance Lead"
approved_by_role: "Compliance Lead"
review_intervall: yearly
```

## Abgrenzung / Nicht-Ziele

- Dieser Standard ist primär der **fachliche Referenzrahmen**; er ersetzt keine vollständige Prozess-/Workflow-Automation.
- Technische Umsetzungspakete (z. B. Logging, Scheduler, Enforcements in Fach-Workflows) werden in separaten Issues geführt (u. a. #525, #522).

## Nachweis

- Backlog-Sync: `docs/BACKLOG.md`
- Umsetzung/Claim-Historie (Policy-Standard): `https://github.com/nimeob/geo-ranking-ch/issues/515`
- Runtime-Metadatenmodell (v1): `src/compliance/policy_metadata.py` (Issue #538)
- Regressionstest Runtime-Modell: `tests/test_compliance_policy_metadata_model.py`
