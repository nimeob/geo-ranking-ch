# Legacy IAM User Decommission Readiness (read-only)

> Scope: **BL-15** — nur Evidenz + Risikoanalyse + Decommission-Checkliste.
> Es wurden **keine** produktiven Rechte entzogen und **keine** Keys deaktiviert.

Stand: 2026-02-26 (UTC)

---

## 1) Verifizierte Ist-Lage (`swisstopo-api-deploy`)

| Item | Wert | Evidenz |
|---|---|---|
| IAM User | `arn:aws:iam::523234426229:user/swisstopo-api-deploy` | `aws sts get-caller-identity` |
| Access Keys | 1 aktiver Key (`AKIAXTUZTXV25VQQLQMX`) | `aws iam list-access-keys --user-name swisstopo-api-deploy` |
| Last Key Use | `2026-02-26T00:52:00Z` (`iam`, `us-east-1`) | `aws iam get-access-key-last-used --access-key-id ...` |
| Managed Policies | `IAMFullAccess`, `PowerUserAccess` | `aws iam list-attached-user-policies --user-name swisstopo-api-deploy` |
| Inline Policy | `swisstopo-dev-ecs-passrole` (nur ECS task/execution role) | `aws iam get-user-policy --user-name swisstopo-api-deploy --policy-name swisstopo-dev-ecs-passrole` |

### Service-Last-Access (IAM Access Advisor, Auszug)

Nur Services mit `LastAuthenticated != null`:

- `bedrock` — 2026-02-26T00:39:53Z
- `cloudformation` — 2026-02-25T21:15:36Z
- `cloudwatch` — 2026-02-26T00:52:04Z
- `dynamodb` — 2026-02-25T18:28:29Z
- `ec2` — 2026-02-25T23:20:08Z
- `ecr` — 2026-02-25T23:13:56Z
- `ecs` — 2026-02-25T23:57:46Z
- `events` — 2026-02-25T23:20:08Z
- `iam` — 2026-02-25T23:17:17Z

Kommando:

```bash
aws iam get-service-last-accessed-details \
  --job-id <job-id> \
  --query 'ServicesLastAccessed[?LastAuthenticated!=`null`].[ServiceNamespace,LastAuthenticated,LastAuthenticatedRegion]' \
  --output table
```

### CloudTrail-Hinweis zu aktivem Consumer

Aktuelle Events zeigen User-Agent `Terraform/1.11.4` auf diesem Principal (read-only Import/Plan-Läufe), z. B. `GetFunctionCodeSigningConfig` via `lambda.amazonaws.com`.

**Interpretation:** Der Legacy-User ist weiterhin in aktiver Nutzung (mindestens durch lokale/Runner-basierte Automationsläufe) und kann nicht „blind“ entfernt werden.

### Repo-scope Consumer-Inventar (read-only, 2026-02-26)

Zur reproduzierbaren Erfassung wurde ein read-only Audit-Script ergänzt:

```bash
./scripts/audit_legacy_aws_consumer_refs.sh
```

Verifizierte Befunde aus dem Lauf:

- Aktiver AWS-Caller im OpenClaw-Umfeld: `arn:aws:iam::523234426229:user/swisstopo-api-deploy` (Legacy-User weiterhin aktiv).
- Aktiver Deploy-Workflow `.github/workflows/deploy.yml` verwendet OIDC (`aws-actions/configure-aws-credentials@v4`) und enthält **keine** statischen AWS-Key-Referenzen.
- Potenzielle lokale/Runner-Consumer bleiben alle `scripts/*` mit direkten `aws`-CLI-Aufrufen (Setup- und Check-Skripte).
- Statische Key-Referenzen wurden nur im deaktivierten Template `scripts/ci-deploy-template.yml` gefunden (nicht produktiver Pfad).

Damit ist der Consumer-Blocker für BL-15 präziser eingegrenzt: **kein CI/CD-Deploy-Problem**, sondern primär lokale/Runner-basierte AWS-Ops-Pfade.

### Runtime-Consumer Baseline (host-level, read-only, 2026-02-26)

