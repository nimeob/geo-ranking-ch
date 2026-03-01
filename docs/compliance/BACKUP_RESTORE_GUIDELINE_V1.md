# Minimum-Compliance-Set — Backup/Restore-Guideline v1

_Status: freigegeben (Repo-Baseline)_  
_Gültig ab: 2026-03-01_  
_Bezug: Issue #526_

## Zweck

Diese Guideline definiert den **verbindlichen Mindeststandard** für Backup und Restore im Projekt `geo-ranking-ch`, damit Compliance-relevante Artefakte reproduzierbar gesichert und im Störfall innerhalb definierter Zielzeiten wiederhergestellt werden können.

## Geltungsbereich

- Repositorische Compliance-Artefakte unter `docs/compliance/`
- Nachweisartefakte unter `reports/compliance/`
- Operative Runbooks und Backlog-Referenzen mit Governance-Bezug (`docs/OPERATIONS.md`, `docs/BACKLOG.md`)
- Konfigurationsstände, die für Auditierbarkeit und Restore-Nachweise notwendig sind

## Mindestanforderungen (RPO/RTO)

| Scope | RPO (max. Datenverlust) | RTO (Wiederanlauf) | Backup-Frequenz | Aufbewahrung |
|---|---|---|---|---|
| Compliance-Dokumente (`docs/compliance`) | 24h | 4h | täglich | 90 Tage |
| Compliance-Nachweise (`reports/compliance`) | 24h | 8h | täglich | 180 Tage |
| Kritische Betriebsdoku (`docs/OPERATIONS.md`, `docs/BACKLOG.md`) | 24h | 4h | täglich | 90 Tage |

## Backup-Policy (verbindlich)

1. **Automatisiertes tägliches Backup** der oben genannten Pfade.
2. **Immutable/append-only Ablage** der Backup-Snapshots, sofern technisch möglich.
3. **Versionierte Benennung** mit UTC-Timestamp (z. B. `backup-2026-03-01T08-00-00Z.tar.zst`).
4. **Integritätsprüfung je Backup-Lauf** (mindestens SHA256-Hash pro Artefakt).
5. **Keine Secrets im Klartext** in Backup-Protokollen oder README-Dateien.

## Restore-Workflow (verbindlich)

1. Restore-Fall klassifizieren (`partial` oder `full`) und Ticket/Incident-ID vergeben.
2. Letztes valides Backup anhand Hash + Manifest auswählen.
3. Restore in isolierter Zielumgebung durchführen (kein Blind-Restore direkt auf produktive Pfade).
4. Dateiintegrität gegen Manifest/Hash prüfen.
5. Funktionsprüfung ausführen (mindestens Doku-Lesbarkeit, Link-Integrität, Compliance-Ordnerstruktur).
6. Restore-Freigabe durch `IT Product Owner` oder `Compliance Lead` dokumentieren.
7. Ergebnis inkl. Abweichungen im Nachweisordner ablegen.

## Restore-Übung und Verifikation

- **Mindestens quartalsweise** einen Restore-Drill durchführen.
- Drill muss enthalten:
  - Restore eines vollständigen Compliance-Docs-Sets
  - Restore eines Nachweis-Samples aus `reports/compliance`
  - Verifikation der Hashes und der erwarteten Verzeichnisstruktur
- Bei fehlgeschlagenem Drill: Korrekturmaßnahmen innerhalb von 5 Arbeitstagen planen und nachverfolgen.

## Nachweisformat (verbindlich)

Ablagepfad:

- `reports/compliance/backup-restore/<YYYY>/<MM>/<restore_run_id>/`

Mindestartefakte:

- `restore_evidence.json` (Run-ID, Scope, Quelle, Ziel, Start/Ende, Ergebnis)
- `manifest.sha256` (Integritätsnachweis)
- `validation_notes.md` (Prüfresultate, Abweichungen, Freigabe)

## Rollen und Eskalation

| Rolle | Verantwortung |
|---|---|
| `IT Backend` | Backup-Läufe technisch betreiben/überwachen |
| `Compliance Lead` | Nachweisqualität und Auditierbarkeit freigeben |
| `IT Product Owner` | Priorisierung, Eskalation und Abnahme bei Restore-Übungen |

Eskalation:
- RPO/RTO-Verletzung oder fehlender Restore-Nachweis => sofortige Eskalation an `IT Product Owner` und `Compliance Lead`.

## Abgrenzung / Nicht-Ziele

- Diese Guideline ersetzt **kein** vollständiges Disaster-Recovery-Konzept für alle Infrastrukturkomponenten.
- Infrastruktur-spezifische Wiederanlaufdetails (z. B. ECS/IaC-Rebuild) bleiben in den bestehenden Ops-/Deploy-Runbooks verankert.

## Nachweis

- Backlog-Sync: `docs/BACKLOG.md`
- Kontrollplan-Referenz: `docs/compliance/EXPORT_DELETE_CONTROL_PLAN_V1.md`
- Umsetzungs-/Claim-Historie: `https://github.com/nimeob/geo-ranking-ch/issues/526`
