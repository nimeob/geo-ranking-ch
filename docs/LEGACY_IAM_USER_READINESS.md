# Legacy IAM User Decommission Readiness (read-only)

> Scope: **BL-15** — nur Evidenz + Risikoanalyse + Decommission-Checkliste.
> Es wurden **keine** produktiven Rechte entzogen und **keine** Keys deaktiviert.

Stand: 2026-03-01 (UTC)

## Policy-Update (2026-03-01)
- **OpenClaw Runtime bleibt auf Access Key + Secret** (kein Runtime-OIDC-Zwang).
- **OIDC bleibt ausschließlich für GitHub-Deploys**.
- Frühere BL-17-Passagen zu „AssumeRole-first als Runtime-Default" sind historisch und für BL-15.r2 nicht mehr als Muss zu werten.

---

## Legacy-Fallback-Log (BL-17.wp2)

Standardformat für Legacy-Notfallnutzung:
- [`docs/LEGACY_FALLBACK_LOG_TEMPLATE.md`](LEGACY_FALLBACK_LOG_TEMPLATE.md)

### Fallback-Log Entries

Derzeit keine neu protokollierten Incident-Fallbacks in diesem Dokument.
Wenn ein Legacy-Fallback notwendig ist, Eintrag im obigen Template-Format ergänzen (Markdown + optional JSON-Snippet).

#### Synthetisches Vollbeispiel (BL-17.wp8, read-only)

```markdown
### Legacy Fallback Entry — legacy-fallback-2026-02-27-001

- timestamp_utc: 2026-02-27T00:18:00Z
- actor: openclaw-host
- reason: AssumeRole-Primärpfad lieferte im Incident-Fenster wiederholt `ThrottlingException` bei zeitkritischem Read-only-Diagnoselauf
- scope: aws cloudwatch describe-alarms --region eu-central-1 --max-items 5
- started_utc: 2026-02-27T00:16:00Z
- ended_utc: 2026-02-27T00:19:00Z
- duration_minutes: 3
- outcome: success
- rollback_needed: no
- evidence:
  - cloudtrail_window_utc: 2026-02-27T00:10:00Z..2026-02-27T00:30:00Z
  - refs:
    - artifacts/legacy-fallback/2026-02-27-001.log
    - artifacts/legacy-fallback/2026-02-27-001-cloudtrail.txt
    - artifacts/legacy-fallback/2026-02-27-001-runtime-inventory.json
    - artifacts/legacy-fallback/2026-02-27-001-posture.json
- follow_up:
  - issue: #150
  - action: Break-glass-Runbook schärfen (Triggerkriterien + Evidenz-Checkliste + Rückweg in den regulären Runtime-Betrieb)
```

Hinweis: Dieses Beispiel ist **synthetisch** und dient nur als vollständige Referenz für die Pflichtfelder und Evidenzpfade.

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

### Runtime-Credential-Injection-Inventar (BL-17.wp5, read-only)

Für die strukturierte Erfassung von Injection-Pfaden inkl. Migrationsschritten:

```bash
./scripts/inventory_bl17_runtime_credential_paths.py \
  --output-json artifacts/bl17/runtime-credential-injection-inventory.json
```

- Der Report liefert pro Befund `effect`, `migration_next_step` und `owner`.
- Exit `10` signalisiert erkannte riskante Injection-Pfade (Legacy/Key-Injection).
- Detaildoku: `docs/BL17_RUNTIME_CREDENTIAL_INJECTION_INVENTORY.md`.

### CloudTrail-Fingerprint Audit (read-only, 2026-02-26)

Zur schnelleren Attribution von aktiven Consumern wurde ergänzt:

```bash
LOOKBACK_HOURS=6 \
FINGERPRINT_REPORT_JSON=artifacts/bl15/legacy-cloudtrail-fingerprint-report.json \
./scripts/audit_legacy_cloudtrail_consumers.sh
```