Zur risikoarmen Erfassung von Runtime-Quellen (Environment, Shell-Profile, Cron, Systemd, OpenClaw-Config) wurde ergänzt:

```bash
./scripts/audit_legacy_runtime_consumers.sh
```

Verifizierte Befunde aus dem Lauf:

- Aktiver AWS-Caller bleibt `arn:aws:iam::523234426229:user/swisstopo-api-deploy`.
- Im aktuellen Runtime-Environment sind `AWS_ACCESS_KEY_ID` und `AWS_SECRET_ACCESS_KEY` gesetzt (sanitisiert ausgegeben).
- Keine Legacy-/Key-Treffer in Shell-/Environment-Profilen (`~/.bashrc`, `~/.profile`, `/etc/environment`).
- Keine Treffer in prüfbaren System-Cron-/Systemd-Konfigurationen.
- Keine Legacy-/Key-Referenzen in OpenClaw-Konfig-Dateien (`openclaw.json`, `cron/jobs.json`).

Interpretation: Der aktive Legacy-Consumer ist aktuell **laufzeitgebunden** (Environment/Credential-Injection), nicht über persistierte Profile/Config auf diesem Host hinterlegt. Für „decommission-ready“ fehlt weiterhin die vollständige Inventarisierung weiterer externer Runner/Hosts.

### CloudTrail-Fingerprint Audit (read-only, 2026-02-26)

Zur schnelleren Attribution von aktiven Consumern wurde ergänzt:

```bash
LOOKBACK_HOURS=6 ./scripts/audit_legacy_cloudtrail_consumers.sh
```

Verifizierter Lauf (`Exit 10`):

- Deutlich aktive Legacy-Nutzung im 6h-Fenster (mehrere hundert Events; `LookupEvents` standardmäßig gefiltert)
- Dominanter Non-AWS-Fingerprint: `source_ip=76.13.144.185` (u. a. `aws-cli/2.33.29`, `aws-sdk-js/3.996.0`, Terraform Provider)
- Zusätzlich delegierte AWS-Service-Aktivität sichtbar (`source_ip=lambda.amazonaws.com`, KMS Events)

Interpretation: Die Legacy-Nutzung ist weiterhin aktiv und technisch klarer eingrenzbar (hauptsächlich ein wiederkehrender Host-Fingerprint plus AWS-Service-Delegation). Für Decommission fehlt weiterhin die vollständige Zuordnung aller externen Runner/Hosts gegen diese Fingerprints.

### Read-only Recheck (2026-02-26, 8h-Fenster)

Erneuter verifizierter Lauf:

- `./scripts/audit_legacy_aws_consumer_refs.sh` → Exit `10` (Caller weiter `...:user/swisstopo-api-deploy`)
- `./scripts/audit_legacy_runtime_consumers.sh` → Exit `30` (Legacy-Caller + gesetzte Runtime-Key-Variablen)
- `LOOKBACK_HOURS=8 ./scripts/audit_legacy_cloudtrail_consumers.sh` → Exit `10` (404 ausgewertete Events, dominante Fingerprints weiterhin `source_ip=76.13.144.185` und `source_ip=lambda.amazonaws.com`)
- `./scripts/check_bl17_oidc_assumerole_posture.sh` → Exit `30` (OIDC-Workflow-Marker korrekt, Runtime-Caller aber weiterhin Legacy-User)

Auffälligkeit im Recheck:

- Im 8h-CloudTrail-Fenster ist zusätzlich `sts:AssumeRole` über denselben Non-AWS-Fingerprint (`76.13.144.185`) sichtbar. Das zeigt bereits punktuelle AssumeRole-Nutzung, ändert aber den BL-15-Gesamtstatus nicht, weil der Primär-Caller im Runtime-Kontext weiter Legacy bleibt.

### Externe Consumer-Matrix (BL-15 Iteration, 2026-02-26)

Zur strukturierten Abarbeitung der offenen Consumer wurde ein dediziertes Tracking ergänzt:

- `docs/LEGACY_CONSUMER_INVENTORY.md`

