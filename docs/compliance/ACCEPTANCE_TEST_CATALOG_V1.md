# Minimum-Compliance-Set — Abnahmetestkatalog v1

_Status: freigegeben (Repo-Baseline)_  
_Gültig ab: 2026-03-01_  
_Bezug: Issue #527_

## Zweck

Dieser Katalog definiert die **verbindlichen Abnahmetests** für das Minimum-Compliance-Set (BL-342) vor dem Go-Live.
Er stellt sicher, dass alle Muss-Kriterien aus Governance, Runtime-Controls und Nachweisführung reproduzierbar geprüft werden.

## Geltungsbereich

- Umgebungen: `dev` (verpflichtend), `staging` (verpflichtend), `prod` (Go-Live-Nachweis)
- Bereiche: Policy-Standards, Korrektur-/Hold-Governance, Export-/Löschkontrollen, externe Zugriffssperren, Export-Logging, Backup/Restore, Policy-Metadatenmodell
- Rollen: `QA Lead` (koordiniert), `Compliance Lead` (fachlicher Sign-off), `IT Product Owner` (technischer Sign-off)

## Eintrittskriterien für Go-Live-Abnahme

1. Alle referenzierten Pflichtdokumente liegen in der jeweils freigegebenen v1-Version vor.
2. Automatisierte Regressionstests laufen in der Zielumgebung grün.
3. Offene Blocker-Issues mit Label `status:blocked` aus dem BL-342-Kontext sind bewertet und für den Testlauf freigegeben.

## Testmatrix Muss-Kriterien (Go-Live)

| Testfall-ID | Muss-Kriterium | Primärnachweis | Prüfart | Erwartung |
|---|---|---|---|---|
| MCS-AT-001 | Policy-Standard mit Pflichtmetadaten ist verbindlich dokumentiert | `docs/compliance/POLICY_STANDARD_V1.md` / #515 | automatisiert (`tests/test_compliance_policy_standard_docs.py`) | Alle Pflichtmarker vorhanden, Backlog verweist auf Abschluss |
| MCS-AT-002 | Korrekturen erfolgen nur als neue Version mit Pflichtfeld `korrekturgrund` | `docs/compliance/KORREKTUR_RICHTLINIE_V1.md` / #516 | automatisiert (`tests/test_compliance_korrektur_richtlinie_docs.py`) | Richtlinienmarker + Backlog-Sync erfüllt |
| MCS-AT-003 | Hold-Governance (Berechtigungen, Vier-Augen-Prinzip) ist definiert | `docs/compliance/HOLD_GOVERNANCE_V1.md` / #517 | automatisiert (`tests/test_compliance_hold_governance_docs.py`) | Rollen-/Regelmarker vorhanden, Backlog-Sync erfüllt |
| MCS-AT-004 | Export-/Lösch-Kontrollplan inkl. Nachweisformat ist definiert | `docs/compliance/EXPORT_DELETE_CONTROL_PLAN_V1.md` / #518 | automatisiert (`tests/test_compliance_export_delete_control_plan_docs.py`) | Kontrollfrequenz, Sampling- und Nachweis-Marker vorhanden |
| MCS-AT-005 | Runtime sperrt externen Direktzugriff deterministisch | `docs/compliance/EXTERNAL_DIRECT_ACCESS_CONTROL_V1.md` + Runtime / #524 | automatisiert (`tests/test_compliance_external_direct_access_control_docs.py`, `tests/test_web_e2e.py`) | Dokumentation + technische Sperrpfade nachweisbar |
| MCS-AT-006 | Export-Logging enthält Pflichtfelder und Doku-Nachweis | `docs/compliance/EXPORT_LOGGING_STANDARD_V1.md` + `src/compliance/export_logging.py` / #525 | automatisiert (`tests/test_compliance_export_logging.py`, `tests/test_compliance_export_logging_docs.py`) | Pflichtfelder (`actor`, `exported_at_utc`, `channel`) und Doc-Marker erfüllt |
| MCS-AT-007 | Backup/Restore-Guideline mit RPO/RTO und Nachweisformat ist vorhanden | `docs/compliance/BACKUP_RESTORE_GUIDELINE_V1.md` / #526 | automatisiert (`tests/test_compliance_backup_restore_guideline_docs.py`) | Guideline-Marker + Backlog-Sync erfüllt |
| MCS-AT-008 | Policy-Metadatenmodell v1 validiert Pflichtfelder robust | `src/compliance/policy_metadata.py` / #538 | automatisiert (`tests/test_compliance_policy_metadata_model.py`) | Validierung akzeptiert gültige Payloads und lehnt ungültige strikt ab |
| MCS-AT-009 | Policy-Metadaten-Contract/Doku-Artefakte vollständig und konsistent | #539 (Child aus #519) | gate-vorbereitend (nach Umsetzung #539 automatisiert) | Contract- und Beispielartefakte liegen vollständig vor |
| MCS-AT-010 | Backlog-/Rollout-Sync für Policy-Metadaten ist dokumentiert | #540 (Child aus #519) | gate-vorbereitend (nach Umsetzung #540 automatisiert) | BL-342-Status und Rollout-Hinweise sind synchronisiert |