Der Lauf schreibt einen strukturierten JSON-Report (standardmäßig `artifacts/bl15/legacy-cloudtrail-fingerprint-report.json`) mit:
- Zeitfenster (`window_utc.start/end`, `lookback_hours`)
- Event-Counts (`events_raw`, `events_analyzed`, `lookup_events_filtered`)
- Top-Fingerprints (`source_ip`, `user_agent`, Event-Sets, letzter Event-Zeitpunkt)
- Optional erweiterten Fingerprint-Dimensionen via `FINGERPRINT_INCLUDE_REGION=1` und/oder `FINGERPRINT_INCLUDE_ACCOUNT=1`
- Letzten 10 Events als read-only Evidenz ohne Secret-Werte

Die Normalisierung/Aggregation der Fingerprints ist in `src/legacy_consumer_fingerprint.py` gekapselt und wird vom Audit-Skript wiederverwendet.

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

### Read-only Recheck (2026-02-26, 6h-Fenster, Worker-Lauf)

Erneuter verifizierter Lauf im Worker-Kontext:

- `./scripts/audit_legacy_aws_consumer_refs.sh` → Exit `10` (Caller weiterhin `arn:aws:iam::523234426229:user/swisstopo-api-deploy`)
- `./scripts/audit_legacy_runtime_consumers.sh` → Exit `30` (Legacy-Caller + gesetzte Runtime-Key-Variablen)
- `LOOKBACK_HOURS=6 ./scripts/audit_legacy_cloudtrail_consumers.sh` → Exit `10` (10 ausgewertete Legacy-Events, dominanter Fingerprint weiterhin `source_ip=76.13.144.185`)
- `./scripts/check_bl17_oidc_assumerole_posture.sh` → Exit `30` (OIDC-Workflow-Marker korrekt, Runtime-Caller aber weiterhin Legacy)

Zusätzliche Härtung im Zuge dieses Laufs:

- `scripts/audit_legacy_aws_consumer_refs.sh` nutzt für Repo-Scans jetzt primär `git grep` mit Excludes für `artifacts/`, `.venv/` und `.terraform/`, damit generierte Audit-Logs keine Folge-Scans verfälschen.

Interpretation: OIDC in CI/CD ist intakt; aktive Runtime-Key-Nutzung ist gemäß Policy zulässig. BL-15-Readiness hängt damit primär an sauberer Dokumentation, Governance und externer Consumer-Zuordnung (nicht an einer Runtime-OIDC-Migration).

### Read-only Recheck (2026-02-27, 6h-Fenster, Worker-A)

Erneuter verifizierter Lauf im Worker-A-Kontext:

- `./scripts/audit_legacy_aws_consumer_refs.sh` → Exit `10` (Caller weiterhin `arn:aws:iam::523234426229:user/swisstopo-api-deploy`)
- `./scripts/audit_legacy_runtime_consumers.sh` → Exit `30` (Legacy-Caller + Runtime-Mode `long-lived-static` mit gesetzten AWS-Key-Variablen)
- `LOOKBACK_HOURS=6 ./scripts/audit_legacy_cloudtrail_consumers.sh` → Exit `10` (98 Raw-Events / 90 ausgewertete Legacy-Events; dominanter Fingerprint weiterhin `source_ip=76.13.144.185`)
- `./scripts/check_bl17_oidc_assumerole_posture.sh` → Exit `30` (OIDC-Workflow-Marker weiterhin korrekt, Runtime-Caller aber Legacy)

Auffälligkeiten im 6h-Recheck:

- CloudTrail zeigt weiterhin wiederkehrende `sts:GetCallerIdentity`-Aktivität auf dem Non-AWS-Fingerprint `76.13.144.185`.
- Zusätzlich sind im selben Fenster Legacy-Events für `logs:FilterLogEvents` (aws-cli) und `bedrock:ListFoundationModels` (aws-sdk-js) sichtbar.

