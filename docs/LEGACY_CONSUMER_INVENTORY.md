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

### 3.2) Externe Target-Registry (aktualisiert, keine offenen `TBD`-Platzhalter)

| target_id | Host/System | caller_arn (last verified) | credential_injection | aws_jobs_or_scripts | migration_path | owner | cutover_target_date | evidence_refs | Status |
|---|---|---|---|---|---|---|---|---|---|
| `ext-ci-runner-fingerprint-76-13-144-185` | Externer Runner/Host (noch nicht namentlich zugeordnet) | `arn:aws:iam::523234426229:user/swisstopo-api-deploy` (CloudTrail-Rechecks 6h/8h) | Wahrscheinlich statische Legacy-Env-Creds auf externem Host; Runtime-Referenzbefund: `runtime-env-static-keys` | `aws-cli/2.33.29` (`sts:GetCallerIdentity`, `logs:FilterLogEvents`, `ecs:Describe*`), `aws-sdk-js/3.996.0` (`bedrock:ListFoundationModels`), Terraform (`HashiCorp Terraform/1.11.4`) | Host eindeutig zuordnen → Credential-Injection entfernen → Standardpfad auf `openclaw-ops-role`/OIDC umstellen | Nico (Asset-Mapping) + platform-ops (Migration) | **Blocker:** Host-Mapping für `source_ip=76.13.144.185` fehlt; Cutover-Termin direkt nach Zuordnung setzen | `artifacts/bl15/legacy-cloudtrail-fingerprint-report.json`, `artifacts/bl17/runtime-credential-inventory.json`, `docs/LEGACY_IAM_USER_READINESS.md` | 🟡 in Analyse |
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

BL-15 kann erst auf ✅, wenn:

1. alle Consumer in der Matrix identifiziert sind,
2. für jeden offenen Consumer ein valider Ersatzpfad existiert,
3. Legacy-Key kontrolliert deaktiviert wurde (24h Beobachtung) ohne Betriebsstörung.

Bis dahin: **No-Go** für finale Decommission.
