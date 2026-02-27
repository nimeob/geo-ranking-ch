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

## 3) Inventarisierung externer Targets (offen)

Diese Liste muss für Decommission-Readiness vollständig gefüllt werden:

- [ ] Externer CI/Runner #1: `<hostname/system>`
- [ ] Externer CI/Runner #2: `<hostname/system>`
- [ ] Sonstige Cron-/Automation-Hosts: `<hostname/system>`
- [ ] Entwickler-Laptop-Profile mit AWS-Creds: `<owner/system>`

Pro Target erfassen:

1. `aws sts get-caller-identity` Ergebnis (ARN)
2. Wie werden Credentials injiziert? (Env/Shared Credentials/Role/SSO)
3. Welche Jobs/Skripte nutzen AWS dort?
4. Migrationspfad auf OIDC/AssumeRole
5. Geplantes Cutover-Datum

---

## 4) Exit-Kriterien für BL-15

BL-15 kann erst auf ✅, wenn:

1. alle Consumer in der Matrix identifiziert sind,
2. für jeden offenen Consumer ein valider Ersatzpfad existiert,
3. Legacy-Key kontrolliert deaktiviert wurde (24h Beobachtung) ohne Betriebsstörung.

Bis dahin: **No-Go** für finale Decommission.