Interpretation: Trotz stabiler OIDC-Marker im Workflow-Pfad bleibt die Runtime-Legacy-Nutzung aktiv. BL-15 bleibt damit auf **No-Go** für eine finale Decommission.

### Read-only Recheck (2026-02-26, BL-17.wp6 AssumeRole-Default-Pfad)

Neuer Runtime-Startpfad:

```bash
./scripts/openclaw_runtime_assumerole_exec.sh <kommando>
```

Verifizierter Nachweislauf im neuen Default-Pfad:

- `./scripts/openclaw_runtime_assumerole_exec.sh ./scripts/inventory_bl17_runtime_credential_paths.py --output-json artifacts/bl17/runtime-credential-injection-inventory-after-assumerole-default.json` → Exit `0`
  - Befund `runtime-env-static-keys`: **detected=false**
  - Caller: `assumed-role/openclaw-ops-role/...`
- `./scripts/openclaw_runtime_assumerole_exec.sh ./scripts/audit_legacy_runtime_consumers.sh` → Exit `0`
- `./scripts/openclaw_runtime_assumerole_exec.sh ./scripts/check_bl17_oidc_assumerole_posture.sh --report-json artifacts/bl17/posture-after-assumerole-default.json` → Exit `0`

Interpretation: Der neue Runtime-Default eliminiert den statischen Env-Key-Befund im aktiven Prozesskontext (temporäre STS-Session-Credentials statt Legacy-User-Key als Startzustand).

### Read-only Recheck (2026-03-01, BL-15.r2.wp2 Runtime-Injection)

Vergleichslauf zwischen ambientem Runtime-Kontext und AssumeRole-first-Kapselung:

- Ambient Runtime:
  - `./scripts/audit_legacy_runtime_consumers.sh` → Exit `30` (`legacy caller` + `credential_mode=long-lived-static`)
  - `python3 scripts/check_bl17_oidc_only_guard.py --output-json artifacts/bl17/oidc-only-guard-20260301-default.json --posture-report-json artifacts/bl17/posture-report-20260301-default.json --runtime-report-json artifacts/bl17/runtime-credential-inventory-20260301-default.json --cloudtrail-log artifacts/bl17/legacy-cloudtrail-audit-20260301-default.log --cloudtrail-lookback-hours 6` → Exit `10`
- AssumeRole-first kapselter Runtime-Pfad:
  - `./scripts/openclaw_runtime_assumerole_exec.sh ./scripts/audit_legacy_runtime_consumers.sh` → Exit `0`
  - `./scripts/openclaw_runtime_assumerole_exec.sh ./scripts/check_bl17_oidc_assumerole_posture.sh --report-json artifacts/bl17/posture-report-20260301-assumerole.json` → Exit `0`
  - `./scripts/openclaw_runtime_assumerole_exec.sh python3 scripts/inventory_bl17_runtime_credential_paths.py --output-json artifacts/bl17/runtime-credential-inventory-20260301-assumerole.json` → Exit `0`
  - `./scripts/openclaw_runtime_assumerole_exec.sh python3 scripts/check_bl17_oidc_only_guard.py --assume-role-first --output-json artifacts/bl17/oidc-only-guard-20260301-assumerole.json --posture-report-json artifacts/bl17/posture-report-20260301-assumerole.json --runtime-report-json artifacts/bl17/runtime-credential-inventory-20260301-assumerole.json --cloudtrail-log artifacts/bl17/legacy-cloudtrail-audit-20260301-assumerole.log --cloudtrail-lookback-hours 6` → Exit `10` (fail **nur** wegen weiterhin vorhandener Legacy-CloudTrail-Events).

Interpretation:
- Runtime-Legacy-Injection ist im ambienten Prozesskontext weiterhin ein Risiko.
- Der gekapselte AssumeRole-first Pfad ist reproduzierbar sauber (`posture=ok`, `runtime_inventory=ok`) und stellt den kontrollierten Standardpfad dar.
- Offene Restarbeit liegt primär in externer Legacy-Nutzung laut CloudTrail (nicht im lokalen Wrapper-Pfad).

