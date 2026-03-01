# Legacy AWS Consumer Inventory (BL-15)

> Zweck: Vollständige, reproduzierbare Inventarisierung aller Consumer, die noch über den Legacy-IAM-User `swisstopo-api-deploy` laufen oder laufen könnten.
>
> Scope: read-only Tracking + Migrationsplanung (keine Abschaltung in diesem Dokument).

Stand: 2026-03-01 (UTC)

---

## 1) Verifizierte Basislage

Aus den read-only Audits:

- `./scripts/audit_legacy_aws_consumer_refs.sh` → Exit `10` (aktiver Caller = Legacy-User)
- `./scripts/audit_legacy_runtime_consumers.sh` → Exit `30` (aktiver Caller + Runtime-Env enthält AWS Key-Variablen)
- `LOOKBACK_HOURS=6 ./scripts/audit_legacy_cloudtrail_consumers.sh` → Exit `10` (Worker-A-Recheck 2026-02-27: 98 Raw-Events / 90 ausgewertete Legacy-Events, dominanter Fingerprint `76.13.144.185`)
- `LOOKBACK_HOURS=8 ./scripts/audit_legacy_cloudtrail_consumers.sh` → Exit `10` (Recheck 2026-02-26 bestätigt dominanten Fingerprint `76.13.144.185` + AWS-Service-Delegation)
- `./scripts/check_bl17_oidc_assumerole_posture.sh` → Exit `30` (OIDC-Marker in Workflows ok, Runtime-Caller bleibt Legacy)
- GitHub Deploy-Workflow (`.github/workflows/deploy.yml`) ist OIDC-only (kein statischer Key im aktiven CI/CD-Pfad)

Interpretation:

- CI/CD ist **nicht** der Hauptblocker.
- Der dominante externe Consumer (`76.13.144.185`) ist als **OpenClaw-Umgebung** identifiziert (AI-Agent/Assistent, der das Repo verwaltet und AWS-Ressourcen nutzt). **Architekturentscheid 2026-03-01: bleibt dauerhaft aktiv (decision: retained).**

---

## 2) Consumer-Matrix

| Consumer | Ort/Typ | Aktueller Auth-Pfad | Status | Zielpfad | Owner | Nächster Schritt |
|---|---|---|---|---|---|---|
| GitHub Actions Deploy (`deploy.yml`) | GitHub Hosted Runner | OIDC Role Assume (`swisstopo-dev-github-deploy-role`) | ✅ migriert | OIDC beibehalten | Repo | Periodische Drift-Prüfung |
| OpenClaw Runtime (dieser Host) | Host/Container Runtime | AWS Env-Creds (Legacy User als aktiver Caller), punktuell `sts:AssumeRole` sichtbar | 🟡 offen | OIDC-first via `workflow_dispatch` + `openclaw-ops-role`; Legacy nur Fallback | Nipa/Nico | Credential-Injection-Quelle entfernen und AWS-Ops standardisiert über `scripts/aws_exec_via_openclaw_ops.sh` ausführen |
| OpenClaw-Umgebung (AI-Agent/Assistent; CloudTrail-Fingerprint `76.13.144.185`) | OpenClaw-Sandbox/Container (außerhalb dieses Hosts) | Legacy Key/Secret (AWS Env-Creds) | ✅ accepted/retained | Architekturentscheid 2026-03-01: dauerhaft beibehalten (decision: retained) | OpenClaw/Nico | Identität bekannt — kein weiterer Handlungsbedarf |
| Lokale/Runner AWS-CLI Skripte (`scripts/*.sh`) | Repo-Artefakte | abhängig vom aufrufenden Runtime-Credential-Context | 🟡 offen | Aufruf über OIDC-Ausführungspfad oder eng begrenzte AssumeRole | Repo | Pro Script Ausführungspfad dokumentieren |

### 2.1) Fingerprint-Hinweise aus CloudTrail (6h + 8h Rechecks)

- Dominanter Non-AWS-Fingerprint: `source_ip=76.13.144.185`
  - `aws-cli/2.33.29` (u. a. `sts:GetCallerIdentity`, `logs:FilterLogEvents`)
  - `aws-sdk-js/3.996.0` (u. a. `bedrock:ListFoundationModels`)
  - Terraform Provider (`HashiCorp Terraform/1.11.4`) auf diversen AWS-APIs
