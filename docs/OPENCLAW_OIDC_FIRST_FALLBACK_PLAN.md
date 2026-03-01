# OpenClaw AWS Auth: OIDC für Deploy, Key/Secret für Runtime

## Zielbild
Für dieses Projekt gilt folgende **verbindliche Trennung**:

1. **CI/CD über GitHub Actions OIDC** (ohne statische AWS-Keys in Workflows)
2. **OpenClaw Runtime-Zugriffe auf AWS über Access Key + Secret**
3. **Kein Runtime-OIDC-Zwang** für direkte OpenClaw-Operationen

Damit bleibt der Deploy-Pfad modern/auditierbar und der OpenClaw-Runtime-Pfad stabil gemäß Betriebsentscheidung.

---

## Aktueller Ist-Stand (2026-03-01)

### OIDC-Pfad (CI/CD)
- Workflow `/.github/workflows/deploy.yml` nutzt `aws-actions/configure-aws-credentials@v4` mit OIDC.
- Rolle: `arn:aws:iam::523234426229:role/swisstopo-dev-github-deploy-role`

### OpenClaw Runtime-Pfad (direkter Betrieb)
- Runtime nutzt Access Key + Secret (Host-/Runtime-Kontext).
- Diese Nutzung ist eine bewusste Betriebsentscheidung und **kein Migrationsrest**.

### Legacy-User
- User: `swisstopo-api-deploy`
- Bleibt für OpenClaw-Runtime aktuell aktiv vorgesehen.

---

## Betriebsregeln (verbindlich)

1. **CI/CD-Deploys:** immer OIDC-Workflow verwenden.
2. **Direkte AWS-Operationen in OpenClaw Runtime:** Nutzung über den vorgesehenen Key/Secret-Pfad.
3. **Keine Pflicht-Migration auf Runtime-OIDC/AssumeRole** in BL-15.r2.
4. Security-Hygiene für Runtime-Key-Pfad bleibt Pflicht (Least-Privilege, Rotation, Audit).

---

## Runbook: Direkter OpenClaw-Betrieb (Runtime Key/Secret)

### 1) Runtime-Caller verifizieren
```bash
aws sts get-caller-identity
```

### 2) Basis-Sanity-Checks
```bash
aws ecs list-clusters --region eu-central-1
aws cloudwatch describe-alarms --region eu-central-1 --max-items 5
```

### 3) OIDC-Deploy bleibt separat
- Deploy-Validierung erfolgt über GitHub Workflow (`deploy.yml`) und OIDC-Role.

> Hinweis: Helper für AssumeRole (`scripts/aws_assume_openclaw_ops.sh`, `scripts/openclaw_runtime_assumerole_exec.sh`) können für Diagnostik bestehen bleiben, sind aber **nicht** mehr der verpflichtende Runtime-Default.

### 4) Startpfad-/Host-Änderungen (nur falls technisch nötig)
- **Default:** Keine Änderungen am Host-Orchestrator-Startpfad für reine Doku-/Policy-Synchronisierung.
- **Nur bei echtem Technikbedarf:** Persistente Startpfad-Anpassungen (z. B. `/entrypoint.sh`, Container-Env-Injektion, Runtime-Restart) ausschließlich im Wartungsfenster mit dokumentiertem Rollback.
- **Allowed Runtime-Key-Setpoints:** Secrets/Env-Management des Hosts/Orchestrators (nicht im Repo als Klartext, nicht in Commit-Historie).

---

## Verifikation / Compliance-Checks

### A) OIDC bleibt primär für Deploy
- `deploy.yml` enthält:
  - `permissions: id-token: write`
  - `configure-aws-credentials` mit `role-to-assume`

### B) Runtime-Zugriffe folgen der Betriebsentscheidung
- OpenClaw-Runtime-Zugriffe auf AWS dürfen über den vorgesehenen Key/Secret-Principal laufen.

### C) Deploy-Pfad bleibt strikt OIDC
- Keine statischen AWS-Keys in aktiven GitHub-Deploy-Workflows.

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

Historischer Runtime-Vergleichsnachweis (AssumeRole-gekapselter Startpfad):
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

Ziel: Runtime-Key-Nutzung ist regulär erlaubt; bei Abweichungen/Incidents bleibt jede Sondernutzung evidenzpflichtig und nachvollziehbar dokumentiert.

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
4. **Unmittelbar zurück in den regulären Runtime-Betrieb** wechseln und Recheck fahren.
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

# 2) Runtime-Credential-Inventar nach Rückkehr in den regulären Betrieb
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
3. Nach Stabilisierung zurück in den regulären Runtime-Betrieb, Recheck + Evidenz sichern.
4. Root-Cause + dauerhafte Korrektur dokumentieren.

---

## Abbauplan Legacy

1. **Phase 1 (Beobachtung):** 48h ohne notwendigen Legacy-Direktzugriff.
2. **Phase 2 (Soft-Cut):** Legacy-Rechte weiter reduzieren, nur Notfallpfad belassen.
3. **Phase 3 (Final):** Key deaktivieren, Monitoring 24h, dann kontrollierte Dekommission.

Hinweis: Finale Abschaltung erst nach vollständiger Inventarisierung externer Consumer (BL-15).