### Source-Attribution-Update (2026-03-01, BL-15.r2.wp2.a / #572)

Neue forensische Runtime-Evidence wurde ergänzt über:

- `./scripts/inventory_bl17_runtime_credential_paths.py --output-json artifacts/bl17/runtime-credential-injection-inventory-20260301T114607Z-ambient.json` → Exit `10`

Relevante neue Detection-IDs im Report:

- `runtime-env-inheritance-process-chain` (detected=`true`): Prozesskette zeigt statische Key-Vererbung bis in OpenClaw-Parent-Prozesse (`openclaw-gateway` → `openclaw` → `node server.mjs`, redacted).
- `runtime-startpath-env-passthrough` (detected=`true`): Wrapper-Hinweise auf Env-Passthrough in bekannten Startpfaden (`/entrypoint.sh`, `/hostinger/server.mjs`).

Interpretation:
- Die Ambient-Injection ist nicht nur ein Shell-Einzelfall, sondern folgt der Prozess-/Startpfad-Vererbung des laufenden OpenClaw-Stacks.
- Damit ist die Quelle für wp2 technisch attribuiert; nächster Schritt ist die persistente Startpfad-Migration in #573.

Temporäre Ausnahme-Klassifikation (wp2, evidenzpflichtig):

| Feld | Wert |
|---|---|
| exception_id | `bl15-r2-wp2-runtime-legacy-env-static-keys` |
| Scope | Ambient OpenClaw-Runtime mit statischen AWS-Env-Keys außerhalb des AssumeRole-Wrappers |
| Control/Mitigation | AWS-relevante Checks/Ops nur über `./scripts/openclaw_runtime_assumerole_exec.sh` bzw. Guard-Mode `--assume-role-first` ausführen |
| Owner | Nico + platform-ops |
| Sunset | 2026-03-15 (bis dahin Quelle der Ambient-Injection identifizieren und entfernen) |
| Follow-up | #570 |
| Evidenz | `artifacts/bl15/runtime-audit-20260301-default.log`, `artifacts/bl15/runtime-audit-20260301-assumerole.log`, `artifacts/bl17/oidc-only-guard-20260301-default.json`, `artifacts/bl17/oidc-only-guard-20260301-assumerole.json` |

### Externe Consumer-Matrix (BL-15 Iteration, aktualisiert 2026-03-01)

Zur strukturierten Abarbeitung der offenen Consumer wurde ein dediziertes Tracking ergänzt:

- `docs/LEGACY_CONSUMER_INVENTORY.md`
  - Abschnitt `3.1`: verbindliches Evidence-Schema pro Target (`caller_arn`, `credential_injection`, `aws_jobs_or_scripts`, `migration_path`, `cutover_target_date`, `evidence_refs`)
  - Abschnitt `3.2`: aktualisierte Target-Registry mit stabilen `target_id`s (Pflichtfelder ohne offene `TBD`-Platzhalter, inkl. Owner/Cutover-Blocker)

Aktueller Kurzbefund daraus:

- GitHub Actions Deploy ist bereits OIDC-migriert.
- OpenClaw Runtime auf diesem Host nutzt weiterhin runtime-injizierte Legacy-Umgebungsvariablen.
- Externe Targets sind strukturiert erfasst und ohne offene `TBD`-Platzhalter gepflegt; mehrere Targets stehen jedoch weiterhin auf explizitem Blockerstatus (fehlendes Host-/Owner-Mapping für finalen Cutover).

### Standardisiertes Evidence-Bundle exportieren (BL-15.wp4)

Für externe Reviews kann aus vorhandener Read-only-Evidenz ein versioniertes Bundle erzeugt werden:

```bash
./scripts/export_bl15_readiness_bundle.py
```

Standardziel: `reports/bl15_readiness/<UTC-Timestamp>/`

