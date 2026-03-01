# OpenClaw AWS Auth: OIDC-first + AssumeRole-first (Legacy nur Fallback)

## Zielbild
Für dieses Projekt gilt ein **Hybrid-Standard**:

1. **CI/CD über GitHub Actions OIDC** (ohne statische AWS-Keys in Workflows)
2. **Direkte OpenClaw-Administration über STS AssumeRole**
3. **Legacy-IAM-User nur als kontrollierter Fallback**

Damit bleibt volle AWS-Verwaltung möglich, ohne den Legacy-Key als Primärmechanismus zu betreiben.

---

## Aktueller Ist-Stand (2026-02-26)

### OIDC-Pfad (CI/CD)
- Workflow `/.github/workflows/deploy.yml` nutzt `aws-actions/configure-aws-credentials@v4` mit OIDC.
- Rolle: `arn:aws:iam::523234426229:role/swisstopo-dev-github-deploy-role`

### Direkter OpenClaw-Pfad (AssumeRole)
- Ops-Rolle: `arn:aws:iam::523234426229:role/openclaw-ops-role`
- Trust erlaubt `sts:AssumeRole` für `arn:aws:iam::523234426229:user/swisstopo-api-deploy`
- Helper-Scripts vorhanden:
  - `scripts/aws_assume_openclaw_ops.sh` (interaktive Session)
  - `scripts/openclaw_runtime_assumerole_exec.sh` (Runtime-Start ohne statische Legacy-Keys als Default)

### Legacy-User
- User: `swisstopo-api-deploy`
- Ist absichtlich noch nicht final dekommissioniert (Fallback/Transition)

---

## Betriebsregeln (verbindlich)

1. **CI/CD-Deploys:** immer OIDC-Workflow verwenden.
2. **Direkte AWS-Operationen in OpenClaw:** zuerst `AssumeRole` in `openclaw-ops-role`.
3. **Legacy-Identity direkt verwenden:** nur bei Blocker/Incident und kurz dokumentieren.
4. **Jede Fallback-Nutzung** mit standardisiertem Minimalformat protokollieren:
   - Template: `docs/LEGACY_FALLBACK_LOG_TEMPLATE.md`
   - Journal: `docs/LEGACY_IAM_USER_READINESS.md` (Section "Fallback-Log Entries")

---

## Runbook: Direkter Betrieb via AssumeRole

### 1) Runtime-Default (AssumeRole-first) starten
```bash
cd /data/.openclaw/workspace/geo-ranking-ch
./scripts/openclaw_runtime_assumerole_exec.sh <dein-openclaw-kommando>
# Beispiel:
./scripts/openclaw_runtime_assumerole_exec.sh openclaw gateway status
```

Dieser Pfad ersetzt langlebige Legacy-Keys im Prozesskontext durch temporäre STS-Session-Credentials (`ASIA...` + `AWS_SESSION_TOKEN`) und ist der neue Default für Runtime-Starts.

### 2) Interaktiver Rollenwechsel (Fallback für manuelle Shell)
```bash
cd /data/.openclaw/workspace/geo-ranking-ch
source ./scripts/aws_assume_openclaw_ops.sh
```

### 3) Identität verifizieren
```bash
aws sts get-caller-identity
# Erwartet: arn:aws:sts::523234426229:assumed-role/openclaw-ops-role/<session>
```

### 4) Beispiel-Sanity-Checks
```bash
aws ecs list-clusters --region eu-central-1
aws cloudwatch describe-alarms --region eu-central-1 --max-items 5
```

### 5) Session-Hygiene
- STS-Session ist temporär.
- Für längere Arbeitsschritte regelmäßig neu assumen.

---

## Verifikation / Compliance-Checks

### A) OIDC bleibt primär für Deploy
- `deploy.yml` enthält:
  - `permissions: id-token: write`
  - `configure-aws-credentials` mit `role-to-assume`

### B) Direktzugriffe laufen über angenommene Rolle
- CloudTrail-Abfragen zeigen `assumed-role/openclaw-ops-role/...` als Principal für OpenClaw-Operationen.

