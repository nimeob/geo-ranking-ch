# BL-17 Runtime Credential Injection Inventory

Stand: 2026-02-27

## Ziel

Dieses Dokument beschreibt die reproduzierbare Inventarisierung von Runtime-Credential-Injection-Pfaden für **BL-17.wp5**.

Fokus:
- aktive Legacy-Injection-Pfade im laufenden OpenClaw-Kontext erkennen,
- Befunde als strukturiertes JSON-Evidence exportieren,
- pro Befund einen konkreten Migrations-/Removal-Next-Step festhalten.

## Read-only Erhebung

```bash
cd /data/.openclaw/workspace/geo-ranking-ch
./scripts/inventory_bl17_runtime_credential_paths.py \
  --output-json artifacts/bl17/runtime-credential-injection-inventory.json
```

Exit-Code-Interpretation:
- `0` = keine riskanten Injection-Befunde erkannt
- `10` = mindestens ein riskanter Befund erkannt (Legacy/Key-Injection)

## Evidence-Schema (JSON)

Pflichtfelder im Report:
- `generated_at_utc`
- `caller.arn`
- `caller.classification`
- `detections[]`
  - `id`, `detected`, `source_type`, `source`
  - `risk_level`, `effect`, `migration_next_step`, `owner`, `evidence`
- `summary.risk_ids`
- `summary.recommended_exit_code`

## Befundkategorien

Die Inventarisierung deckt u. a. folgende Pfade ab:

1. **Runtime-Caller-Klassifikation** (`aws sts get-caller-identity`)
2. **Statische Keys im Prozess-Environment** (`AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`)
3. **Web-Identity-Signal** (`AWS_WEB_IDENTITY_TOKEN_FILE`)
4. **Persistente Profile** (Shell-/Env-Dateien)
5. **AWS Config/Credentials Files** (`~/.aws/config`, `~/.aws/credentials`)
6. **OpenClaw-Konfig-Dateien** (`/data/.openclaw/*.json`)
7. **Scheduler-Pfade** (user/system `cron`, `systemd`)
8. **Verfügbarer Migrationspfad** (`scripts/aws_exec_via_openclaw_ops.sh`)

## Remediation-Leitlinie pro Befund

Für jeden `detected=true` Befund gilt:
- Legacy-/statische Key-Injection **entfernen** oder **depriorisieren**,
- AWS-Operationspfad auf **AssumeRole-first** (`aws_exec_via_openclaw_ops.sh`) umstellen,
- Fortschritt in `docs/LEGACY_IAM_USER_READINESS.md` + `docs/BACKLOG.md` nachführen.

## Verknüpfte Artefakte

- OIDC/AssumeRole Posture-Check: `scripts/check_bl17_oidc_assumerole_posture.sh`
- Fensteraggregation: `scripts/summarize_bl17_posture_reports.py`
- Haupt-Runbook: `docs/OPENCLAW_OIDC_FIRST_FALLBACK_PLAN.md`
- Legacy Readiness: `docs/LEGACY_IAM_USER_READINESS.md`