## Automatisierter Abnahmelauf (Baseline)

Empfohlene Reihenfolge für den Baseline-Check:

```bash
python3 -m unittest \
  tests.test_compliance_policy_standard_docs \
  tests.test_compliance_korrektur_richtlinie_docs \
  tests.test_compliance_hold_governance_docs \
  tests.test_compliance_export_delete_control_plan_docs \
  tests.test_compliance_external_direct_access_control_docs \
  tests.test_compliance_export_logging \
  tests.test_compliance_export_logging_docs \
  tests.test_compliance_backup_restore_guideline_docs \
  tests.test_compliance_policy_metadata_model \
  tests.test_compliance_acceptance_test_catalog_docs
```

## Manueller Abnahmeablauf (v1)

1. **Scope bestätigen:** QA Lead bestätigt, dass der Lauf BL-342 vollständig abdeckt.
2. **Automationslauf ausführen:** Baseline-Command ausführen und Ergebnis archivieren.
3. **Stichprobe manuell prüfen:** mindestens ein Fall je Governance-Bereich gegen die Primärdoku querlesen.
4. **Abweichungen erfassen:** Findings in Issue/Follow-up dokumentieren, Schweregrad setzen.
5. **Sign-off durchführen:** Compliance Lead + IT Product Owner zeichnen den Lauf ab.

## Sign-off-Protokoll (verbindlich)

```yaml
acceptance_run_id: ACC-MCS-2026-03-01-001
scope: BL-342 Minimum-Compliance-Set
environment: dev
executed_by_role: QA Lead
reviewed_by_roles:
  - Compliance Lead
  - IT Product Owner
executed_at_utc: "2026-03-01T08:45:00Z"
result: pass | pass-with-findings | fail
finding_count: 0
finding_refs: []
evidence_ref: "reports/compliance/acceptance/2026/03/ACC-MCS-2026-03-01-001/"
```

## Nachweisablage (verbindlich)

Jeder Abnahmelauf muss unter folgendem Pfad archiviert werden:

`reports/compliance/acceptance/<YYYY>/<MM>/<acceptance_run_id>/`

Pflichtdateien pro Lauf:

- `summary.md` (Ziel, Ergebnis, Sign-off)
- `automated-test-output.txt` (roh)
- `findings.md` (inkl. Schweregrad + Follow-up-Links)
- `signoff.yaml` (strukturierter Freigabenachweis)

## Abgrenzung / Nicht-Ziele

- Dieser Katalog führt **keine** produktiven Änderungen aus; er definiert ausschließlich den Abnahmepfad.
- Operative Go-Live-Entscheidung bleibt in den nachgelagerten Gates #528/#529/#530.

## Nachweis

- Backlog-Sync: `docs/BACKLOG.md`
- Umsetzung/Claim-Historie: `https://github.com/nimeob/geo-ranking-ch/issues/527`
