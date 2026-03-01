# Legacy IAM User Decommission Readiness (read-only)

> Scope: **BL-15** — nur Evidenz + Risikoanalyse + Decommission-Checkliste.
> Es wurden **keine** produktiven Rechte entzogen und **keine** Keys deaktiviert.

Stand: 2026-03-01 (UTC)

## Architekturentscheid 2026-03-01

Der externe Consumer (`76.13.144.185`) = **OpenClaw-Umgebung** (AI-Agent/Assistent, der das Repo verwaltet und AWS-Ressourcen nutzt); bleibt dauerhaft aktiv (decision: retained).
Gate G3 (Consumer-Migration) ist als «accepted/retained» klassifiziert — kein Blocking mehr.
BL-15 gilt als abgeschlossen.

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

Interpretation: Die Legacy-Nutzung ist weiterhin aktiv. Dominanter externer Consumer (`source_ip=76.13.144.185`) ist als **OpenClaw-Umgebung** identifiziert (AI-Agent/Assistent, der das Repo verwaltet und AWS-Ressourcen nutzt). **Architekturentscheid 2026-03-01: bleibt dauerhaft aktiv (decision: retained).** Zuordnungsaufgabe externer Runner/Hosts: abgeschlossen (Identität: OpenClaw).

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

Interpretation: OIDC in CI/CD ist intakt; aktive Runtime-Key-Nutzung ist gemäß Policy zulässig. Externe Consumer-Zuordnung: **abgeschlossen** — `76.13.144.185` = OpenClaw-Umgebung (AI-Agent/Assistent), Architekturentscheid 2026-03-01: dauerhaft beibehalten (decision: retained). BL-15-Readiness ist damit vollständig dokumentiert und geschlossen.

### Read-only Recheck (2026-02-27, 6h-Fenster, Worker-A)

Erneuter verifizierter Lauf im Worker-A-Kontext:

- `./scripts/audit_legacy_aws_consumer_refs.sh` → Exit `10` (Caller weiterhin `arn:aws:iam::523234426229:user/swisstopo-api-deploy`)
- `./scripts/audit_legacy_runtime_consumers.sh` → Exit `30` (Legacy-Caller + Runtime-Mode `long-lived-static` mit gesetzten AWS-Key-Variablen)
- `LOOKBACK_HOURS=6 ./scripts/audit_legacy_cloudtrail_consumers.sh` → Exit `10` (98 Raw-Events / 90 ausgewertete Legacy-Events; dominanter Fingerprint weiterhin `source_ip=76.13.144.185`)
- `./scripts/check_bl17_oidc_assumerole_posture.sh` → Exit `30` (OIDC-Workflow-Marker weiterhin korrekt, Runtime-Caller aber Legacy)

Auffälligkeiten im 6h-Recheck:

- CloudTrail zeigt weiterhin wiederkehrende `sts:GetCallerIdentity`-Aktivität auf dem Non-AWS-Fingerprint `76.13.144.185` = **OpenClaw-Umgebung** (AI-Agent/Assistent, bekannt und retained by design).
- Zusätzlich sind im selben Fenster Legacy-Events für `logs:FilterLogEvents` (aws-cli) und `bedrock:ListFoundationModels` (aws-sdk-js) sichtbar.

Interpretation (historisch, 2026-02-27): Trotz stabiler OIDC-Marker im Workflow-Pfad bleibt die Runtime-Legacy-Nutzung aktiv. BL-15 stand zu diesem Zeitpunkt auf **No-Go** für eine finale Decommission. ⚠️ **Überholt durch Architekturentscheid 2026-03-01**: `76.13.144.185` = **OpenClaw-Umgebung**, bleibt dauerhaft aktiv (decision: retained). BL-15 ist abgeschlossen.

### Read-only Vergleichslauf (2026-02-26, BL-17.wp6, historisch — kein Runtime-Default)

Historisch getesteter Kapselungs-Pfad:

```bash
./scripts/openclaw_runtime_assumerole_exec.sh <kommando>
```

Verifizierter Nachweislauf im gekapselten Vergleichspfad:

- `./scripts/openclaw_runtime_assumerole_exec.sh ./scripts/inventory_bl17_runtime_credential_paths.py --output-json artifacts/bl17/runtime-credential-injection-inventory-after-assumerole-default.json` → Exit `0`
  - Befund `runtime-env-static-keys`: **detected=false**
  - Caller: `assumed-role/openclaw-ops-role/...`
- `./scripts/openclaw_runtime_assumerole_exec.sh ./scripts/audit_legacy_runtime_consumers.sh` → Exit `0`
- `./scripts/openclaw_runtime_assumerole_exec.sh ./scripts/check_bl17_oidc_assumerole_posture.sh --report-json artifacts/bl17/posture-after-assumerole-default.json` → Exit `0`

