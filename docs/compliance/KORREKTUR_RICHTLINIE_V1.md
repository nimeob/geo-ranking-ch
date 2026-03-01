# Minimum-Compliance-Set — Korrektur-Richtlinie v1

_Status: freigegeben (Repo-Baseline)_  
_Gültig ab: 2026-03-01_  
_Bezug: Issue #516_

## Zweck

Diese Richtlinie legt verbindlich fest, wie fachliche oder technische Korrekturen an bereits erfassten Policy-/Compliance-Dokumenten durchzuführen sind.

Kernprinzip: **Das Original bleibt unverändert.** Jede Korrektur wird als **neue Version** dokumentiert und enthält ein verpflichtendes Feld **`korrekturgrund`**.

## Geltungsbereich

- Alle Policies und Nachweisartefakte im Kontext des Minimum-Compliance-Sets (BL-342)
- Relevante Bereiche: Korrektur, Aufbewahrung/Löschung, Export, Hold
- Gilt für `dev`, `staging` und `prod` als inhaltlicher Governance-Standard

## Verbindliche Regeln

1. **Keine Überschreibung des Originals**
   - Bereits freigegebene Inhalte dürfen nicht in-place ersetzt werden.
   - Das Original bleibt referenzierbar und auditierbar erhalten.
2. **Korrekturen nur als neue Version**
   - Jede Korrektur erzeugt einen neuen Versionsstand (`v<major>.<minor>` gemäß Policy-Standard).
   - Der neue Stand muss auf den Vorgänger verweisen (`supersedes_version`).
3. **Pflichtfeld `korrekturgrund`**
   - Jede Korrektur enthält eine nachvollziehbare Begründung (`korrekturgrund`).
   - Leerwerte, Platzhalter oder rein technische Kürzel ohne Kontext sind unzulässig.
4. **Wirksamkeit und Nachweis**
   - Der neue Stand enthält `wirksam_ab` und eine verlinkte Nachweisreferenz (Issue/Decision/Review).
   - Änderungen ohne Nachweis gelten als nicht freigegeben.

## Pflichtfelder für Korrektur-Einträge

| Feld | Pflicht | Regel |
|---|---|---|
| `version` | ja | Neuer Versionsstand (`v<major>.<minor>`) |
| `supersedes_version` | ja | Referenz auf abgelösten Stand |
| `korrekturgrund` | ja | Verständliche, prüfbare Begründung |
| `wirksam_ab` | ja | ISO-Datum (`YYYY-MM-DD`) |
| `approved_by_role` | ja | Freigabe durch verantwortliche Rolle |
| `evidence_ref` | ja | Link auf Ticket/Review/Entscheid |

## Minimaler Ablauf (v1)

1. Korrekturbedarf identifizieren und als Änderungsvorschlag dokumentieren
2. Neue Version mit vollständigen Pflichtfeldern erfassen
3. Fachliche Prüfung durch `Compliance Lead`
4. Freigabe durch `approved_by_role`
5. Veröffentlichung im Repo + Backlog-/Issue-Verweis aktualisieren

## Kommunikation (Freigabe-Definition)

Die Richtlinie gilt als **veröffentlicht und kommuniziert**, wenn:

- der Richtlinientext im Repo vorliegt,
- das zugehörige Issue den Abschluss dokumentiert,
- die Backlog-Referenz (`docs/BACKLOG.md`) auf abgeschlossen gesetzt ist.

## Referenztemplate (Copy/Paste)

```yaml
version: v1.1
supersedes_version: v1.0
korrekturgrund: "Abschnitt zu Pflichtfeldvalidierung präzisiert; unklare Freitextregel entfernt"
wirksam_ab: "2026-03-05"
approved_by_role: "Compliance Lead"
evidence_ref: "https://github.com/nimeob/geo-ranking-ch/issues/516"
```

## Abgrenzung / Nicht-Ziele

- Diese Richtlinie implementiert selbst keine Runtime-Validierung.
- Technische Durchsetzung (Workflow, Pflichtfeld-Checks, Datenmodell) erfolgt in separaten Issues (u. a. #520, #521, #519).

## Nachweis

- Backlog-Sync: `docs/BACKLOG.md`
- Umsetzung/Claim-Historie: `https://github.com/nimeob/geo-ranking-ch/issues/516`
