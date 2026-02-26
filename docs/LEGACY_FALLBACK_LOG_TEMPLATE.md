# Legacy Fallback Logging Template (BL-17.wp2)

Ziel: Legacy-Fallbacks (direkte Nutzung des IAM-Users `swisstopo-api-deploy`) einheitlich, kurz und maschinenlesbar dokumentieren.

## 1) Markdown-Minimaltemplate (verbindlich)

```markdown
### Legacy Fallback Entry — <fallback_id>

- timestamp_utc: <YYYY-MM-DDTHH:MM:SSZ>
- actor: <user|runner|workflow>
- reason: <warum war OIDC/AssumeRole nicht nutzbar?>
- scope: <betroffene Aktion/Command-Gruppe>
- started_utc: <YYYY-MM-DDTHH:MM:SSZ>
- ended_utc: <YYYY-MM-DDTHH:MM:SSZ>
- duration_minutes: <integer>
- outcome: <success|partial|failed>
- rollback_needed: <yes|no>
- evidence:
  - cloudtrail_window_utc: <from..to>
  - refs:
    - <relativer Pfad auf Artefakt/Log>
    - <relativer Pfad auf Artefakt/Log>
- follow_up:
  - issue: <#123 oder n/a>
  - action: <kurze nächste Maßnahme>
```

## 2) Optionales JSON-Snippet (für Aggregation/Parsing)

```json
{
  "fallback_id": "legacy-fallback-2026-02-26-001",
  "timestamp_utc": "2026-02-26T23:20:00Z",
  "actor": "openclaw-host",
  "reason": "OIDC workflow_dispatch API timeout",
  "scope": "aws ecs describe-services --cluster swisstopo-dev-cluster --services swisstopo-dev-service",
  "started_utc": "2026-02-26T23:18:00Z",
  "ended_utc": "2026-02-26T23:20:00Z",
  "duration_minutes": 2,
  "outcome": "success",
  "rollback_needed": "no",
  "evidence": {
    "cloudtrail_window_utc": "2026-02-26T23:00:00Z..2026-02-26T23:30:00Z",
    "refs": [
      "artifacts/legacy-fallback/2026-02-26-001.log",
      "artifacts/legacy-fallback/2026-02-26-001-cloudtrail.json"
    ]
  },
  "follow_up": {
    "issue": "#137",
    "action": "OIDC timeout root cause analysieren und Retry-Policy anpassen"
  }
}
```

## 3) Ausfüllregeln

- `timestamp_utc`, `started_utc`, `ended_utc` immer in UTC (`Z`-Suffix).
- `scope` soll den tatsächlich ausgeführten Legacy-Scope eindeutig beschreiben (Befehl/Workflow/Service).
- `reason` muss den Blocker benennen (nicht nur "ging nicht").
- `outcome=partial|failed` erfordert zwingend einen Follow-up-Issue-Link.
- Evidence-Referenzen immer als relative Repo-Pfade notieren.

## 4) Beispiel-Eintrag (ausgefüllt)

```markdown
### Legacy Fallback Entry — legacy-fallback-2026-02-26-002

- timestamp_utc: 2026-02-26T23:52:00Z
- actor: openclaw-host
- reason: AssumeRole-Aufruf lieferte mehrfach Throttling, Incident-Fenster aktiv
- scope: aws cloudwatch describe-alarms --region eu-central-1 --max-items 5
- started_utc: 2026-02-26T23:50:00Z
- ended_utc: 2026-02-26T23:52:00Z
- duration_minutes: 2
- outcome: success
- rollback_needed: no
- evidence:
  - cloudtrail_window_utc: 2026-02-26T23:45:00Z..2026-02-27T00:00:00Z
  - refs:
    - artifacts/legacy-fallback/2026-02-26-002.log
    - artifacts/legacy-fallback/2026-02-26-002-cloudtrail.json
- follow_up:
  - issue: #138
  - action: Runtime-Evidence-Export um Throttling-Klassifikation ergänzen
```

## 5) Ablageort

- Primäre Dokumentation der realen Fallbacks: `docs/LEGACY_IAM_USER_READINESS.md` (Section "Fallback-Log Entries").
- Operative Regel/Verweis: `docs/OPENCLAW_OIDC_FIRST_FALLBACK_PLAN.md`.
