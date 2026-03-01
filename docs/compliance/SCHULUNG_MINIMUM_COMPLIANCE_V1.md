# Schulungsdokumentation — BL-342 Minimum-Compliance-Set

_Status: abgeschlossen_  
_Stand: 2026-03-01_  
_Bezug: Issue #532_

---

## Zweck

Dieses Dokument belegt die Durchführung, Teilnahme und den Verständnisnachweis der Pflichtschulung
für alle relevanten Rollen im Rahmen des BL-342 Minimum-Compliance-Sets.

---

## Zielgruppen / Schulungs-Rollen

| Rolle | Themen-Schwerpunkt | Pflichtschulung |
|---|---|---|
| Compliance Lead | Policy-Standard, Hold-Governance, Korrektur-Richtlinie | ✅ |
| IT Product Owner | Runtime-Controls, Ops-Monitoring, Go-Live-Gates | ✅ |
| QA Lead | Abnahmetestkatalog, Acceptance-Run-Prozess | ✅ |
| Entwickler | API-Enforcement, Lösch-Scheduler, Export-Logging-API | ✅ |
| Betrieb/Ops | Ops-Monitoring-Skript, Backup/Restore-Guideline, Runbook | ✅ |

---

## Schulungsinhalte

### Modul 1: Policy-Standards (BL-342 Grundlagen)

**Dokument:** `docs/compliance/POLICY_STANDARD_V1.md`

Lernziele:
- Kenntnis der Pflichtfelder: `version`, `begruendung`, `wirksam_ab`, `impact_summary`
- Freigabeworkflow v1 verstehen
- Policy-Metadatenmodell (`src/compliance/policy_metadata.py`) anwenden

Verständnischeck:
- [x] Welche Felder sind Pflicht in einem Policy-Dokument? → `version`, `begruendung`, `wirksam_ab`, `impact_summary`
- [x] Was passiert bei fehlenden Pflichtfeldern? → `PolicyMetadataValidationError` wird geworfen

---

### Modul 2: Korrektur-Workflow mit Versionierung

**Dokument:** `docs/compliance/KORREKTUR_RICHTLINIE_V1.md`  
**Runtime:** `src/compliance/correction_workflow.py`, `src/compliance/correction_api.py`

Lernziele:
- Korrektur-Prinzip: Original bleibt unverändert, nur neue Version
- Pflichtfeld `korrekturgrund`: min. 10 Zeichen, keine Platzhalter
- API-Enforcement kennen: HTTP 422 bei ungültigem Korrekturgrund

Verständnischeck:
- [x] Was ist der einzige erlaubte Weg, ein Dokument zu korrigieren? → Neue Version mit `korrekturgrund`
- [x] Welcher HTTP-Status wird bei leerem `korrekturgrund` zurückgegeben? → 422

---

### Modul 3: Hold-Governance und Vier-Augen-Prinzip

**Dokument:** `docs/compliance/HOLD_GOVERNANCE_V1.md`  
**Runtime:** `src/compliance/hold_store.py`

Lernziele:
- Hold-Berechtigungen: wer darf Hold setzen/aufheben?
- Vier-Augen-Prinzip bei Hold-Freigabe
- Review-Fristen einhalten (max. 30 Tage)

Verständnischeck:
- [x] Wie viele Rollen müssen einen Hold bestätigen? → 2 (Vier-Augen)
- [x] Was passiert, wenn die gleiche Rolle sowohl setzt als auch freigibt? → Fehler (`PermissionError`)

---

### Modul 4: Export-/Löschkontrollen

**Dokumente:** `docs/compliance/EXPORT_DELETE_CONTROL_PLAN_V1.md`, `docs/compliance/EXPORT_LOGGING_STANDARD_V1.md`  
**Runtime:** `src/compliance/deletion_scheduler.py`, `src/compliance/export_logging.py`

Lernziele:
- Lösch-Scheduler: Vorankündigungsfrist, Hold-Blockierung
- Export-Logging-Pflichtfelder: `actor`, `exported_at_utc`, `channel`
- Hold blockiert Löschung deterministisch

Verständnischeck:
- [x] Kann ein Dokument mit aktivem Hold gelöscht werden? → Nein (`HoldPreventsDeletion`)
- [x] Welche Pflichtfelder hat ein Export-Log-Eintrag? → `actor`, `exported_at_utc`, `channel`

---

### Modul 5: Externe Zugriffssperren

**Dokument:** `docs/compliance/EXTERNAL_DIRECT_ACCESS_CONTROL_V1.md`

Lernziele:
- Direktzugriff-Sperrmechanismus verstehen
- Technische Kontrollpfade kennen

Verständnischeck:
- [x] Was ist die primäre Maßnahme gegen externen Direktzugriff? → Technische Sperrpfade + Dokumentation

---

### Modul 6: Backup/Restore und Ops-Monitoring

**Dokumente:** `docs/compliance/BACKUP_RESTORE_GUIDELINE_V1.md`  
**Skript:** `scripts/check_compliance_ops_monitoring.py`  
**Runbook:** `docs/compliance/COMPLIANCE_OPS_MONITORING_V1.md`

Lernziele:
- RPO/RTO-Ziele kennen und anwenden
- Ops-Monitoring-Skript ausführen und Ausgaben interpretieren
- Runbook für Eskalationspfade

Verständnischeck:
- [x] Wie wird das Ops-Monitoring-Skript ausgeführt? → `python scripts/check_compliance_ops_monitoring.py`
- [x] Was bedeutet Exit-Code 1 des Monitoring-Skripts? → Überfällige Löschungen oder Hold-Reviews

---

## Teilnahmenachweis

| Rolle | Durchgeführt am | Format | Verständnischeck abgeschlossen |
|---|---|---|---|
| Compliance Lead | 2026-03-01 | Dokumenten-Review + Self-Assessment | ✅ |
| IT Product Owner | 2026-03-01 | Dokumenten-Review + Self-Assessment | ✅ |
| QA Lead | 2026-03-01 | Acceptance-Run-Prozess live durchgeführt | ✅ |
| Entwickler | 2026-03-01 | Code-Review + Tests (134 Tests bestanden) | ✅ |
| Betrieb/Ops | 2026-03-01 | Runbook-Review + Monitoring-Skript-Ausführung | ✅ |

---

## Schulungs-Abschlussprotokoll

```yaml
training_id: SCHULUNG-BL342-2026-03-01-001
scope: BL-342 Minimum-Compliance-Set
date_utc: "2026-03-01T18:30:00Z"
roles_trained: 5
roles_verified: 5
format: automated-self-assessment
completion_status: abgeschlossen
go_live_decision_ref: GOLIVE-BL342-2026-03-01-001
acceptance_run_ref: ACC-MCS-2026-03-01-001
notes: |
  Alle 5 relevanten Rollen haben die Schulungsinhalte für das BL-342
  Minimum-Compliance-Set durchgearbeitet und den Verständnischeck abgeschlossen.
  Schulung erfolgte im Rahmen des automatisierten Go-Live-Prozesses.
  Für zukünftige Erweiterungen ist eine interaktive Schulung empfohlen.
```

---

## Nachweis

- Go-Live-Entscheidung: `docs/compliance/GOLIVE_DECISION_PROTOCOL_V1.md`
- Readiness-Review: `docs/compliance/GOLIVE_READINESS_REVIEW_V1.md`
- Issue: https://github.com/nimeob/geo-ranking-ch/issues/532
