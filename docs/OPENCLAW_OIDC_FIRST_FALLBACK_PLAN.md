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
- Helper-Script vorhanden: `scripts/aws_assume_openclaw_ops.sh`

### Legacy-User
- User: `swisstopo-api-deploy`
- Ist absichtlich noch nicht final dekommissioniert (Fallback/Transition)

---

## Betriebsregeln (verbindlich)

1. **CI/CD-Deploys:** immer OIDC-Workflow verwenden.
2. **Direkte AWS-Operationen in OpenClaw:** zuerst `AssumeRole` in `openclaw-ops-role`.
3. **Legacy-Identity direkt verwenden:** nur bei Blocker/Incident und kurz dokumentieren.
4. **Jede Fallback-Nutzung** mit Grund + Scope + Ergebnis in `docs/LEGACY_IAM_USER_READINESS.md` protokollieren.

---

## Runbook: Direkter Betrieb via AssumeRole

### 1) Rollenwechsel
```bash
cd /data/.openclaw/workspace/geo-ranking-ch
source ./scripts/aws_assume_openclaw_ops.sh
```

### 2) Identität verifizieren
```bash
aws sts get-caller-identity
# Erwartet: arn:aws:sts::523234426229:assumed-role/openclaw-ops-role/<session>
```

### 3) Beispiel-Sanity-Checks
```bash
aws ecs list-clusters --region eu-central-1
aws cloudwatch describe-alarms --region eu-central-1 --max-items 5
```

### 4) Session-Hygiene
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

---

## Rollback (wenn AssumeRole-Flow blockiert)

1. Incident dokumentieren (`was/warum/wann`).
2. Zeitlich begrenzt Legacy-Pfad nutzen, um Betrieb zu sichern.
3. Nach Stabilisierung zurück auf AssumeRole-first.
4. Root-Cause + dauerhafte Korrektur dokumentieren.

---

## Abbauplan Legacy

1. **Phase 1 (Beobachtung):** 48h ohne notwendigen Legacy-Direktzugriff.
2. **Phase 2 (Soft-Cut):** Legacy-Rechte weiter reduzieren, nur Notfallpfad belassen.
3. **Phase 3 (Final):** Key deaktivieren, Monitoring 24h, dann kontrollierte Dekommission.

Hinweis: Finale Abschaltung erst nach vollständiger Inventarisierung externer Consumer (BL-15).