Aktueller Kurzbefund daraus:

- GitHub Actions Deploy ist bereits OIDC-migriert.
- OpenClaw Runtime auf diesem Host nutzt weiterhin runtime-injizierte Legacy-Umgebungsvariablen.
- Externe Runner/Hosts sind noch nicht vollständig inventarisiert (Hauptblocker für Decommission-Freigabe).

---

## 2) Risiko-Einschätzung

**Risikolevel:** Hoch (Credentialed IAM User + breite AWS-Managed Policies).

Haupttreiber:
- Dauerhafte Access Keys statt kurzlebiger OIDC/STS-Credentials
- Sehr breite Rechte (`IAMFullAccess`, `PowerUserAccess`)
- Aktive Nutzung nachweisbar (CloudTrail + AccessKeyLastUsed)

---

## 3) Decommission-Readiness Checkliste (risikoarm)

### Phase A — Vorbereitung (ohne Impact)

- [x] Repo-scope Consumer-Inventar erstellt (Workflow/Script-Referenzen via `./scripts/audit_legacy_aws_consumer_refs.sh`)
- [ ] Runtime-Consumer vervollständigen (OpenClaw Runner, lokale Shell-Profile, Cronjobs außerhalb des Repos)
  - ✅ Host-Baseline via `./scripts/audit_legacy_runtime_consumers.sh` erhoben.
  - ✅ CloudTrail-Fingerprint-Audit via `LOOKBACK_HOURS=6 ./scripts/audit_legacy_cloudtrail_consumers.sh` erhoben (Recheck zusätzlich mit 8h-Fenster verifiziert).
  - ✅ Consumer-Matrix für offene Targets angelegt: `docs/LEGACY_CONSUMER_INVENTORY.md`.
  - ✅ BL-17 Posture-Quick-Check (`./scripts/check_bl17_oidc_assumerole_posture.sh`) als Cross-Check eingebunden (OIDC Workflows ok, Runtime-Caller weiterhin Legacy).
  - ⏳ Externe Runner/Hosts (außerhalb dieses OpenClaw-Hosts) noch offen.
- [ ] Für jeden Consumer Ersatzpfad definieren (bevorzugt OIDC/AssumeRole, sonst eng begrenzte Role)
  - 🟡 Für bekannte Consumer initial im Tracker hinterlegt; externe Targets noch offen.
- [ ] Read-only Smoke-Tests pro Ersatzpfad dokumentieren

### Phase B — Controlled Cutover

- [ ] Wartungsfenster festlegen (30–60 min)
- [ ] CloudTrail-Query für Fehlerüberwachung vorbereiten (`AccessDenied`, `InvalidClientTokenId`, `SignatureDoesNotMatch`)
- [ ] Access Key des Legacy-Users **deaktivieren** (nicht löschen)
- [ ] 24h Monitoring auf Auth-Fehler + Deploy/Ops-Funktion
- [ ] Bei Problemen: Key kurzfristig wieder aktivieren (Rollback)

### Phase C — Finalisierung

- [ ] Wenn 24h stabil: Access Key löschen
- [ ] Managed Policies vom User entfernen
- [ ] Inline Policy entfernen
- [ ] IAM User löschen
- [ ] Abschlussnachweis in `docs/AWS_INVENTORY.md` + `CHANGELOG.md`

---

## 4) Entscheidungs-Template (für Nico)

**Frage:** Können wir `swisstopo-api-deploy` jetzt dekommissionieren?

- **Go**, wenn:
  1) alle Consumer migriert sind,
  2) 24h ohne Legacy-Key stabil,
  3) CI/CD via OIDC weiterhin grün.

- **No-Go**, wenn:
  1) irgendein aktiver Consumer offen ist,
  2) Access-Denied-Fehler nach Deaktivierung auftreten,
  3) Notfall-Rollback nicht vorbereitet ist.

Empfohlene Default-Entscheidung aktuell: **No-Go (noch nicht bereit)**, da aktive Nutzung des Legacy-Users verifiziert ist.