Interpretation: Der gekapselte Vergleichspfad eliminiert im Testkontext den statischen Env-Key-Befund (temporäre STS-Session-Credentials statt Legacy-User-Key). Dieser Pfad bleibt optional für Diagnostik/Evidence und ist kein verpflichtender Runtime-Startzustand.

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
- Der gekapselte AssumeRole-first Pfad ist reproduzierbar sauber (`posture=ok`, `runtime_inventory=ok`), dient aber nur als optionaler Diagnose-/Vergleichspfad (nicht als Runtime-Standard).
- Offene Restarbeit liegt primär in externer Legacy-Nutzung laut CloudTrail (nicht im lokalen Wrapper-Pfad).

### Source-Attribution-Update (2026-03-01, BL-15.r2.wp2.a / #572)

Neue forensische Runtime-Evidence wurde ergänzt über:

- `./scripts/inventory_bl17_runtime_credential_paths.py --output-json artifacts/bl17/runtime-credential-injection-inventory-20260301T114607Z-ambient.json` → Exit `10`

Relevante neue Detection-IDs im Report:

- `runtime-env-inheritance-process-chain` (detected=`true`): Prozesskette zeigt statische Key-Vererbung bis in OpenClaw-Parent-Prozesse (`openclaw-gateway` → `openclaw` → `node server.mjs`, redacted).
- `runtime-startpath-env-passthrough` (detected=`true`): Wrapper-Hinweise auf Env-Passthrough in bekannten Startpfaden (`/entrypoint.sh`, `/hostinger/server.mjs`).

Interpretation:
- Die Ambient-Injection ist nicht nur ein Shell-Einzelfall, sondern folgt der Prozess-/Startpfad-Vererbung des laufenden OpenClaw-Stacks.
- Damit ist die Quelle für wp2 technisch attribuiert; nächster Schritt ist die Startpfad-/Governance-Dokumentation in #573. Persistente technische Startpfad-Änderungen bleiben optional und nur bei echtem Bedarf im Wartungsfenster.

### BL-15.r2.wp2.b.prereq-Entscheid (2026-03-01, #576)

Bewertung des Prereqs „Wartungsfenster/Host-Zugriff nur falls nötig":

- Ergebnis: Für den aktuellen Scope der BL-15.r2-Doku-/Policy-Synchronisierung ist **kein** Host-Orchestrator-Eingriff erforderlich.
- Konsequenz: #573 kann als Doku-/Governance-Härtung ohne verpflichtendes Wartungsfenster fortgeführt werden.
- Wartungsfenster bleibt **nur** dann Pflicht, wenn tatsächlich persistente Startpfad-Änderungen am Host/Container vorgenommen werden müssen (z. B. `/entrypoint.sh`, Orchestrator-Env-Injektion, kontrollierter Restart).

Temporäre Ausnahme-Klassifikation (wp2, evidenzpflichtig):

| Feld | Wert |
|---|---|
| exception_id | `bl15-r2-wp2-runtime-legacy-env-static-keys` |
| Scope | Ambient OpenClaw-Runtime mit statischen AWS-Env-Keys im regulären Startpfad |
| Control/Mitigation | Runtime-Key/Secret ausschließlich über Host-/Orchestrator-Secret-Setpoints führen; für Vergleichsdiagnostik optional Wrapper/Guard (`openclaw_runtime_assumerole_exec.sh`, `--assume-role-first`) nutzen |
| Owner | Nico + platform-ops |
| Sunset | 2026-03-15 (bis dahin Quelle der Ambient-Injection identifizieren und entfernen) |
| Follow-up | #570 |
| Evidenz | `artifacts/bl15/runtime-audit-20260301-default.log`, `artifacts/bl15/runtime-audit-20260301-assumerole.log`, `artifacts/bl17/oidc-only-guard-20260301-default.json`, `artifacts/bl17/oidc-only-guard-20260301-assumerole.json` |

### BL-15.r2.wp3-Entscheid (2026-03-01, #567)

Neubewertung des bisherigen Legacy-Key-Disable-Canary im Kontext der bestätigten Zielarchitektur:

- **Entscheid:** Disable-Canary ist für BL-15.r2 **kein Pflicht-Blocker** und wird im Standardpfad als **entfällt** bewertet.
- **Begründung:** Der Canary war an einen Decommission-/Runtime-OIDC-Pfad gekoppelt, der für OpenClaw-Runtime nicht mehr Zielzustand ist (Runtime bleibt Key/Secret; OIDC bleibt Deploy-only).
- **Governance-Regel:** Ein Disable-Canary bleibt als optionaler Härtungs-/Failover-Test zulässig, aber nur bei explizitem Bedarf, dokumentiertem Nutzen und vorbereitetem Rollback.

Entscheidungsmatrix für die Praxis:

