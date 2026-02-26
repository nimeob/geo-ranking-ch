# Legacy AWS Consumer Inventory (BL-15)

> Zweck: Vollständige, reproduzierbare Inventarisierung aller Consumer, die noch über den Legacy-IAM-User `swisstopo-api-deploy` laufen oder laufen könnten.
>
> Scope: read-only Tracking + Migrationsplanung (keine Abschaltung in diesem Dokument).

Stand: 2026-02-26 (UTC)

---

## 1) Verifizierte Basislage

Aus den read-only Audits:

- `./scripts/audit_legacy_aws_consumer_refs.sh` → Exit `10` (aktiver Caller = Legacy-User)
- `./scripts/audit_legacy_runtime_consumers.sh` → Exit `30` (aktiver Caller + Runtime-Env enthält AWS Key-Variablen)
- GitHub Deploy-Workflow (`.github/workflows/deploy.yml`) ist OIDC-only (kein statischer Key im aktiven CI/CD-Pfad)

Interpretation:

- CI/CD ist **nicht** der Hauptblocker.
- Hauptblocker ist aktuell ein **runtime-injizierter Legacy-Credential-Pfad** plus unbekannte externe Runner/Hosts.

---

## 2) Consumer-Matrix

| Consumer | Ort/Typ | Aktueller Auth-Pfad | Status | Zielpfad | Owner | Nächster Schritt |
|---|---|---|---|---|---|---|
| GitHub Actions Deploy (`deploy.yml`) | GitHub Hosted Runner | OIDC Role Assume (`swisstopo-dev-github-deploy-role`) | ✅ migriert | OIDC beibehalten | Repo | Periodische Drift-Prüfung |
| OpenClaw Runtime (dieser Host) | Host/Container Runtime | AWS Env-Creds (Legacy User als aktiver Caller) | 🟡 offen | OIDC-first via `workflow_dispatch`; Legacy nur Fallback | Nipa/Nico | Quelle der Credential-Injection identifizieren + entfernen |
| Externe Runner/Hosts (unbekannt) | außerhalb dieses Hosts | unbekannt | ⏳ offen | OIDC/AssumeRole je Consumer | Nico | Zielsysteme inventarisieren (Liste unten) |
| Lokale/Runner AWS-CLI Skripte (`scripts/*.sh`) | Repo-Artefakte | abhängig vom aufrufenden Runtime-Credential-Context | 🟡 offen | Aufruf über OIDC-Ausführungspfad oder eng begrenzte AssumeRole | Repo | Pro Script Ausführungspfad dokumentieren |

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