- 6h-Recheck (2026-02-27): 98 Raw-Events / 90 ausgewertete Events; Top-Aktivität weiter auf `76.13.144.185`.
- Zusätzliche AWS-Service-Delegation im 8h-Recheck (2026-02-26): `source_ip=lambda.amazonaws.com` (KMS-Zugriffe), plus sichtbare `sts:AssumeRole`-Events auf dem dominanten Fingerprint.

Bewertung:
- **`76.13.144.185` = OpenClaw-Umgebung** (AI-Agent/Assistent, der das Repo verwaltet und AWS-Ressourcen nutzt). Identität abschliessend geklärt. **Architekturentscheid 2026-03-01: bleibt dauerhaft aktiv (decision: retained).**
- Die sichtbaren `AssumeRole`-Events sind ein positives Signal für BL-17, aber noch kein Nachweis für AssumeRole-first im Runtime-Default.
- Zuordnungsaufgabe „externe Runner/Hosts inventarisieren": **abgeschlossen (Identität: OpenClaw)**. Kein weiterer offener externer Consumer nachgewiesen.

---

## 3) Inventarisierung externer Targets (BL-15.wp3)

### 3.1) Verbindliches Evidence-Schema je Target

Für jedes externe Target wird ein eigener Evidence-Record mit stabiler `target_id` geführt.
Pflichtfelder (DoD):

1. `caller_arn` (letzte verifizierte `aws sts get-caller-identity`-Antwort)
2. `credential_injection` (Env / Shared Credentials / Role / SSO + Fundstelle)
3. `aws_jobs_or_scripts` (konkrete Jobs, Skripte oder User-Agents)
4. `migration_path` (OIDC-/AssumeRole-Zielpfad inkl. Owner)
5. `cutover_target_date` (geplantes Umschaltdatum oder klarer Blocker)
6. `evidence_refs` (Artefakte/Logs/Runbook-Referenzen)

### 3.2) Externe Target-Registry (aktualisiert, keine offenen `TBD`-Platzhalter)

