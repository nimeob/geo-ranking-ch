# Legacy AWS Consumer Inventory (BL-15)

> Zweck: Vollständige, reproduzierbare Inventarisierung aller Consumer, die noch über den Legacy-IAM-User `swisstopo-api-deploy` laufen oder laufen könnten.
>
> Scope: read-only Tracking + Migrationsplanung (keine Abschaltung in diesem Dokument).

Stand: 2026-02-27 (UTC)

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
- Hauptblocker ist aktuell ein **runtime-injizierter Legacy-Credential-Pfad** plus unbekannte externe Runner/Hosts.

---

## 2) Consumer-Matrix

| Consumer | Ort/Typ | Aktueller Auth-Pfad | Status | Zielpfad | Owner | Nächster Schritt |
|---|---|---|---|---|---|---|
| GitHub Actions Deploy (`deploy.yml`) | GitHub Hosted Runner | OIDC Role Assume (`swisstopo-dev-github-deploy-role`) | ✅ migriert | OIDC beibehalten | Repo | Periodische Drift-Prüfung |
| OpenClaw Runtime (dieser Host) | Host/Container Runtime | AWS Env-Creds (Legacy User als aktiver Caller), punktuell `sts:AssumeRole` sichtbar | 🟡 offen | OIDC-first via `workflow_dispatch` + `openclaw-ops-role`; Legacy nur Fallback | Nipa/Nico | Credential-Injection-Quelle entfernen und AWS-Ops standardisiert über `scripts/aws_exec_via_openclaw_ops.sh` ausführen |
| Externe Runner/Hosts (unbekannt) | außerhalb dieses Hosts | unbekannt | ⏳ offen | OIDC/AssumeRole je Consumer | Nico | Zielsysteme inventarisieren (Liste unten) |
| Lokale/Runner AWS-CLI Skripte (`scripts/*.sh`) | Repo-Artefakte | abhängig vom aufrufenden Runtime-Credential-Context | 🟡 offen | Aufruf über OIDC-Ausführungspfad oder eng begrenzte AssumeRole | Repo | Pro Script Ausführungspfad dokumentieren |

### 2.1) Fingerprint-Hinweise aus CloudTrail (6h + 8h Rechecks)

- Dominanter Non-AWS-Fingerprint: `source_ip=76.13.144.185`
  - `aws-cli/2.33.29` (u. a. `sts:GetCallerIdentity`, `logs:FilterLogEvents`)
  - `aws-sdk-js/3.996.0` (u. a. `bedrock:ListFoundationModels`)
  - Terraform Provider (`HashiCorp Terraform/1.11.4`) auf diversen AWS-APIs
- 6h-Recheck (2026-02-27): 98 Raw-Events / 90 ausgewertete Events; Top-Aktivität weiter auf `76.13.144.185`.
- Zusätzliche AWS-Service-Delegation im 8h-Recheck (2026-02-26): `source_ip=lambda.amazonaws.com` (KMS-Zugriffe), plus sichtbare `sts:AssumeRole`-Events auf dem dominanten Fingerprint.

Bewertung:
- `76.13.144.185` ist aktuell primärer Kandidat für den aktiven Legacy-Consumer-Pfad.
- Die sichtbaren `AssumeRole`-Events sind ein positives Signal für BL-17, aber noch kein Nachweis für AssumeRole-first im Runtime-Default.
- Für BL-15 bleibt offen, ob daneben weitere externe Runner/Hosts in separaten Zeitfenstern Legacy-Zugriffe ausführen.

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

### 3.2) Externe Target-Registry (initial befüllt)

| target_id | Host/System | caller_arn (last verified) | credential_injection | aws_jobs_or_scripts | migration_path | cutover_target_date | evidence_refs | Status |
|---|---|---|---|---|---|---|---|---|
| `ext-ci-runner-fingerprint-76-13-144-185` | Externer Runner/Host (noch nicht namentlich zugeordnet) | `arn:aws:iam::523234426229:user/swisstopo-api-deploy` | Unbekannt; Kandidat ist runtime-injizierter Legacy-Key auf externem Host | `aws-cli/2.33.29` (`sts:GetCallerIdentity`, `logs:FilterLogEvents`), `aws-sdk-js/3.996.0` (`bedrock:ListFoundationModels`), `HashiCorp Terraform/1.11.4` | Host eindeutig zuordnen → Credential-Injection entfernen → Standardpfad auf `openclaw-ops-role`/OIDC umstellen | `TBD` (abhängig von Host-Identifikation) | `artifacts/bl15/legacy-cloudtrail-fingerprint-report.json`, `docs/LEGACY_IAM_USER_READINESS.md` | 🟡 in Analyse |
| `ext-ci-runner-secondary` | Externer CI/Runner #2 (unbestätigt) | `TBD` | `TBD` | `TBD` | Nach Identifikation gleiche OIDC/AssumeRole-Migration wie Primär-Runner | `TBD` | Fingerprint-Rechecks via `LOOKBACK_HOURS=6|8 ./scripts/audit_legacy_cloudtrail_consumers.sh` | ⏳ offen |
| `ext-cron-automation-hosts` | Sonstige externe Cron-/Automation-Hosts (unbestätigt) | `TBD` | `TBD` | `TBD` | Inventar je Host erstellen, dann auf kurzlebige Role-Credentials umstellen | `TBD` | Runtime-/CloudTrail-Quervergleich in `docs/LEGACY_IAM_USER_READINESS.md` | ⏳ offen |
| `dev-laptop-aws-profiles` | Entwickler-Laptop-Profile mit AWS-Credentials | `TBD` | `TBD` (Profil/SSO/Env je Gerät erfassen) | `TBD` | Lokale Profile auf Role/SSO ohne Legacy-Key umstellen, danach Key-Nutzung verifizieren | `TBD` | Konsolidierte Target-Liste in diesem Abschnitt + BL-15-Go/No-Go-Checkliste | ⏳ offen |

### 3.3) Offene Verifikations-Checkliste

- [x] Evidence-Schema mit Pflichtfeldern und stabilen `target_id`s dokumentiert.
- [x] Initiale externe Target-Registry mit vier prüfbaren Records angelegt.
- [ ] Für alle Targets `caller_arn` per direktem Nachweis (`aws sts get-caller-identity`) ergänzt.
- [ ] Für alle Targets `credential_injection` und konkrete Job-/Script-Bezüge vervollständigt.
- [ ] Für alle Targets `cutover_target_date` mit Termin oder explizitem Blocker gesetzt.

---

## 4) Exit-Kriterien für BL-15

BL-15 kann erst auf ✅, wenn:

1. alle Consumer in der Matrix identifiziert sind,
2. für jeden offenen Consumer ein valider Ersatzpfad existiert,
3. Legacy-Key kontrolliert deaktiviert wurde (24h Beobachtung) ohne Betriebsstörung.

Bis dahin: **No-Go** für finale Decommission.
