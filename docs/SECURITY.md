# SECURITY.md — IAM, Credentials & API-Sicherheit (kanonisch)

> Dieses Dokument ist der **kanonische Ort** für alle Sicherheits- und Credential-Themen.
> Historische BL-spezifische Quelldokumente sind in `docs/archive/` archiviert.

Stand: 2026-03-01

---

## 1) Architekturentscheid AWS Auth (BL-15 / BL-17) — verbindlich

**Entscheid 2026-03-01 (final):**

| Pfad | Auth-Methode | Begründung |
|---|---|---|
| **CI/CD (GitHub Actions)** | OIDC-Only (`swisstopo-dev-github-deploy-role`) | Modern, auditierbar, kein statischer Key im Workflow |
| **OpenClaw Runtime** | Access Key + Secret | Bewusste Betriebsentscheidung, kein Migrationsrest |
| **Legacy-Key-Deaktivierung** | **nicht angestrebt** | OpenClaw-Runtime bleibt dauerhaft auf Key/Secret |

**BL-15 ist abgeschlossen.** Gate G3 (Consumer-Migration) ist als «accepted/retained» klassifiziert.

### BL-15.r2.wp3 — Legacy-Key Disable-Canary (Policy)

Neubewertung des bisherigen Disable-Canary (Legacy-Key-Deaktivierung) im Kontext der bestätigten Zielarchitektur:

- **Default-Entscheid:** **entfällt** (kein Pflicht-Blocker)
- **Begründung:** Der Canary war an einen Decommission-/Runtime-OIDC-Pfad gekoppelt, der **nicht** Zielzustand ist (Runtime bleibt Key/Secret; OIDC bleibt Deploy-only).
- **Governance-Regel:** Ein Disable-Canary ist als **optionaler** Härtungs-/Failover-Test zulässig, aber nur bei explizitem Bedarf, dokumentiertem Nutzen und vorbereitetem Rollback.

Entscheidungsmatrix (Minimum):

| Pfad | Trigger | Mindestnachweis |
|---|---|---|
| `entfällt` (Default) | Kein akuter Security-/Incident-Treiber | Verweis auf diese Policy + Parent-Sync (BL-15.r2) |
| `optional durchführen` | Konkreter Bedarf (z. B. Incident-Learning, Audit-Auflage, gezielter Failover-Test) | Ziel/Hypothese, Rollback-Plan, Evidence-Refs (CloudTrail/Logs), ggf. Wartungsfenster falls persistente Änderungen nötig |

---

## 2) Consumer-Inventar (BL-15)

| Consumer | Auth-Pfad | Status |
|---|---|---|
| GitHub Actions Deploy (`deploy.yml`) | OIDC Role Assume | ✅ migriert |
| OpenClaw-Umgebung (`76.13.144.185`, AI-Agent/Assistent) | Legacy Key/Secret | ✅ accepted/retained (Architekturentscheid 2026-03-01) |
| Lokale AWS-CLI Skripte (`scripts/*.sh`) | Abhängig vom Runtime-Context | 🟡 pro Script dokumentieren |

**IAM-User:** `arn:aws:iam::523234426229:user/swisstopo-api-deploy`
- 1 aktiver Key (`AKIAXTUZTXV25VQQLQMX`)
- Managed Policies: `IAMFullAccess`, `PowerUserAccess`
- Inline Policy: `swisstopo-dev-ecs-passrole`

---

## 3) Betriebsregeln (verbindlich)

1. CI/CD-Deploys: immer OIDC-Workflow verwenden (`deploy.yml`).
2. OpenClaw Runtime AWS-Ops: über den vorgesehenen Key/Secret-Pfad.
3. Keine Pflicht-Migration auf Runtime-OIDC/AssumeRole.
4. Security-Hygiene: Least-Privilege, Rotation, Audit.

**Nicht erlaubt:** Klartext-Secrets im Repo, in Commit-Historie, in Runbooks oder in persistenten Shell-Profilen.

---

## 4) Runtime Credential Injection (BL-17)

### Quick-Check (OIDC/AssumeRole-Posture)
```bash
cd /data/.openclaw/workspace/geo-ranking-ch
./scripts/check_bl17_oidc_assumerole_posture.sh
# Optional mit Evidence-Export:
BL17_POSTURE_REPORT_JSON=artifacts/bl17/posture-report.json ./scripts/check_bl17_oidc_assumerole_posture.sh
```

### Runtime Credential Inventory
```bash
./scripts/inventory_bl17_runtime_credential_paths.py \
  --output-json artifacts/bl17/runtime-credential-injection-inventory.json
```
- Exit `0`: keine riskanten Injection-Befunde
- Exit `10`: riskanter Befund (Legacy/Key-Injection)