Bundle-Inhalt (Minimum):

- `evidence/fingerprint/legacy-cloudtrail-fingerprint-report.json`
- `consumer_targets_hint.md` (extrahierte `target_id`s aus der Consumer-Matrix)
- `inventory.json` (Manifest + SHA256-Checksums)
- `README.md` (Kurzinterpretation je Artefakt)

Optional können zusätzliche Artefakte über `--optional-glob` eingebunden werden.

### Readiness-Collector (BL-15.wp6)

Für einen kombinierten Lauf (Repo-/Runtime-/CloudTrail-Audit + strukturierte JSON/MD-Nachweise + optionales Bundle) steht ein dedizierter Collector bereit:

```bash
./scripts/collect_bl15_readiness_evidence.py
```

Standardartefakte je Lauf:

- `artifacts/bl15/readiness-collector-<timestamp>/collector_report.json`
- `artifacts/bl15/readiness-collector-<timestamp>/collector_report.md`
- `artifacts/bl15/readiness-collector-<timestamp>/logs/*.log`

Deterministische Exit-Codes des Collectors:

- `0` = Lauf erfolgreich, keine Findings
- `10` = Lauf erfolgreich, Findings vorhanden (z. B. Legacy-Caller weiterhin aktiv)
- `20` = externer Blocker/Ausführungsfehler (z. B. CloudTrail-Berechtigung oder fehlendes Script)

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
  - ✅ Externe Target-Registry auf Evidence-Schema konkretisiert (`docs/LEGACY_CONSUMER_INVENTORY.md`, Abschnitt 3.1/3.2; BL-15.wp3).
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

## 4) GO/NO-GO Decision-Matrix (BL-15.wp5)

### 4.1 Harte Gates (entscheidungsrelevant)

| Gate | Muss erfüllt sein für **GO** | Primäre Evidenz | Status 2026-02-27 | Bewertung |
|---|---|---|---|---|
| G1: Runtime-Policy dokumentiert | OpenClaw Runtime-Key/Secret-Nutzung ist explizit freigegeben, begründet und konsistent dokumentiert | `docs/BACKLOG.md`, BL-15.r2-Issues, dieses Dokument | Policy-Update gesetzt, Feinsync läuft | 🟡 |
| G2: Deploy-Pfad OIDC-konform | Aktive Deploy-Workflows nutzen OIDC ohne statische Keys | `.github/workflows/deploy.yml`, `./scripts/check_bl17_oidc_assumerole_posture.sh` | OIDC-Deploy verifiziert | 🟢 |
| G3: Externe Consumer vollständig inventarisiert | Für jedes Target: `caller_arn`, Injection-Pfad, Owner, Cutover-/Review-Datum, Evidenz | `docs/LEGACY_CONSUMER_INVENTORY.md` | Pflichtfelder vollständig befüllt, aber mehrere Targets mit offenen Identifikations-/Cutover-Blockern | 🔴 |
| G4: Monitoring + Rollback vorbereitet | Governance/Monitoring + dokumentierter Reaktivierungsweg vorhanden | Abschnitt 3 (Phase B), Fallback-Template | Basis vorhanden, Dry-Run/Abnahme offen | 🟡 |
| G5: Security-Hygiene Runtime-Key-Pfad | Rotation/Least-Privilege/Audit für Runtime-Key-Pfad nachvollziehbar und überprüfbar | IAM-/Audit-Evidenz + Runbooks | Teilweise nachgewiesen, Abschluss-Sync offen | 🟡 |

### 4.2 Entscheidungslogik

- **GO**: Alle harten Gates (G1–G5) sind grün.
- **GO with timebox**: Kein rotes Gate; maximal 2 gelbe Gates mit klarer Restmaßnahme, Owner und fester Frist (≤14 Tage).
- **NO-GO**: Mindestens ein rotes Gate oder fehlender Sign-off eines Pflicht-Owners.