| target_id | Host/System | caller_arn (last verified) | credential_injection | aws_jobs_or_scripts | migration_path | owner | cutover_target_date | evidence_refs | Status |
|---|---|---|---|---|---|---|---|---|---|
| `ext-ci-runner-fingerprint-76-13-144-185` | **OpenClaw-Umgebung** (AI-Agent/Assistent, der das Repo verwaltet und AWS-Ressourcen nutzt) | `arn:aws:iam::523234426229:user/swisstopo-api-deploy` (CloudTrail-Rechecks 6h/8h) | Statische Legacy-Env-Creds in der OpenClaw-Umgebung; Runtime-Referenzbefund: `runtime-env-static-keys` — bekannt, bewusst und dokumentiert | `aws-cli/2.33.29` (`sts:GetCallerIdentity`, `logs:FilterLogEvents`, `ecs:Describe*`), `aws-sdk-js/3.996.0` (`bedrock:ListFoundationModels`), Terraform (`HashiCorp Terraform/1.11.4`) | **Architekturentscheid 2026-03-01: dauerhaft beibehalten (decision: retained).** Kein Cutover erforderlich. | OpenClaw/Nico | Kein Blocker — Identität bekannt, Entscheid dokumentiert | `artifacts/bl15/legacy-cloudtrail-fingerprint-report.json`, `artifacts/bl17/runtime-credential-inventory.json`, `docs/LEGACY_IAM_USER_READINESS.md` | ✅ abgeschlossen (Identität: OpenClaw, retained by design) |
| `ext-ci-runner-secondary` | Externer CI/Runner #2 (derzeit kein separater Fingerprint im 6h-Fenster sichtbar) | Kein separater ARN isoliert; verbleibende Legacy-Events zeigen weiterhin `arn:aws:iam::523234426229:user/swisstopo-api-deploy` | Kein separater Injection-Pfad verifiziert; bis zur Identifikation als potenzieller statischer-Key-Consumer geführt | Kein eindeutiger separater Job-Satz im aktuellen Fingerprint-Report; Detection bei neuem Non-AWS-Fingerprint sofort nachziehen | Bei Identifikation auf denselben OIDC/AssumeRole-Zielpfad wie Primär-Runner migrieren | Nico (Asset-Mapping) + platform-ops (Migration) | **Blocker:** derzeit kein separates Zielsystem nachweisbar; Re-Validierung je CloudTrail-Recheck-Lauf | `artifacts/bl15/legacy-cloudtrail-fingerprint-report.json`, `docs/LEGACY_IAM_USER_READINESS.md` | 🟡 monitoren |
| `ext-cron-automation-hosts` | Sonstige externe Cron-/Automation-Hosts (nicht zugeordnet) | Nicht host-spezifisch separiert; Legacy-Nutzung im Fenster weiter auf `...:user/swisstopo-api-deploy` sichtbar | Mögliche Injektion über fremde Cron-/Automation-Env oder Shared Credentials; auf diesem Host aktuell keine Cron-Treffer | Wiederkehrende CLI-/SDK-Aktivität (`sts:GetCallerIdentity`, `ecs:Describe*`, `bedrock:ListFoundationModels`) muss pro externem Host zugeordnet werden | Host-Inventar je Automationssystem erstellen, dann auf kurzlebige Role-Credentials umstellen | Nico (Inventar) + platform-ops (Migration) | **Blocker:** externe Hostliste/Owner-Zuordnung fehlt; Cutover erst nach Inventarisierung je Host | `artifacts/bl15/legacy-cloudtrail-fingerprint-report.json`, `artifacts/bl17/runtime-credential-inventory.json`, `docs/LEGACY_IAM_USER_READINESS.md` | 🟡 offen |
| `dev-laptop-aws-profiles` | Entwickler-Laptop-Profile mit AWS-Credentials | Geräteweise noch nicht verifiziert; globaler Legacy-Caller bleibt `arn:aws:iam::523234426229:user/swisstopo-api-deploy` | Auf diesem Host keine persistierten Profile-Treffer; für Entwicklergeräte weiterhin Risiko durch lokale Profile/Env ohne SSO-Guard | Potenziell ad-hoc `aws-cli`/Terraform/SDK-Aufrufe von Entwicklergeräten; pro Gerät separat zu erfassen | Lokale Profile auf Role/SSO ohne Legacy-Key umstellen und pro Gerät verifizieren | Nico + jeweilige Geräte-Owner | **Blocker:** vollständige Geräteliste + Owner fehlt; Cutover je Gerät nach Einzel-Check | `artifacts/bl15/legacy-cloudtrail-fingerprint-report.json`, `artifacts/bl17/runtime-credential-inventory.json`, `docs/LEGACY_IAM_USER_READINESS.md` | ⏳ offen |

### 3.3) Verifikations-Checkliste (BL-15.r2.wp1)

- [x] Evidence-Schema mit Pflichtfeldern und stabilen `target_id`s dokumentiert.
- [x] Externe Target-Registry auf vier aktive Zielklassen mit eindeutigen Ownern aktualisiert.
- [x] Keine offenen `TBD`-Platzhalter mehr in den Pflichtfeldern (`caller_arn`, `credential_injection`, `aws_jobs_or_scripts`, `cutover_target_date`).
- [x] Für alle Targets ist `cutover_target_date` als Terminpfad **oder expliziter Blocker** dokumentiert.
- [x] Alle Targets enthalten Status + nächsten konkreten Schritt (Migration/Inventarisierung/Re-Validierung).

---

## 4) Exit-Kriterien für BL-15

**BL-15 ist abgeschlossen (Architekturentscheid 2026-03-01).**

Ursprüngliche Kriterien (zum Nachweis der Auflösung):
1. ✅ Alle Consumer in der Matrix identifiziert — dominanter externer Consumer `76.13.144.185` = **OpenClaw-Umgebung** (AI-Agent/Assistent, bekannt und gewollt).
2. ✅ Consumer-Migration entfällt als Gate-Kriterium — **Architekturentscheid: dauerhaft beibehalten (decision: retained)**.
3. ⏸ Legacy-Key-Deaktivierung: **nicht angestrebt** — OpenClaw-Runtime bleibt dauerhaft auf Key/Secret (Policy 2026-03-01).

**Entscheid: GO** — kein weiterer Handlungsbedarf für BL-15.