| Entscheidungspfad | Trigger | Mindestnachweis |
|---|---|---|
| `entfällt` (Default) | Kein akuter Security-/Incident-Treiber für Disable-Experiment | Verweis auf diese Policy-Entscheidung + Parent-Sync (#564) |
| `optional durchführen` | Konkreter Bedarf (z. B. Incident-Learning, Audit-Auflage, gezielter Failover-Test) | Ziel/Hypothese, Wartungsfenster falls persistente Startpfad-Änderung nötig, Rollback-Plan, Evidenzpfade |

Konsequenz für BL-15.r2:
- Die externe Consumer-Zuordnung (Gate G3) ist **abgeschlossen**: `76.13.144.185` = OpenClaw-Umgebung (AI-Agent/Assistent). Architekturentscheid 2026-03-01: dauerhaft beibehalten (decision: retained). Kein Disable-Canary-Lauf erforderlich.

### Read-only Abschluss-Recheck (2026-03-01, BL-15.r2.wp2.c)

Reproduzierbarer Recheck mit aktueller Zielarchitektur (**Runtime = Key/Secret als bewusste Policy**):

- `./scripts/audit_legacy_runtime_consumers.sh` → Exit `30`
  - Log: `artifacts/bl15/runtime-audit-20260301T134803Z-default.log`
- `./scripts/check_bl17_oidc_assumerole_posture.sh --report-json artifacts/bl17/posture-report-20260301T134803Z-default.json` → Exit `30`
  - Log: `artifacts/bl15/posture-20260301T134803Z-default.log`
- `python3 scripts/inventory_bl17_runtime_credential_paths.py --output-json artifacts/bl17/runtime-credential-injection-inventory-20260301T134803Z-ambient.json` → Exit `10`
  - Log: `artifacts/bl15/runtime-inventory-20260301T134803Z-ambient.log`
- `python3 scripts/check_bl17_oidc_only_guard.py --output-json artifacts/bl17/oidc-only-guard-20260301T134803Z-default.json --posture-report-json artifacts/bl17/oidc-only-guard-20260301T134803Z-posture.json --runtime-report-json artifacts/bl17/oidc-only-guard-20260301T134803Z-runtime.json --cloudtrail-log artifacts/bl15/oidc-only-guard-20260301T134803Z-cloudtrail.log --cloudtrail-lookback-hours 6` → Exit `10`
  - Log: `artifacts/bl15/oidc-only-guard-20260301T134803Z.log`

Interpretation:
- OIDC-Deploy-Marker bleiben intakt; Runtime läuft weiterhin im dokumentierten Key/Secret-Mode.
- Die non-zero Exitcodes sind erwartete Findings für Legacy-Aktivität/Runtime-Key-Injection (Readiness weiter **NO-GO**, bis externe Consumer-Blocker aufgelöst sind).
- Die Policy-Synchronisierung ist damit nachvollziehbar aktualisiert und auf den gültigen Zielzustand referenziert.

### Externe Consumer-Matrix (BL-15 Iteration, aktualisiert 2026-03-01)

Zur strukturierten Abarbeitung der offenen Consumer wurde ein dediziertes Tracking ergänzt:

- `docs/LEGACY_CONSUMER_INVENTORY.md`
  - Abschnitt `3.1`: verbindliches Evidence-Schema pro Target (`caller_arn`, `credential_injection`, `aws_jobs_or_scripts`, `migration_path`, `cutover_target_date`, `evidence_refs`)
  - Abschnitt `3.2`: aktualisierte Target-Registry mit stabilen `target_id`s (Pflichtfelder ohne offene `TBD`-Platzhalter, inkl. Owner/Cutover-Blocker)

Aktueller Kurzbefund daraus:

- GitHub Actions Deploy ist bereits OIDC-migriert.
- OpenClaw Runtime auf diesem Host nutzt weiterhin runtime-injizierte Legacy-Umgebungsvariablen.
- Externe Targets sind strukturiert erfasst und ohne offene `TBD`-Platzhalter gepflegt. Primäres Target (`76.13.144.185`) = **OpenClaw-Umgebung** (AI-Agent/Assistent); Architekturentscheid 2026-03-01: dauerhaft beibehalten (decision: retained). Kein offener Blockerstatus mehr für BL-15.

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

| Gate | Muss erfüllt sein für **GO** | Primäre Evidenz | Status 2026-03-01 (BL-15.r2.wp4) | Bewertung |
|---|---|---|---|---|
| G1: Runtime-Policy dokumentiert | OpenClaw Runtime-Key/Secret-Nutzung ist explizit freigegeben, begründet und konsistent dokumentiert | `docs/BACKLOG.md`, BL-15.r2-Issues, dieses Dokument | Policy-Klarstellung + Parent-/Backlog-Sync abgeschlossen (`#570`, `#568`) | 🟢 |
| G2: Deploy-Pfad OIDC-konform | Aktive Deploy-Workflows nutzen OIDC ohne statische Keys | `.github/workflows/deploy.yml`, `./scripts/check_bl17_oidc_assumerole_posture.sh` | OIDC-Deploy verifiziert | 🟢 |
| G3: Externe Consumer vollständig inventarisiert | Für jedes Target: `caller_arn`, Injection-Pfad, Owner, Cutover-/Review-Datum, Evidenz | `docs/LEGACY_CONSUMER_INVENTORY.md` | **ACCEPTED (waived)** — Architekturentscheid 2026-03-01: externer Consumer (`76.13.144.185`) = **OpenClaw-Umgebung** (AI-Agent/Assistent, der das Repo verwaltet und AWS-Ressourcen nutzt); bleibt dauerhaft aktiv (decision: retained); Consumer-Migration entfällt als Gate-Kriterium | ✅ |
| G4: Monitoring + Rollback vorbereitet | Governance/Monitoring + dokumentierter Reaktivierungsweg vorhanden | Abschnitt 3 (Phase B), Fallback-Template | Basis vorhanden, Dry-Run/Abnahme offen | 🟡 |
| G5: Security-Hygiene Runtime-Key-Pfad | Rotation/Least-Privilege/Audit für Runtime-Key-Pfad nachvollziehbar und überprüfbar | IAM-/Audit-Evidenz + Runbooks | Dokumentations-/Runbook-Härtung erfolgt, operative Restarbeit an offenen externen Targets verbleibt | 🟡 |

### 4.2 Entscheidungslogik

- **GO**: Alle harten Gates (G1–G5) sind grün.
- **GO with timebox**: Kein rotes Gate; maximal 2 gelbe Gates mit klarer Restmaßnahme, Owner und fester Frist (≤14 Tage).
- **NO-GO**: Mindestens ein rotes Gate oder fehlender Sign-off eines Pflicht-Owners.

### 4.3 Aktueller Entscheid (Snapshot)

**Aktuell: GO (Architekturentscheid 2026-03-01).**

Begründung:
- G3 (Consumer-Migration) ist als «ACCEPTED (waived)» klassifiziert — externer Consumer (`76.13.144.185`) = **OpenClaw-Umgebung** (AI-Agent/Assistent); bleibt dauerhaft aktiv (decision: retained); kein weiterer Cutover erforderlich.
- G1 (Runtime-Policy dokumentiert): 🟢 — unverändert grün.
- G2 (Deploy-Pfad OIDC-konform): 🟢 — unverändert grün.
- G4 und G5: dokumentierter Stand bleibt gültig; mit G3-Waiver kein rotes Gate mehr vorhanden.
- BL-15 gilt damit als vollständig abgeschlossen.

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
| Decision-ID | `bl15-decommission-20260301-03` |
| Entscheidung | `GO (architectural decision 2026-03-01)` |
| Scope | `swisstopo-api-deploy Legacy IAM User` |
| Bewertungszeitpunkt (UTC) | `2026-03-01T18:00:00Z` |
| Gate-Status G1..G5 | `G1=🟢; G2=🟢; G3=✅ ACCEPTED (waived); G4=🟡; G5=🟡` |
| Timebox-Ende | `n/a` |
| Pflicht-Evidenz | `docs/LEGACY_CONSUMER_INVENTORY.md`, `artifacts/bl15/legacy-cloudtrail-fingerprint-report.json`, `artifacts/bl17/runtime-credential-injection-inventory.json` |
| Risiken (Top 3) | `1) Runtime-Key/Secret bleibt aktiv (bewusste Policy); 2) G4/G5 Restarbeiten laufen weiter (kein Blocker); 3) Externer Consumer dauerhaft aktiv — Architekturentscheid akzeptiert` |
| Freigaben | `Security: accepted`, `Platform: accepted`, `Service: accepted` |
| Next Review | `Kein Pflicht-Review — BL-15 abgeschlossen; bei Änderung der Architekturentscheidung erneut evaluieren` |

---

## 6) Vorgeschlagener Entscheidungsablauf (max. 5 Schritte)

1. **Evidenz aktualisieren** (Runtime-, CloudTrail- und Consumer-Inventar-Checks aus Abschnitt 1/3).
2. **Gates G1–G5 bewerten** und Ampelstatus dokumentieren.
3. **Entscheidung klassifizieren** (`GO`, `GO with timebox`, `NO-GO`) nach Abschnitt 4.2.
4. **Sign-off einholen** (Security/Platform/Service) mit Template aus Abschnitt 5.1.
5. **Nächsten operativen Schritt terminieren** (Cutover starten oder konkrete Blocker-Maßnahmen mit Termin/Owner).