### 4.3 Aktueller Entscheid (Snapshot)

**Aktuell: NO-GO.**

Begründung (kurz):
- Externe Consumer-Inventarisierung ist noch nicht vollständig (G3 rot).
- Runtime-Key/Secret-Policy ist gesetzt, aber Governance-/Dokumentationssync ist noch nicht final (G1/G5 gelb).

### 4.4 Verlinkte BL-15-Evidenzartefakte

- Consumer-Inventar + Target-Registry: `docs/LEGACY_CONSUMER_INVENTORY.md`
- CloudTrail-Fingerprint-Report: `artifacts/bl15/legacy-cloudtrail-fingerprint-report.json`
- Runtime-Credential-Injection-Inventar: `artifacts/bl17/runtime-credential-injection-inventory.json`
- AssumeRole-Default-Nachweis (Host-Lauf): `artifacts/bl17/runtime-credential-injection-inventory-after-assumerole-default.json`
- Standardisiertes Review-Bundle: `reports/bl15_readiness/<timestamp>/`

---

## 5) Sign-off-Template + synthetisches Beispiel

### 5.1 Sign-off-Template (auszufüllen pro Entscheidung)

| Feld | Inhalt |
|---|---|
| Decision-ID | `bl15-decommission-<YYYYMMDD>-<nn>` |
| Entscheidung | `GO` \| `GO with timebox` \| `NO-GO` |
| Scope | z. B. `swisstopo-api-deploy Legacy IAM User` |
| Bewertungszeitpunkt (UTC) | `<timestamp>` |
| Gate-Status G1..G5 | `G1=...; G2=...; G3=...; G4=...; G5=...` |
| Timebox-Ende (falls relevant) | `<YYYY-MM-DD>` oder `n/a` |
| Pflicht-Evidenz | Links auf BL-15-Artefakte |
| Risiken (Top 3) | Stichpunkte mit Gegenmaßnahme |
| Freigaben | Security Owner, Platform Owner, Service Owner |
| Next Review | Datum/Zeit oder Trigger |

### 5.2 Synthetisch ausgefülltes Beispiel

| Feld | Beispielwert |
|---|---|
| Decision-ID | `bl15-decommission-20260227-01` |
| Entscheidung | `NO-GO` |
| Scope | `swisstopo-api-deploy Legacy IAM User` |
| Bewertungszeitpunkt (UTC) | `2026-02-27T04:25:00Z` |
| Gate-Status G1..G5 | `G1=🔴; G2=🟡; G3=🔴; G4=🟡; G5=🔴` |
| Timebox-Ende | `n/a` |
| Pflicht-Evidenz | `docs/LEGACY_CONSUMER_INVENTORY.md`, `artifacts/bl15/legacy-cloudtrail-fingerprint-report.json`, `artifacts/bl17/runtime-credential-injection-inventory-after-assumerole-default.json` |
| Risiken (Top 3) | `1) Externer Runtime-Consumer unbekannt; 2) Fehlender 24h-Cutover-Beleg; 3) Incident-Rollback ohne Dry-Run` |
| Freigaben | `Security: pending`, `Platform: pending`, `Service: pending` |
| Next Review | `nach Abschluss externer Target-Verifikation + geplantem Cutover-Dry-Run` |

---

## 6) Vorgeschlagener Entscheidungsablauf (max. 5 Schritte)

1. **Evidenz aktualisieren** (Runtime-, CloudTrail- und Consumer-Inventar-Checks aus Abschnitt 1/3).
2. **Gates G1–G5 bewerten** und Ampelstatus dokumentieren.
3. **Entscheidung klassifizieren** (`GO`, `GO with timebox`, `NO-GO`) nach Abschnitt 4.2.
4. **Sign-off einholen** (Security/Platform/Service) mit Template aus Abschnitt 5.1.
5. **Nächsten operativen Schritt terminieren** (Cutover starten oder konkrete Blocker-Maßnahmen mit Termin/Owner).