### OIDC-only Guard (konsolidiert Runtime+CloudTrail)
```bash
./scripts/check_bl17_oidc_only_guard.py \
  --assume-role-first \
  --output-json artifacts/bl17/oidc-only-guard-report.json \
  --cloudtrail-lookback-hours 24
```
- Exit `0`: `ok`, Exit `10`: `fail`, Exit `20`: `warn`

### Persistenter Startpfad (kanonisch)
`Host-Orchestrator` → `/entrypoint.sh` → `runuser -u node -- node server.mjs` → `openclaw` → `openclaw-gateway`

---

## 5) Break-glass Runbook (Legacy-Fallback)

Zulässig **nur wenn alle** Bedingungen erfüllt:
1. Relevanter Betriebsablauf ist blockiert
2. Regulärer Runtime-Key/Secret-Pfad ist konkret blockiert
3. Scope auf Minimum eingegrenzt

**Ablauf:**
1. Fallback-ID vergeben (`legacy-fallback-YYYY-MM-DD-nnn`)
2. Primärpfad-Blocker belegen
3. Legacy-Scope minimal ausführen (zeitlich begrenzt)
4. Zurück in regulären Betrieb + Recheck
5. Log nach Template-Format (Pflichtfelder: `fallback_id`, `timestamp_utc`, `actor`, `reason`, `scope`, `started/ended_utc`, `duration_minutes`, `outcome`, `rollback_needed`, `evidence.cloudtrail_window_utc`, `evidence.refs`, `follow_up.issue`)

Ablageort für Fallback-Log-Einträge: `docs/archive/LEGACY_IAM_USER_READINESS.md` → Abschnitt "Fallback-Log Entries".

**Template:** `docs/archive/LEGACY_FALLBACK_LOG_TEMPLATE.md`

---

## 6) Datenhaltung & API-Sicherheit (BL-06 / BL-07)

### Datenhaltung: Stateless (BL-06)

**Entscheid:** Keine persistente Datenbank in `dev` (weder RDS noch DynamoDB).
- Request rein → Analyse → Response raus — kein persistenter Zustand
- Trigger für DB-Einführung erst bei: hoher Repeat-Query-Last, fachlichem Audit-Bedarf, oder Feature-Anforderung für gespeicherten Zustand
- **Falls Persistenz nötig:** DynamoDB-first, Tabelle `swisstopo-dev-analysis-cache`, Partition Key `request_hash`, TTL aktiv (24–72h)

### API-Sicherheit `/analyze` (BL-07)

**Zielbild Auth:**
1. Durchsetzungspunkt am Edge: ALB + AWS WAF
2. Client-Authentisierung: Bearer/API-Key aus Secret Manager/SSM
3. Autorisierung: Scope-basiert (`analyze:invoke`)

**Rate-Limit:** AWS WAF Rate-based Rule vor ALB (primär), App-seitiges Soft-Limit als Fallback.
Richtwert: 100 Requests / 5 Minuten pro IP auf `/analyze`.

**Secret-Handling (Mindestanforderungen):**
1. Speicherung: nur in AWS Secrets Manager oder SSM Parameter Store (`SecureString`)
2. Transport: nur TLS, keine Token in Query-Parametern
3. Injection: via ECS Task-Definition `secrets`, kein Klartext in Images
4. Logging: Token nie loggen, Header/Secrets maskieren
5. Rotation: definierter Turnus + Dual-Key-Rollover
6. IAM: Least-Privilege auf Secret-Pfade

---

## 7) Abbauplan Legacy-Key (referenziell)

1. Phase 1 (Beobachtung): 48h ohne notwendigen Legacy-Direktzugriff
2. Phase 2 (Soft-Cut): Legacy-Rechte weiter reduzieren, nur Notfallpfad
3. Phase 3 (Final): Key deaktivieren, 24h Monitoring, Dekommission

> Hinweis: Finale Abschaltung erst nach vollständiger Inventarisierung aller Consumer (BL-15 abgeschlossen).

---

## 8) Verweise

- Archivierte Quelldokumente: `docs/archive/`
  - `LEGACY_IAM_USER_READINESS.md` (vollständiges BL-15-Audit + Fallback-Log)
  - `LEGACY_CONSUMER_INVENTORY.md` (Consumer-Matrix + CloudTrail-Fingerprints)
  - `OPENCLAW_OIDC_FIRST_FALLBACK_PLAN.md` (detailliertes Runbook)
  - `BL17_RUNTIME_CREDENTIAL_INJECTION_INVENTORY.md` (Inventarisierungs-Anleitung)
  - `DATA_AND_API_SECURITY.md` (BL-06/07 Originalentscheid)
- Check-Script: `scripts/check_bl17_oidc_assumerole_posture.sh`
- Inventory-Script: `scripts/inventory_bl17_runtime_credential_paths.py`