### C) Legacy nur Fallback
- Keine Routine-Aktivität auf Principal `...:user/swisstopo-api-deploy` außerhalb definierter Fallback-Fenster.

### D) Automatischer Quick-Check (BL-17)
```bash
cd /data/.openclaw/workspace/geo-ranking-ch
./scripts/check_bl17_oidc_assumerole_posture.sh
```
- Prüft OIDC-Marker in Workflows (`id-token: write`, `configure-aws-credentials`).
- Prüft auf statische AWS-Key-Referenzen in aktiven Workflows.
- Klassifiziert den aktiven Runtime-Caller (AssumeRole vs. Legacy-User).
- Führt die bestehenden Read-only Audits (`audit_legacy_aws_consumer_refs.sh`, `audit_legacy_runtime_consumers.sh`) als Kontext mit aus.

Optionaler Evidence-Export (für reproduzierbare Nachweise in BL-17/BL-15):
```bash
./scripts/check_bl17_oidc_assumerole_posture.sh --report-json artifacts/bl17/posture-report.json
# alternativ via ENV:
BL17_POSTURE_REPORT_JSON=artifacts/bl17/posture-report.json ./scripts/check_bl17_oidc_assumerole_posture.sh
```
Der JSON-Report enthält mindestens Timestamp, Caller-Klassifikation und relevante Exit-Codes (`workflow_check`, `caller_check`, Kontext-Audits, final).

Runtime-Credential-Injection-Inventar (BL-17.wp5):
```bash
./scripts/inventory_bl17_runtime_credential_paths.py \
  --output-json artifacts/bl17/runtime-credential-injection-inventory.json
```

Runtime-Default-Nachweis (AssumeRole-first Startpfad):
```bash
./scripts/openclaw_runtime_assumerole_exec.sh \
  ./scripts/inventory_bl17_runtime_credential_paths.py \
  --output-json artifacts/bl17/runtime-credential-injection-inventory-after-assumerole-default.json
```

- Exit `0`: keine riskanten Injection-Befunde erkannt
- Exit `10`: riskante Injection-Befunde erkannt (Legacy/Key-Injection)
- Details/DoD: `docs/BL17_RUNTIME_CREDENTIAL_INJECTION_INVENTORY.md`

Zeitfenster-Aggregation (z. B. für 48h Legacy-Fallback-Beobachtung):
```bash
./scripts/summarize_bl17_posture_reports.py \
  --glob "artifacts/bl17/posture-*.json" \
  --min-reports 2 \
  --output-json artifacts/bl17/posture-window-summary.json
```
- Exit `0`: Window ist "ready" (kein Legacy-Caller, keine non-zero final exits).
- Exit `10`: Window ist "not-ready" (Legacy beobachtet, non-zero Exit oder zu wenige Reports).
- Exit `2`: ungültige Eingaben/Report-Dateien.

OIDC-only Guard (konsolidierter Runtime+CloudTrail-Nachweis, BL-17.wp7):
```bash
./scripts/check_bl17_oidc_only_guard.py \
  --assume-role-first \
  --output-json artifacts/bl17/oidc-only-guard-report.json \
  --cloudtrail-lookback-hours 24
```
- Output-Schema: `status = ok|warn|fail`, `execution_mode = ambient-runtime|assume-role-first` + `checks.*.evidence_paths`.
- Exit `0`: konsolidiert `ok` (kein Legacy-Befund in Posture/Runtime/CloudTrail).
- Exit `10`: konsolidiert `fail` (Legacy-Befund erkannt).
- Exit `20`: konsolidiert `warn` (Teilcheck inkonsistent/nicht eindeutig).

---

## Break-glass Runbook (Legacy-Fallback, BL-17.wp8)

Ziel: Der Legacy-IAM-User bleibt nur ein **zeitlich begrenzter Notfallpfad**. Jede Nutzung ist evidenzpflichtig und muss auf den AssumeRole/OIDC-Primärpfad zurückgeführt werden.

### Trigger (erlaubte Fälle)

Legacy-Fallback ist nur zulässig, wenn **alle** Bedingungen erfüllt sind:

1. Ein relevanter Betriebsablauf ist blockiert (z. B. Incident, kritischer Deploy-/Ops-Blocker).
2. OIDC- oder AssumeRole-Primärpfad ist für den konkreten Ablauf aktuell nicht nutzbar.
3. Scope ist auf das notwendige Minimum eingegrenzt (kein "Convenience-Fallback").

Nicht zulässig: Routinearbeiten, reine Bequemlichkeit oder fehlende Vorprüfung des Primärpfads.

### Ablauf (verbindlich)

1. **Fallback-ID vergeben** (z. B. `legacy-fallback-YYYY-MM-DD-<nnn>`) und Incident-Context eröffnen.
2. **Primärpfad-Blocker kurz belegen** (Fehlermeldung/Command-Output, read-only).
3. **Legacy-Scope minimal ausführen** (zeitlich begrenzt, nur notwendige Kommandos).
4. **Unmittelbar zurück auf AssumeRole-first** wechseln und Recheck fahren.
5. **Fallback-Log vollständig dokumentieren** nach Template:
   - `docs/LEGACY_FALLBACK_LOG_TEMPLATE.md`
   - Ablage im Journal: `docs/LEGACY_IAM_USER_READINESS.md` (Section "Fallback-Log Entries").

### Evidenz-Checkliste (Pflichtfelder)

- `fallback_id`, `timestamp_utc`, `actor`
- `reason` (konkreter Primärpfad-Blocker), `scope` (konkrete Legacy-Kommandos)
- `started_utc`, `ended_utc`, `duration_minutes`, `outcome`, `rollback_needed`
- `evidence.cloudtrail_window_utc`
- `evidence.refs` (mindestens Log + CloudTrail-Beleg + Runtime/Posture-Beleg)
- `follow_up.issue` + `follow_up.action` (bei `partial|failed` zwingend)

### Mindest-Nachweise / Prüfpunkte (read-only)

```bash
# 1) CloudTrail-Fingerprint im Fallback-Fenster
LOOKBACK_HOURS=2 ./scripts/audit_legacy_cloudtrail_consumers.sh \
  > artifacts/legacy-fallback/<fallback_id>-cloudtrail.txt

# 2) Runtime-Credential-Inventar nach Rückkehr auf AssumeRole-first
./scripts/inventory_bl17_runtime_credential_paths.py \
  --output-json artifacts/legacy-fallback/<fallback_id>-runtime-inventory.json

# 3) OIDC/AssumeRole-Posture-Recheck
./scripts/check_bl17_oidc_assumerole_posture.sh \
  --report-json artifacts/legacy-fallback/<fallback_id>-posture.json
```

Optionaler Konsolidierungs-Check:

```bash
./scripts/check_bl17_oidc_only_guard.py \
  --assume-role-first \
  --output-json artifacts/legacy-fallback/<fallback_id>-oidc-only-guard.json \
  --cloudtrail-lookback-hours 24
```

### Vollständig ausgefülltes synthetisches Beispiel (read-only)

Ein ausgefülltes Referenz-Event (inkl. CloudTrail-/Inventory-/Posture-Refs) steht unter:
- `docs/LEGACY_IAM_USER_READINESS.md` → Abschnitt **"Synthetisches Vollbeispiel (BL-17.wp8)"**

## Rollback (wenn AssumeRole-Flow blockiert)

1. Incident dokumentieren (`was/warum/wann`).
2. Zeitlich begrenzt Legacy-Pfad gemäß Break-glass-Runbook nutzen.
3. Nach Stabilisierung zurück auf AssumeRole-first, Recheck + Evidenz sichern.
4. Root-Cause + dauerhafte Korrektur dokumentieren.

---

## Abbauplan Legacy

1. **Phase 1 (Beobachtung):** 48h ohne notwendigen Legacy-Direktzugriff.
2. **Phase 2 (Soft-Cut):** Legacy-Rechte weiter reduzieren, nur Notfallpfad belassen.
3. **Phase 3 (Final):** Key deaktivieren, Monitoring 24h, dann kontrollierte Dekommission.

Hinweis: Finale Abschaltung erst nach vollständiger Inventarisierung externer Consumer (BL-15).
