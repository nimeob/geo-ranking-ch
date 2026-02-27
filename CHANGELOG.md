# Changelog

Alle bemerkenswerten Änderungen an diesem Projekt werden in diesem Dokument festgehalten.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).
Dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

---

## [Unreleased]

### Added
- Projektdokumentation: README.md, ARCHITECTURE.md, DEPLOYMENT_AWS.md, OPERATIONS.md
- Basis-Verzeichnisstruktur (`docs/`, `scripts/`, `.github/workflows/`)
- GitHub Actions Placeholder-Workflow für CI/CD

### Changed (2026-02-27 — BL-20.4.a Umfelddaten-Radiusmodell + Kernkennzahlen, Issue #28)
- **`src/address_intel.py`** um ein neues Layer `intelligence.environment_profile` erweitert: radialer 3-Ring-Ansatz (`inner/mid/outer`) mit transparenter Distanzgewichtung, Domain-/Ring-Counts, Dichtewerten und Kernmetriken (`density`, `diversity`, `accessibility`, `family_support`, `vitality`, `quietness`, `overall`).
- **`summary_compact.intelligence.environment_profile`** ergänzt (Status, `overall_score`, `poi_total`) für schnelle operative Einordnung.
- **`tests/test_core.py`** um Regressionstests für das Radiusmodell und den Basic-Mode-Disable-Pfad erweitert.
- **`docs/api/environment-profile-radius-model-v1.md`** neu ergänzt und in **`docs/api/contract-v1.md`** verlinkt.
- **`docs/BACKLOG.md`** BL-20-Fortschritt um Abschlussnachweis für #28 fortgeschrieben.

### Changed (2026-02-27 — BL-20.1.j Stabiles grouped Response-Schema v1, Issue #279)
- **`docs/api/schemas/v1/analyze.grouped.response.schema.json`** neu ergänzt: normatives grouped Response-Schema mit fester Grundstruktur (`result.status` + `result.data`) und additiven Erweiterungspunkten (`additionalProperties`).
- **`docs/api/schemas/v1/analyze.grouped.core-paths.v1.json`** neu ergänzt: versionierte Single-Source-of-Truth-Liste für stabile Kernpfade (u. a. Confidence-, Entity- und Match-Score-Pfade).
- **`docs/api/grouped-response-schema-v1.md`** neu ergänzt: Human-readable Referenz inkl. Evolutionsregeln und Verlinkung der Kernpfad-/Schema-Artefakte.
- **`docs/api/examples/current/analyze.response.grouped.additive-before.json`** und **`docs/api/examples/current/analyze.response.grouped.additive-after.json`** ergänzt: reproduzierbare before/after-Beispiele für additive Erweiterung ohne Strukturbruch.
- **`tests/test_grouped_response_schema_v1.py`** neu ergänzt: Guard-Tests für Kernstruktur, Kernpfad-Stabilität, additive Evolution und Runtime-Pfadkonsistenz.
- **`docs/api/contract-v1.md`** und **`docs/api/contract-stability-policy.md`** um BL-20.1.j-Verweise/Regeln fortgeschrieben.

### Changed (2026-02-27 — BL-20.1.k.wp1 Contract: Code-only Response + Dictionary-Referenzfelder, Issue #287)
- **`docs/api/contract-v1.md`** um den BL-20.1.k.wp1-Abschnitt erweitert: normativer Contract-Diff für `result.status.dictionary.{version,etag,domains?}` inkl. Code-first-Regeln und Referenzierung der neuen before/after-Beispiele.
- **`docs/api/schemas/v1/analyze.grouped.response.schema.json`** und **`docs/api/schemas/v1/location-intelligence.response.schema.json`** additiv um den Dictionary-Envelope ergänzt (required bei vorhandenem Envelope: `version` + `etag`; optionale `domains` pro Domain mit `version`/`etag` + `path`).
- **`docs/api/examples/current/analyze.response.grouped.code-only-before.json`** und **`docs/api/examples/current/analyze.response.grouped.code-only-after.json`** neu ergänzt, um denselben Fall vor/nach Code-only-Migration mit Dictionary-Referenzen reproduzierbar zu zeigen.
- **`docs/api/grouped-response-schema-v1.md`** um die Dictionary-Envelope-Notiz und den Code-first-Beispielpfad fortgeschrieben.
- **`tests/test_api_contract_v1.py`** und **`tests/test_grouped_response_schema_v1.py`** um Guard-Checks für den neuen Dictionary-Envelope und die neuen before/after-Artefakte erweitert.
- **`docs/BACKLOG.md`** BL-20-Fortschritt um Abschlussnachweis für Issue #287 ergänzt.

### Changed (2026-02-27 — BL-20.1.k.wp2 Dictionary-Endpoints (versioniert + cachebar), Issue #288)
- **`src/web_service.py`** erweitert um Dictionary-Routing (`GET /api/v1/dictionaries`, `GET /api/v1/dictionaries/<domain>`) mit Domain-Tabellen für `building`/`heating`, stabilen ETags (Hash-basiert) und `Cache-Control`.
- Conditional-GET für Dictionaries implementiert: `If-None-Match` führt bei Match auf `304 Not Modified` inkl. `ETag` + `Cache-Control`, ohne Response-Body.
- **`tests/test_web_e2e.py`** um End-to-End-Guards für Dictionary-Index, Domain-Payloads, Unknown-Domain-404 und `304`-Cachepfad ergänzt.
- **`docs/api/contract-v1.md`** um BL-20.1.k.wp2-Sektion erweitert (normative Endpoint-/Caching-Regeln inkl. `If-None-Match`).
- **`docs/user/api-usage.md`** um Endpoint-Referenz + Curl-Beispiele für Dictionary-Endpoints inkl. Conditional-GET ergänzt.
- **`tests/test_api_contract_v1.py`** um Marker-Guards für die neue Contract-Sektion erweitert; **`docs/BACKLOG.md`** mit Abschlussnachweis #288 fortgeschrieben.

### Changed (2026-02-27 — BL-20.1.k.wp4 Migration/Kompatibilitätsmodus/Doku/Tests, Issue #290)
- **`src/web_service.py`** um optionalen Legacy-Migrationspfad erweitert: `options.include_labels` (boolean, Default `false`) steuert, ob Inline-Label-Felder (`building.decoded`, `energy.decoded_summary`) temporär weiter ausgeliefert werden.
- Nicht-boolsche Werte für `options.include_labels` liefern jetzt deterministisch `400 bad_request` (`options.include_labels must be a boolean when provided`).
- **`tests/test_web_e2e.py`** ergänzt um End-to-End-Nachweise für Default-code-first, Legacy-Opt-in und Input-Validierung des Flags.
- **`tests/test_web_service_grouped_response.py`** ergänzt um expliziten Guard für Legacy-Label-Projektion bei aktivem Kompatibilitätsmodus.
- **Contract-/User-/Ops-Doku** synchronisiert (`docs/api/contract-v1.md`, `docs/api/contract-stability-policy.md`, `docs/api/grouped-response-schema-v1.md`, `docs/user/api-usage.md`, `docs/OPERATIONS.md`) inkl. Sunset-Strategie und Release-Hinweisen.
- **`docs/api/schemas/v1/location-intelligence.request.schema.json`** und **`tests/test_api_contract_v1.py`** um `options.response_mode` + `options.include_labels` als additive Request-Optionen fortgeschrieben.

### Changed (2026-02-27 — BL-20.4.d.wp2 Two-Stage Suitability Response Fields, Issue #181)
- **`src/suitability_light.py`** erweitert um explizites Response-Paar `base_score` + `personalized_score`; solange kein aktives Präferenzsignal verarbeitet wird, liefert der Fallback deterministisch `personalized_score == base_score`.
- **`docs/api/contract-v1.md`**, **`docs/api/schemas/v1/location-intelligence.response.schema.json`**, **`docs/api/scoring_methodology.md`** und **`docs/api/field_catalog.json`** auf die neuen Two-Stage-Suitability-Felder synchronisiert.
- **`docs/api/examples/v1/location-intelligence.response.success.address.json`** sowie Golden-Contract-Payloads unter `tests/data/api_contract_v1/valid/` um die neuen Felder ergänzt.
- **`tests/test_suitability_light.py`** und **`tests/test_api_contract_v1.py`** um Guards für die neuen Felder erweitert; zusätzlicher Negativfall unter `tests/data/api_contract_v1/invalid/response.success.missing-two-stage-scores.json`.

### Changed (2026-02-27 — BL-15.wp7 Fingerprint-Korrelation als wiederverwendbares Modul, Issue #188)
- **`src/legacy_consumer_fingerprint.py`** neu ergänzt: kapselt CloudTrail-Event-Normalisierung, deterministische Fingerprint-Aggregation (`source_ip` + `user_agent`, optional `region`/`recipient_account`) sowie Report-Rendering.
- **`scripts/audit_legacy_cloudtrail_consumers.sh`** refaktoriert: nutzt das Shared-Modul für Page-Normalisierung und Auswertung, behält Exit-Code-Verhalten (`0/10/20`) bei und bietet optionale Dimensionen über `FINGERPRINT_INCLUDE_REGION`/`FINGERPRINT_INCLUDE_ACCOUNT`.
- **`tests/test_legacy_consumer_fingerprint.py`** ergänzt: deckt Mischquellen-/Tie-Sortierung, NDJSON-Robustheit und optionale Fingerprint-Dimensionen ab; bestehende Script-Regressionen bleiben grün.
- **`docs/LEGACY_IAM_USER_READINESS.md`** und **`docs/BACKLOG.md`** um Integrationshinweise + Abschlussnachweis für #188 fortgeschrieben.

### Changed (2026-02-27 — BL-20.x.wp1 Actionable TODO/FIXME-Filter, Issue #202)
- **`scripts/github_repo_crawler.py`** um `is_actionable_todo_line(...)` erweitert: TODO/FIXME-Treffer mit erledigt-/historisch-Markern (`✅`, `erledigt`, `abgeschlossen`, `closed`, `changelog`) werden nicht mehr als neue Finding-Issues erzeugt.
- **`tests/test_github_repo_crawler.py`** um gezielte Regressionsfälle ergänzt (Marker-Filter + End-to-End-Scan mit gemischten TODO-Zeilen), damit nur actionable Treffer in `scan_repo_for_findings` verbleiben.
- **`docs/WORKSTREAM_BALANCE_BASELINE.md`** und **`README.md`** um den Actionable-Filter-Hinweis im Crawler-Regressionskontext ergänzt.

### Changed (2026-02-27 — BL-20.x.wp2 Finding-Schema + Consistency-Reports, Issue #203)
- **`scripts/github_repo_crawler.py`** um ein konsistentes Finding-Schema (`type`, `severity`, `summary`, `evidence`, `source`) und stabile Report-Generierung erweitert (`reports/consistency_report.json` + `reports/consistency_report.md` in einem Lauf).
- Crawler-Audits (`audit_closed_issues`, `scan_repo_for_findings`, `audit_workstream_balance`) liefern nun strukturierte Findings zurück; Reports enthalten priorisierte Summary (Severity/Typ) plus evidenzbasierte Referenzen.
- **`tests/test_github_repo_crawler.py`** um Regressionsfälle für Report-Sortierung/-Schema und Datei-Output erweitert.
- **`README.md`** um den reproduzierbaren Dry-Run zur Report-Erzeugung ergänzt.

### Changed (2026-02-27 — BL-20.x.wp4 Code↔Doku-Drift-Check, Issue #205)
- **`scripts/github_repo_crawler.py`** um einen read-only Drift-Audit erweitert: extrahiert Code-Indikatoren (Flask-Routen + `os.getenv`-Flags), gleicht sie gegen zentrale Doku (`README.md`, `docs/OPERATIONS.md`, `docs/api/*`) ab und erzeugt evidenzbasierte Findings für undokumentierte Features sowie stale Routen-Referenzen.
- Drift-Findings sind begrenzt (`CODE_DOCS_MAX_FINDINGS`), um Finding-Fluten im Standardlauf zu vermeiden.
- **`tests/test_github_repo_crawler.py`** um Regressionsfälle für Drift-Erkennung (undokumentierter Flag, stale Route, Finding-Cap) erweitert.
- **`README.md`** Crawler-Regressionshinweis um den neuen Code↔Doku-Drift-Check ergänzt.

### Changed (2026-02-27 — BL-15 Parent-Sync Work-Packages, Issue #8)
- **`docs/BACKLOG.md`** BL-15 um eine explizite Work-Package-Checklist erweitert (abgeschlossen: `#109`, `#111`, `#112`; offen: `#151`, `#152`, `#187`, `#188`) zur sauberen Parent/Child-Fortschrittsführung.
- **GitHub Issue `#8`** Work-Package-Checklist auf den aktuellen Child-Scope synchronisiert und Zerlegungsbegründung auf die offenen Folgepakete erweitert.

### Changed (2026-02-27 — BL-15.wp2 Fingerprint-Evidence-Export, Issue #111)
- **`scripts/audit_legacy_cloudtrail_consumers.sh`** um strukturierten Export erweitert: pro Lauf wird ein reproduzierbarer JSON-Report (`FINGERPRINT_REPORT_JSON`, Default `artifacts/bl15/legacy-cloudtrail-fingerprint-report.json`) mit Zeitfenster, Event-Counts, Top-Fingerprints und letzten Events geschrieben.
- **`tests/test_audit_legacy_cloudtrail_consumers.py`** erweitert um Pfadvalidierung für `FINGERPRINT_REPORT_JSON` sowie Nachweise für Exportdatei-Inhalte in No-Event- und Event-Found-Pfaden.
- **`docs/LEGACY_IAM_USER_READINESS.md`** um Runbook-Nutzung und Report-Feldübersicht ergänzt.
- **`docs/BACKLOG.md`** BL-15-Nachweis um Abschluss von #111 fortgeschrieben.

### Changed (2026-02-27 — BL-20.1.h Capability-/Entitlement-Envelope, Issue #127)
- **`docs/api/contract-v1.md`** um BL-20.1.h-Abschnitt erweitert: additive Request-/Response-Envelopes (`options.capabilities`, `options.entitlements`, `result.status.capabilities`, `result.status.entitlements`) inkl. Stabilitäts-/Einführungsregeln und Verweisen auf #105/#106/#107/#18.
- **`docs/api/contract-stability-policy.md`** um dedizierte Policy-Sektion für den Capability-/Entitlement-Envelope erweitert (stable Envelope, beta/internal für innere Feature-Keys, Legacy-Kompatibilität als Muss).
- **`docs/api/schemas/v1/location-intelligence.request.schema.json`** und **`docs/api/schemas/v1/location-intelligence.response.schema.json`** um optionale Envelope-Felder ergänzt (rein additiv, non-breaking).
- **`tests/test_api_contract_v1.py`** erweitert um Envelope-Validierung + additive Legacy-Kompatibilitätsguards; neue positive/negative Golden-Cases unter `tests/data/api_contract_v1/`.
- **`tests/test_contract_compatibility_regression.py`** um Entitlement-Meta im Additivitäts-Regressionstest ergänzt.
- **`docs/BACKLOG.md`** BL-20-Fortschritt um Abschluss von #127 aktualisiert.

### Changed (2026-02-27 — BL-20.1.f.wp1 Checklist-/Issue-Sync, Issue #79)
- **`docs/BACKLOG.md`** BL-20-Fortschritt um den Checklist-/Issue-Sync für #79 ergänzt (Crawler-Reopen bereinigt, Re-Validation mit `validate_field_catalog.py` + `tests/test_api_field_catalog.py`/`tests/test_scoring_methodology_golden.py` dokumentiert).

### Changed (2026-02-27 — BL-17.wp8 Break-glass-Fallback-Runbook)
- **`docs/OPENCLAW_OIDC_FIRST_FALLBACK_PLAN.md`** um ein verbindliches Break-glass-Runbook erweitert (Triggerkriterien, Ablauf, Evidenz-Checkliste, CloudTrail-/Inventory-/Posture-Prüfpunkte, Rückweg auf AssumeRole-first).
- **`docs/LEGACY_IAM_USER_READINESS.md`** um ein vollständig ausgefülltes synthetisches Fallback-Event (read-only) ergänzt, inklusive referenzierter Evidenzpfade.
- **`docs/BACKLOG.md`** BL-17-Fortschritt/Work-Package-Checklist auf Abschluss von `#150` fortgeschrieben.

### Added (2026-02-27 — BL-17.wp4 Posture-Window-Aggregation)
- **`scripts/summarize_bl17_posture_reports.py`** neu ergänzt: aggregiert mehrere BL-17-Posture-Reports (`check_bl17_oidc_assumerole_posture.sh --report-json ...`) über ein Zeitfenster und liefert strukturierte Summary (Klassifikationsverteilung, Legacy-Treffer, `ready`/`not-ready`) mit klarer Exitcode-Policy (`0`/`10`/`2`).
- **`tests/test_summarize_bl17_posture_reports.py`** ergänzt: reproduzierbare Script-Tests für Ready-Window, Legacy-Treffer und Invalid-JSON-Input.

### Added (2026-02-27 — BL-17.wp5 Runtime-Credential-Injection-Inventar)
- **`scripts/inventory_bl17_runtime_credential_paths.py`** neu ergänzt: read-only Inventarisierung von Runtime-Credential-Injection-Pfaden inkl. strukturiertem JSON-Export (`--output-json`) und standardisierten Befundfeldern (`effect`, `migration_next_step`, `owner`).
- **`tests/test_inventory_bl17_runtime_credential_paths.py`** ergänzt: reproduzierbare Script-Tests für Legacy-Caller + statische Env-Keys (`exit 10`) sowie cleanen AssumeRole-Pfad (`exit 0`).
- **`docs/BL17_RUNTIME_CREDENTIAL_INJECTION_INVENTORY.md`** neu angelegt: Runbook/DoD für BL-17.wp5 inkl. Befundkategorien und Exitcode-Interpretation.

### Changed (2026-02-27 — BL-17.wp4 Doku-/Backlog-Sync)
- **`docs/OPENCLAW_OIDC_FIRST_FALLBACK_PLAN.md`** um Zeitfenster-Aggregationslauf ergänzt (`summarize_bl17_posture_reports.py` inkl. Exitcode-Interpretation).
- **`docs/BACKLOG.md`** BL-17-Fortschritt und Work-Package-Checklist um Abschluss von #144 erweitert; Folgepaket #145 als offen dokumentiert.

### Changed (2026-02-27 — BL-17.wp5 Doku-/Backlog-Sync)
- **`docs/OPENCLAW_OIDC_FIRST_FALLBACK_PLAN.md`** um den Runtime-Injection-Inventory-Lauf (`inventory_bl17_runtime_credential_paths.py`) inkl. Exitcode-Policy erweitert.
- **`docs/LEGACY_IAM_USER_READINESS.md`** um den neuen BL-17.wp5-Evidence-Pfad ergänzt (strukturierter Inventory-Report als Read-only-Nachweis).
- **`docs/BACKLOG.md`** BL-17-Work-Package-Checklist auf `#145` abgeschlossen fortgeschrieben.

### Changed (2026-02-26 — BL-17.wp1 AssumeRole-Exec Wrapper Hardening)
- **`scripts/aws_exec_via_openclaw_ops.sh`** gehärtet: fail-fast Validierung für `OPENCLAW_OPS_ROLE_ARN`, `OPENCLAW_OPS_SESSION_SECONDS` (Integer `900..43200`) und `OPENCLAW_OPS_SESSION_NAME`; robuste Fehlerbehandlung für `aws sts assume-role` und JSON-/Credential-Parsing.
- **`tests/test_aws_exec_via_openclaw_ops.py`** ergänzt: reproduzierbare Script-Tests für Missing-Args, Invalid-Duration, Invalid-Role-ARN, Parse-Error und Happy-Path mit gemocktem AWS-CLI-Verhalten.
- **`docs/OPERATIONS.md`** um Hinweis auf fail-fast Input-Validation des AssumeRole-Exec-Wrappers ergänzt.
- **`docs/BACKLOG.md`** BL-17-Fortschritt + Work-Package-Checklist um Abschluss von #136 erweitert.

### Changed (2026-02-26 — BL-18.1 kritischer Deploy-Blocker: ECS-Healthcheck-Churn)
- **`Dockerfile`** um Runtime-Dependency `curl` ergänzt (`apt-get install --no-install-recommends curl`), da die aktive ECS-Task-Definition den Container-Healthcheck via `curl -f http://localhost:8080/health || exit 1` ausführt.
- **`tests/test_dockerfile_runtime_deps.py`** neu ergänzt: Regressionstest, der den `curl`-Install-Guard im Dockerfile erzwingt.
- **`docs/BACKLOG.md`** BL-18.1 um den kritischen Deploy-Blocker-Fix (Freeze-Ausnahme) ergänzt.

### Added (2026-02-26 — BL-18.1.wp2 Blocker-Retry-Supervisor)
- **`scripts/blocker_retry_supervisor.py`** neu ergänzt: überwacht `status:blocked`-Issues auf externe Timeout/Reachability-Fehler, erzwingt 3h Grace-Period + max. 3 Fehlversuche und erstellt bei 3/3 automatisch ein Follow-up-Issue inkl. Rückverlinkung.
- **`tests/test_blocker_retry_supervisor.py`** ergänzt: reproduzierbare Unit-Tests für Fehlerklassifikation, Grace-Handling und Follow-up-Erzeugung.

### Changed (2026-02-26 — BL-18.1.wp2 Doku-Sync)
- **`docs/AUTONOMOUS_AGENT_MODE.md`** um verbindliche Blocker-Retry-Policy (Grace/Retry/Follow-up) erweitert.
- **`docs/OPERATIONS.md`** um Betriebsabschnitt für den Retry-Supervisor inkl. Cron-Hinweis + manuellem Debug-Lauf ergänzt.
- **`docs/BACKLOG.md`** BL-18.1-Fortschritt um Abschluss von #134 inkl. Testnachweis aktualisiert.

### Changed (2026-02-26 — BL-18.fc1 Contract-Compatibility-Regression)
- **`tests/test_contract_compatibility_regression.py`** ergänzt: Guard-Tests für additive Contract-Evolution (Legacy-Minimalprojektion bleibt stabil), explizite Semantik-Trennung `result.status` vs. `result.data` und Smoke-Minimum-Kompatibilität.
- **`docs/api/contract-stability-policy.md`** um BL-18.fc1-Abschnitt erweitert (Forward-Compatibility-Guardrails mit Referenzen auf #3 und #127).
- **`docs/BACKLOG.md`** BL-18-Fortschritt um Abschluss von #130 inkl. Testnachweis aktualisiert.

### Changed (2026-02-26 — BL-18.fc2 Request-Options-Envelope)
- **`src/web_service.py`** um robusten `options`-Envelope-Parser ergänzt: `options` ist optional (Default-Verhalten unverändert), muss bei Presence ein Objekt sein (`400 bad_request` bei Typfehler), unbekannte Keys bleiben additive No-Op-Felder.
- **`tests/test_web_e2e.py`** um Guard-Tests erweitert: unbekannte `options`-Keys dürfen den Happy-Path nicht brechen; nicht-objektförmige `options` liefern deterministisch `400 bad_request` statt Crash.
- **`docs/api/contract-stability-policy.md`** und **`docs/api/contract-v1.md`** um FC2-Policy ergänzt (stabiler `options`-Namespace für spätere Erweiterungen, Verweise auf #3/#107/#127).
- **`docs/BACKLOG.md`** BL-18-Fortschritt um Abschluss von #131 inkl. Nachweiskommando aktualisiert.

### Changed (2026-02-26 — BL-15 CloudTrail-Audit Testhärtung)
- **`tests/test_audit_legacy_cloudtrail_consumers.py`** neu ergänzt: reproduzierbare Script-Tests für `scripts/audit_legacy_cloudtrail_consumers.sh` (Parametervalidierung, No-Events `exit 0`, Events-Found `exit 10`, LookupEvents-Filterung via `INCLUDE_LOOKUP_EVENTS`).
- **`docs/BACKLOG.md`** BL-15-Nachweis um den Testhärtungsstand für Issue #109 erweitert.

### Changed (2026-02-26 — BL-15 Readiness-Recheck Hardening)
- **`scripts/audit_legacy_aws_consumer_refs.sh`** Repo-Scan auf `git grep` mit Excludes (`artifacts/`, `.venv/`, `.terraform/`) umgestellt, damit erzeugte Audit-Logs keine Folgeaudits verfälschen.
- **`docs/LEGACY_IAM_USER_READINESS.md`** um dokumentierten Worker-Recheck ohne lokale `aws`-CLI ergänzt (Exit-Codes + Implikationen für BL-15-Status).
- **`docs/BACKLOG.md`** BL-15-Nachweis um den Worker-Recheck und die Script-Härtung erweitert.
- **`tests/test_audit_legacy_aws_consumer_refs.py`** ergänzt: Regressionstest, dass `artifacts/` beim Legacy-Repo-Scan ignoriert wird.

### Added (2026-02-26 — BL-20.1.d.wp2 Human-readable Field Reference)
- **`docs/api/field-reference-v1.md`** neu angelegt: menschenlesbare Feldreferenz für `legacy` + `grouped` inkl. Feldpfad, Semantik, Typ, Pflicht/Optionalität, Stabilitätsklasse, Modusbedingungen und Beispielwert.

### Added (2026-02-26 — BL-20.1.d.wp3 Contract-Examples)
- **`docs/api/examples/current/analyze.response.grouped.partial-disabled.json`** ergänzt: grouped Edge-Case mit fehlenden/deaktivierten Quellen/Modulen (`status=disabled|missing`, `present=false`, leere `by_source.data`-Blöcke) als Integrationsreferenz für defensive Consumer.

### Changed (2026-02-26 — BL-20.1.d.wp3 Doku-/Test-Sync)
- **`docs/api/contract-v1.md`** um explizite Contract-Example-Verweise erweitert (vollständige legacy/grouped Payloads + grouped Edge-Case).
- **`docs/api/field-reference-v1.md`** um direkten Link auf den grouped Edge-Case ergänzt.
- **`docs/user/api-usage.md`** um versionierte Referenzlinks zu den vollständigen und Edge-Case-Beispielpayloads erweitert.
- **`tests/test_api_field_catalog.py`** um Guard-Checks für den grouped Edge-Case erweitert (Status `missing|disabled`, fehlendes Modul, `present=false`, leere Source-Datenblöcke).
- **`docs/BACKLOG.md`** BL-20-Fortschritt um Abschluss von #72 aktualisiert.

### Changed (2026-02-26 — BL-20.1.d.wp2 Doku-/Test-Sync)
- **`docs/api/contract-v1.md`** um direkten Verweis auf die neue Feldreferenz erweitert (Abschnitt „Human-readable Feldreferenz“ + Link im Feldkatalog-Abschnitt).
- **`README.md`** Dokumentationstabelle um `docs/api/field-reference-v1.md` ergänzt.
- **`tests/test_api_field_catalog.py`** um Marker-Checks für die neue Feldreferenz erweitert.
- **`docs/BACKLOG.md`** BL-20-Fortschritt um Abschluss von #71 aktualisiert.

### Added (2026-02-26 — BL-20.1.d.wp4 Stability Guide + Contract-Change-Policy)
- **`docs/api/contract-stability-policy.md`** neu angelegt: verbindliche Stabilitätsklassen (`stable`, `beta`, `internal`) inkl. Integrator-Regeln, Breaking/Non-Breaking-Kriterien und Versionsregel für `/api/v1`.

### Changed (2026-02-26 — BL-20.1.d.wp4 Doku-/Backlog-Sync)
- **`docs/api/contract-v1.md`** um Abschnitt „Stability Guide + Contract-Change-Policy" erweitert (Cross-Link + Kurzregeln).
- **`README.md`** Dokumentationstabelle um den Stability-Policy-Leitfaden ergänzt.
- **`docs/BACKLOG.md`** BL-20-Fortschritt um Abschluss von #73 aktualisiert.

### Added (2026-02-26 — BL-20.1.f.wp1 Score-Katalog)
- **`docs/api/scoring_methodology.md`** neu angelegt: dedizierte Methodik-Spezifikation mit vollständigem Score-Katalog (legacy + grouped), Richtung/Skala/Stabilitätsstatus je Feld und Konsistenzregeln zum Feldkatalog.

### Changed (2026-02-26 — BL-20.1.f.wp1 Doku-/Test-Sync)
- **`docs/api/contract-v1.md`** um Abschnitt „Scoring Methodology Specification“ inkl. Cross-Link erweitert.
- **`tests/test_api_field_catalog.py`** um Guard-Checks ergänzt, die die Abdeckung aller scoring-relevanten Feldpfade in `docs/api/scoring_methodology.md` erzwingen.
- **`docs/BACKLOG.md`** BL-20-Fortschritt um Abschluss von #79 aktualisiert.

### Added (2026-02-26 — BL-20.2.b Feld-Mapping Quelle -> Domain)
- **`docs/DATA_SOURCE_FIELD_MAPPING_CH.md`** neu angelegt: quellenweises Feld-Mapping auf Domainpfade (`build_report`/`result.data.*`) inkl. verbindlicher Transform-/Normalisierungsregeln und Source->Module-Zuordnung für `by_source`.
- **`tests/test_data_source_field_mapping_docs.py`** ergänzt: Regressionstest auf Pflichtsektionen der Mapping-Doku inkl. Follow-up-Verweisen (#63/#64/#65).
- **Follow-up-Issues angelegt:** #63 (machine-readable Mapping-Spec), #64 (Transform-Regeln als wiederverwendbare Functions + Tests), #65 (Source-Schema-Drift-Checks).

### Changed (2026-02-26 — BL-20.2.b Doku-/Backlog-Sync)
- **`docs/DATA_SOURCE_INVENTORY_CH.md`** um direkten Verweis auf die neue Feld-Mapping-Spezifikation erweitert.
- **`README.md`** Dokumentationstabelle um `docs/DATA_SOURCE_FIELD_MAPPING_CH.md` ergänzt.
- **`docs/BACKLOG.md`** BL-20-Fortschritt aktualisiert (#25 abgeschlossen; Follow-up-Gaps #63/#64/#65 dokumentiert).

### Added (2026-02-26 — BL-20.7.a.r2 Konfigurationsmatrix Packaging/Runtime)
- **`docs/PACKAGING_BASELINE.md`** um Abschnitt „Konfigurationsmatrix (Packaging/Runtime)" erweitert: konsolidierte Parameterliste für Build-/Run-Modi inkl. Pflicht/Optional, Default und Beispielwerten.
- **`tests/test_user_docs.py`** erweitert: Regressionstest für die neue Matrix-Sektion inkl. Pflicht-Querverweis auf den User-Config-Guide.

### Changed (2026-02-26 — BL-20.7.a.r2 Doku-/Backlog-Sync)
- **`docs/user/configuration-env.md`** um direkten Verweis auf die Packaging-Konfigurationsmatrix ergänzt.
- **`README.md`** Dokumentationstabellen-Eintrag zu `docs/PACKAGING_BASELINE.md` auf r1/r2/r3-Umfang aktualisiert.
- **`docs/BACKLOG.md`** BL-20-Fortschritt aktualisiert (#55 abgeschlossen; nächster Schritt: Parent #34 finalisieren).

### Added (2026-02-26 — BL-20.7.a.r1 Packaging-Baseline)
- **`docs/PACKAGING_BASELINE.md`** neu angelegt: reproduzierbare Build/Run-Matrix (Local + Docker), Schrittfolgen für Verifikation (`/health`) und klarer Scope für den API-only Packaging-Basisschnitt.
- **`tests/test_user_docs.py`** erweitert: Regressionstest auf Pflichtsektionen der Packaging-Baseline.

### Changed (2026-02-26 — BL-20.7.a.r1 Doku-/Backlog-Sync)
- **`README.md`** Dokumentationstabelle um `docs/PACKAGING_BASELINE.md` erweitert.
- **`docs/BACKLOG.md`** BL-20-Fortschritt aktualisiert (#54 abgeschlossen; Next Steps #55/#56).

### Added (2026-02-26 — BL-20.7.a.r3 Basis-Release-Checkliste)
- **`docs/PACKAGING_BASELINE.md`** um eine prüfbare API-only Basis-Release-Checkliste ergänzt (Build, Run, Smoke, Test-Gate, Doku-Gate, Artefakt-Nachweis) inkl. markierter Follow-ups.

### Changed (2026-02-26 — BL-20.7.a.r3 Doku-/Backlog-Sync)
- **`docs/OPERATIONS.md`** Release-Checkliste um direkten Verweis auf die Packaging-Baseline-Checks erweitert.
- **`README.md`** Packaging-Doku-Beschreibung auf Build/Run + Basis-Release-Checkliste aktualisiert.
- **`docs/BACKLOG.md`** BL-20-Fortschritt aktualisiert (#56 abgeschlossen, nächster Schritt #55).

### Added (2026-02-26 — BL-20.1.a API-Contract v1)
- **`docs/api/contract-v1.md`** neu angelegt: versionierter BL-20-Vertrag mit Pfadstrategie (`/api/v1`), Request-/Response-Profil, Fehlercode-Matrix und Verweisen auf Schemas/Beispielpayloads.
- **`docs/api/schemas/v1/*.json`** ergänzt: Request-, Success-Response- und Error-Envelope-Schema für `POST /api/v1/location-intelligence`.
- **`docs/api/examples/v1/*.json`** ergänzt: adressbasierter + punktbasierter Request, Success-Response und `bad_request`-Fehlerbeispiel.
- **`tests/test_api_contract_v1.py`** ergänzt: Guard-Tests für Contract-Doku, Schema-/Beispieldateien und Basiskonsistenz der Payloads.

### Changed (2026-02-26 — BL-20.1.a Doku-Sync)
- **`docs/user/api-usage.md`** um Verweis auf den versionierten BL-20-API-Vertrag ergänzt.
- **`README.md`** Dokumentationstabelle um `docs/api/contract-v1.md` erweitert.
- **`docs/BACKLOG.md`** BL-20-Fortschritt aktualisiert (#22 abgeschlossen, nächster Schritt #23) und BL-20-Status auf „in Umsetzung" angehoben.

### Added (2026-02-26 — BL-20.1.b Contract-Validierungstests)
- **`tests/data/api_contract_v1/valid/*.json`** ergänzt: positive Golden-Case-Payloads für Request/Success/Error.
- **`tests/data/api_contract_v1/invalid/*.json`** ergänzt: negative Golden-Case-Payloads für typische Vertragsverletzungen.
- **`.github/workflows/contract-tests.yml`** ergänzt: dedizierter CI-Check für API-Contract-v1-Golden-Tests.

### Changed (2026-02-26 — BL-20.1.b Test-/CI-Verdrahtung)
- **`tests/test_api_contract_v1.py`** von Struktur-Checks auf echte Contract-Golden-Validierung erweitert (positive + negative Fälle).
- **`docs/api/contract-v1.md`** um CI-Abschnitt (Workflow + Trigger + Golden-Testdaten) ergänzt.
- **`docs/BACKLOG.md`** BL-20-Fortschritt aktualisiert (#23 abgeschlossen, nächster Schritt #24).

### Added (2026-02-26 — BL-20.1.e Maschinenlesbarer API-Feldkatalog)
- **`docs/api/field_catalog.json`** neu angelegt: Feldmanifest für aktuell ausgelieferte Response-Felder über beide Shapes (`legacy`, `grouped`) inkl. Typ, Required-Status, Stability, Provenance-Hinweis und Modusbedingungen.
- **`docs/api/examples/current/analyze.response.grouped.success.json`** ergänzt: referenzierbarer grouped Success-Payload für Contract-/Manifest-Validierung.
- **`scripts/validate_field_catalog.py`** ergänzt: prüft Manifest-Schema, Feldabdeckung gegen Beispielpayloads, Typkonsistenz und Required-Felder pro Shape.
- **`tests/test_api_field_catalog.py`** ergänzt: Regressionstest für Feldkatalog-Validator und Contract-Doku-Referenzen.

### Changed (2026-02-26 — BL-20.1.e Doku-/CI-Sync)
- **`.github/workflows/contract-tests.yml`** erweitert: Trigger + Ausführung für Feldkatalog-Checks (`tests/test_api_field_catalog.py`, `scripts/validate_field_catalog.py`).
- **`docs/api/contract-v1.md`** um Feldkatalog-Abschnitt und Pflegeprozess ergänzt (Single-Source-of-Truth + Update-Workflow).
- **`docs/user/api-usage.md`** um direkten Verweis auf den maschinenlesbaren Feldkatalog ergänzt.
- **`docs/BACKLOG.md`** BL-20-Fortschritt aktualisiert (#67 abgeschlossen).

### Added (2026-02-26 — BL-19.6 Betrieb & Runbooks)
- **`docs/user/operations-runbooks.md`** neu angelegt: kompaktes User-Runbook für Daily Quick Check, reproduzierbaren `/analyze`-Smoke, kurzen Stabilitätslauf, Deploy-Checks und Incident-Minirunbook mit Evidenz-Pfad.
- **`tests/test_user_docs.py`** erweitert: prüft Präsenz/Kernsektionen des neuen Operations-Guides sowie Cross-Links aus User-Index/Getting-Started.

### Changed (2026-02-26 — BL-19.6 Doku-Integration)
- **`docs/user/README.md`** verlinkt jetzt den Operations Quick Guide.
- **`docs/user/getting-started.md`** und **`docs/user/troubleshooting.md`** um direkte Verweise auf `operations-runbooks.md` ergänzt.
- **`README.md`** Doku-Tabelle um `docs/user/operations-runbooks.md` erweitert.
- **`docs/BACKLOG.md`** BL-19-Fortschritt um BL-19.6 ergänzt und Next-Step auf Parent-Issue-Finalisierung aktualisiert.

### Added (2026-02-26 — BL-19.8 Doku-Qualitätsgate)
- **`tests/test_markdown_links.py`** neu angelegt: prüft für alle getrackten Markdown-Dateien interne Links (Datei-Targets, Repo-Grenzen, Verzeichnisziele) sowie Markdown-Anker auf auflösbare Überschriften-Slugs.
- **`scripts/check_docs_quality_gate.sh`** neu angelegt: führt BL-19.8 als „frisches Setup“ in einem temporären venv aus (Install `requirements-dev.txt`, danach `pytest -q tests/test_user_docs.py tests/test_markdown_links.py`).
- **`.github/workflows/docs-quality.yml`** neu angelegt: startet das Doku-Qualitätsgate automatisch bei Doku-relevanten Push-/PR-Änderungen.

### Changed (2026-02-26 — BL-19.8 Doku-Gate-Integration)
- **`README.md`** und **`docs/OPERATIONS.md`** um den ausführbaren Gate-Befehl `./scripts/check_docs_quality_gate.sh` ergänzt.
- **`docs/BACKLOG.md`** Fortschritt für BL-19 aktualisiert (BL-19.3 und BL-19.8 als umgesetzt; nächster Fokus bleibt BL-19.5).

### Added (2026-02-26 — BL-20.7.b GTM-MVP-Artefakte)
- **`docs/GO_TO_MARKET_MVP.md`** neu angelegt: Value Proposition, Scope/Non-Scope, Packaging-Rahmen (API-only vs GUI+API), Demo-Storyline (10–12 min) und nächste Schritte für BL-20.7.
- **`tests/test_go_to_market_mvp_docs.py`** ergänzt: Regressionstest auf Pflichtsektionen der GTM-Doku inkl. Referenzen auf die Risiko-Follow-ups (#36/#37/#38).

### Changed (2026-02-26 — BL-20.7.b Backlog-/Vision-Sync)
- **`docs/BACKLOG.md`** um Fortschrittseintrag für BL-20.7.b ergänzt (Issue #35 abgeschlossen, Follow-up-Risiken #36/#37/#38, nächster Schritt #34).
- **`docs/VISION_PRODUCT.md`** um Verweis auf die GTM-MVP-Artefakte erweitert.
- **`README.md`** Dokumentations-Tabelle um `docs/GO_TO_MARKET_MVP.md` ergänzt.

### Added (2026-02-26 — BL-19.4 API Usage Guide + README-Featurestruktur)
- **`docs/user/api-usage.md`** neu angelegt: vollständige Endpoint-Referenz (`/health`, `/version`, `/analyze`) mit Auth-Verhalten, Request-/Response-Beispielen, Request-ID-Priorität/Sanitization, Statuscode-Matrix und API-relevanten ENV-Variablen.
- **`tests/test_user_docs.py`** ergänzt: Regressionstests für User-Doku-Struktur (API-Guide vorhanden, korrekte Cross-Links in `docs/user/*`, thematisch gegliederte Feature-Sektion im Root-README).

### Changed (2026-02-26 — BL-19.4/BL-19.7 Doku-Integration)
- **`docs/user/README.md`** verlinkt den API-Guide jetzt direkt (`./api-usage.md`) statt Platzhalter.
- **`docs/user/getting-started.md`** verweist auf den neuen API-Guide als nächsten Schritt.
- **`README.md`** um thematisch organisierte Webservice-Featureliste erweitert und User-Doku-Link auf `docs/user/api-usage.md` ergänzt.
- **`docs/BACKLOG.md`** Fortschritt für BL-19 aktualisiert (BL-19.4 + BL-19.7 als umgesetzt markiert, nächster Fokus BL-19.3).

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Double-Slash-Pfad-Normalisierung + Real-Run, Iteration 48)
- **`src/web_service.py`:** Routing-Normalisierung kollabiert jetzt zusätzlich doppelte Slash-Segmente (`//`) auf einen Slash, bevor Endpunkte aufgelöst werden; Query-/Fragment-Ignorierung und tolerant handling für trailing Slashes bleiben unverändert aktiv.
- **`tests/test_web_e2e.py`:** neue E2E-Fälle sichern reproduzierbar ab, dass `//health//?probe=1`, `//version///?ts=1` und `POST //analyze//?trace=double-slash` korrekt funktionieren inkl. Request-ID-Echo.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`124 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`).
- **Smoke-Variante:** getrimmter Short-Hyphen-Request-Alias (`SMOKE_REQUEST_ID_HEADER="request-id"`) mit Echo-Check aktiv (`SMOKE_ENFORCE_REQUEST_ID_ECHO="TrUe"`, `request_id_header_name=Request-Id`).
- **Stabilitäts-Variante:** getrimmter Underscore-`X`-Correlation-Alias (`SMOKE_REQUEST_ID_HEADER="x_correlation_id"`) mit deaktiviertem Echo-Check (`SMOKE_ENFORCE_REQUEST_ID_ECHO="off"`) und booleschem Stop-Flag-Alias (`STABILITY_STOP_ON_FIRST_FAIL="no"`) stabil reproduziert (`request_id_header_name=X_Correlation_Id`).
- **API-Realcheck Double-Slash-Pfade:** `GET //health//?probe=double-slash` und `POST //analyze//?trace=double-slash` liefern `200` + konsistentes Request-ID-Echo in Header+JSON.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772122638.json`, `artifacts/worker-1-10m/iteration-48/bl18.1-remote-stability-local-worker-1-10m-1772122638.ndjson`, `artifacts/bl18.1-double-slash-path-normalization-worker-1-10m-1772122638.json`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772122638.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: README/Runbook/Backlog auf Worker-1-10m Iteration-48 + Double-Slash-Pfade synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Routing-Hinweise um Double-Slash-Kollaps ergänzt und Nachweisführung auf Iteration 48 (`124 passed`, Smoke + 3x Stabilität + API-Double-Slash-Realcheck) angehoben.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Pfad-Normalisierung (`/analyze/` + Query tolerant) + Real-Run, Iteration 47)
- **`src/web_service.py`:** Routing normalisiert jetzt den Request-Pfad robust über `urlsplit(...).path` und toleriert optionale trailing Slashes; Query-/Fragment-Anteile werden für die Endpunktauflösung ignoriert (`/health/?...`, `/version/?...`, `/analyze/?...`).
- **`tests/test_web_e2e.py`:** neue E2E-Fälle sichern reproduzierbar ab, dass `/health/?probe=1`, `/version/?ts=1` und `POST /analyze/?trace=1` weiterhin korrekt funktionieren inkl. Request-ID-Echo.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`122 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`).
- **Smoke-Variante:** getrimmter Short-Hyphen-Correlation-Alias (`SMOKE_REQUEST_ID_HEADER="correlation-id"`) mit Echo-Check aktiv (`SMOKE_ENFORCE_REQUEST_ID_ECHO="on"`, `request_id_header_name=Correlation-Id`).
- **Stabilitäts-Variante:** getrimmter Underscore-`X`-Request-Alias (`SMOKE_REQUEST_ID_HEADER="x_request_id"`) mit deaktiviertem Echo-Check (`SMOKE_ENFORCE_REQUEST_ID_ECHO="No"`) und booleschem Stop-Flag-Alias (`STABILITY_STOP_ON_FIRST_FAIL="off"`) stabil reproduziert (`request_id_header_name=X_Request_Id`).
- **API-Realcheck Pfad-Normalisierung:** `/health/?probe=1` und `/analyze/?trace=path-normalization` liefern weiterhin `200` + konsistentes Request-ID-Echo in Header+JSON.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772121986.json`, `artifacts/worker-1-10m/iteration-47/bl18.1-remote-stability-local-worker-1-10m-1772121986.ndjson`, `artifacts/bl18.1-path-normalization-worker-1-10m-1772121986.json`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772121986.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: README/Runbook/Backlog auf Worker-1-10m Iteration-47 + Pfad-Normalisierung synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Routing-Hinweise um tolerierte trailing Slashes + Query-ignorierende Endpunktauflösung ergänzt und Nachweisführung auf Iteration 47 (`122 passed`, Smoke + 3x Stabilität + API-Pfad-Realcheck) angehoben.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m `Request_Id`-Smoke + `X_Correlation_Id`-Stabilität, Iteration 46)
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`120 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`).
- **Smoke-Variante:** getrimmter Short-Underscore-Primäralias (`SMOKE_REQUEST_ID_HEADER="request_id"`) mit booleschem Echo-Alias (`SMOKE_ENFORCE_REQUEST_ID_ECHO="YeS"`) und bewusst leer gelassener `SMOKE_REQUEST_ID` (auto-generierte Default-ID bestätigt, `request_id_header_name=Request_Id`).
- **Stabilitäts-Variante:** getrimmter Underscore-`X`-Correlation-Alias (`SMOKE_REQUEST_ID_HEADER="x_correlation_id"`) mit deaktiviertem Echo-Check (`SMOKE_ENFORCE_REQUEST_ID_ECHO="off"`) und booleschem Stop-Flag-Alias (`STABILITY_STOP_ON_FIRST_FAIL="No"`) stabil reproduziert (`request_id_header_name=X_Correlation_Id`).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772121276.json`, `artifacts/worker-1-10m/iteration-46/bl18.1-remote-stability-local-worker-1-10m-1772121276.ndjson`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772121276.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-1-10m Iteration-46 synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Nachweisführung auf Iteration 46 (`120 passed`, Smoke + 3x Stabilität) angehoben und um den kombinierten Alias-Run (`request_id` im Smoke, `x_correlation_id` in Stabilität, boolesche Flag-Aliasse `YeS/off/No`) ergänzt.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m auto-generierte Default-Request-ID + Real-Run, Iteration 45)
- **`scripts/run_remote_api_smoketest.sh`:** für leere/nicht gesetzte `SMOKE_REQUEST_ID` wird jetzt eine eindeutige Default-ID (`bl18-<epoch>-<uuid-suffix>`) erzeugt, damit enge/parallele Läufe nicht auf derselben Korrelations-ID landen.
- **`tests/test_remote_smoke_script.py`:** E2E-Fall ergänzt, der bei eingefrorener Systemzeit (`PATH`-override auf Fake-`date`) zwei Smoke-Läufe ohne `SMOKE_REQUEST_ID` startet und die eindeutige Auto-ID-Generierung reproduzierbar absichert.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`120 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) mit auto-generierter Default-Request-ID im Smoke (`SMOKE_REQUEST_ID` bewusst nicht gesetzt).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772120889.json`, `artifacts/worker-1-10m/iteration-45/bl18.1-remote-stability-local-worker-1-10m-1772120889.ndjson`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772120889.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: README/Runbook/Backlog auf Iteration-45 + Default-Request-ID synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** `SMOKE_REQUEST_ID` als optionale Variable mit auto-generierter Default-ID dokumentiert und Nachweisführung auf Iteration 45 (`120 passed`, Smoke + 3x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m echte Short-Alias-Header-Sendung + Real-Run, Iteration 44)
- **`scripts/run_remote_api_smoketest.sh`:** Alias-Normalisierung für `SMOKE_REQUEST_ID_HEADER` präzisiert: `request-id`/`correlation-id` senden jetzt real `Request-Id`/`Correlation-Id`, `request_id`/`correlation_id` senden `Request_Id`/`Correlation_Id`; `x-*`-Aliasse bleiben unverändert auf `X-*`.
- **`tests/test_remote_smoke_script.py`:** Happy-Path-Abdeckung erweitert für echte Short-Alias-Headernamen (`request-id`, `correlation-id`, `request_id`, `correlation_id`) inkl. Assert auf `request_id_header_name`.
- **`tests/test_web_e2e.py`:** zusätzliche API-E2E-Fälle sichern `Request_Id` als primären Kurz-Alias sowie den Fallback auf `Correlation_Id` reproduzierbar ab.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`119 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) mit echten Short-Alias-Headern (`request_id_header_name=Request-Id` im Smoke, `Correlation_Id` in Stabilität).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772120287.json`, `artifacts/worker-1-10m/iteration-44/bl18.1-remote-stability-local-worker-1-10m-1772120287.ndjson`, `artifacts/bl18.1-request-id-short-underscore-alias-worker-1-10m-1772120287.json`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772120287.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-44 + echte Short-Alias-Header synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Alias-Mapping-Doku auf echte Short-Header-Sendung aktualisiert (`Request-Id`/`Correlation-Id`, `Request_Id`/`Correlation_Id`) und Nachweisführung auf Iteration 44 (`119 passed`, Smoke + 3x Stabilität + Short-Underscore-API-Realcheck) angehoben.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Short-Request-ID-Header-Aliasse (`Request-Id`/`Correlation-Id`) + Real-Run, Iteration 43)
- **`src/web_service.py`:** Request-ID-Korrelation akzeptiert jetzt zusätzlich kurze Header-Aliasse (`Request-Id`/`Request_Id` als primär, `Correlation-Id`/`Correlation_Id` als Fallback) und nutzt weiterhin denselben Sanitizer/Fallback-Pfad wie bei `X-*`-Headern.
- **`tests/test_web_e2e.py`:** neue API-E2E-Fälle verifizieren reproduzierbar, dass `Request-Id` primär gespiegelt wird und bei ungültigem primären Request-Alias deterministisch `Correlation-Id` gewinnt.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`115 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) im getrimmten Short-Alias-Mode (`SMOKE_REQUEST_ID_HEADER="request-id"` im Smoke, `"correlation_id"` in Stabilität).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772119525.json`, `artifacts/worker-1-10m/iteration-43/bl18.1-remote-stability-local-worker-1-10m-1772119525.ndjson`, `artifacts/bl18.1-request-id-short-alias-worker-1-10m-1772119525.json`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772119525.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-43 + Short-Header-Aliasse synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Request-ID-Korrelationsdoku um Short-Aliasse (`Request-Id`/`Correlation-Id`) erweitert und Nachweisführung auf Iteration 43 (`115 passed`, Smoke + 3x Stabilität + Short-Alias-API-Realcheck) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A-10m ASCII-Only Request-ID-Guard + Real-Run, Iteration 42)
- **`src/web_service.py`:** Request-ID-Sanitizer verwirft jetzt zusätzlich Non-ASCII-Werte; bei ungültigem Primärheader bleibt der bestehende Correlation-Fallback deterministisch aktiv.
- **`scripts/run_remote_api_smoketest.sh`:** `SMOKE_REQUEST_ID` wird fail-fast auch auf ASCII-only geprüft (`exit 2` bei Non-ASCII), damit unsichtbare/mehrdeutige Headerwerte nicht in Remote-Runs landen.
- **`tests/test_web_e2e.py`:** neuer API-E2E-Fall verifiziert den Correlation-Fallback bei Non-ASCII `X-Request-Id`.
- **`tests/test_remote_smoke_script.py`:** neuer Negativtest deckt fail-fast für Non-ASCII `SMOKE_REQUEST_ID` reproduzierbar ab.
- **Langlauf-Real-Run (Worker A-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`113 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-a-10m-1772119023.json`, `artifacts/worker-a-10m/iteration-42/bl18.1-remote-stability-local-worker-a-10m-1772119023.ndjson`, `artifacts/bl18.1-request-id-nonascii-fallback-worker-a-10m-1772119039.json`.
- **Serverlauf:** `artifacts/bl18.1-worker-a-10m-server-1772119023.log`, `artifacts/bl18.1-worker-a-10m-server-nonascii-1772119039.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-A-10m Iteration-42 + ASCII-Only Request-ID synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Request-ID-Regeln um ASCII-only-Guard erweitert und Nachweisführung auf Iteration 42 (`113 passed`, Smoke + 3x Stabilität + Non-ASCII-Fallback-Evidenz) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Bool-Flag-Aliasse für Echo/Stop-on-first-fail + Real-Run, Iteration 41)
- **`scripts/run_remote_api_smoketest.sh`:** `SMOKE_ENFORCE_REQUEST_ID_ECHO` akzeptiert jetzt zusätzlich boolesche Alias-Werte (`true|false|yes|no|on|off`, case-insensitive), normalisiert robust auf `1|0` und bleibt bei ungültigen Modi fail-fast (`exit 2`).
- **`scripts/run_remote_api_stability_check.sh`:** `STABILITY_STOP_ON_FIRST_FAIL` akzeptiert jetzt ebenfalls boolesche Alias-Werte (`true|false|yes|no|on|off`), normalisiert auf `0|1` und behält den bisherigen Early-Stop-Mechanismus unverändert bei.
- **`tests/test_remote_smoke_script.py`:** neuer Happy-Path verifiziert reproduzierbar den booleschen Echo-Flag-Alias (`SMOKE_ENFORCE_REQUEST_ID_ECHO="  fAlSe  "`) inkl. Artefaktfeld `request_id_echo_enforced=false`.
- **`tests/test_remote_stability_script.py`:** neue E2E-Abdeckung sichert boolesche Stop-Flag-Aliasse (`"  TrUe  "`/`"  fAlSe  "`) reproduzierbar ab (Early-Stop nur bei `true`).
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`111 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) mit booleschen Alias-Flags (`SMOKE_ENFORCE_REQUEST_ID_ECHO="TrUe"` im Smoke; `SMOKE_ENFORCE_REQUEST_ID_ECHO="FaLsE"` + `STABILITY_STOP_ON_FIRST_FAIL="fAlSe"` in Stabilität).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772118464.json`, `artifacts/worker-1-10m/iteration-41/bl18.1-remote-stability-local-worker-1-10m-1772118464.ndjson`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772118464.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-41 + Bool-Flag-Aliasse synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Flag-Dokumentation für `SMOKE_ENFORCE_REQUEST_ID_ECHO` und `STABILITY_STOP_ON_FIRST_FAIL` auf Alias-Support (`0|1|true|false|yes|no|on|off`) erweitert und Nachweisführung auf Iteration 41 (`111 passed`, Smoke + 3x Stabilität, `request_id_echo_enforced=true/false`) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Short-Alias-Support für `SMOKE_REQUEST_ID_HEADER` + Real-Run, Iteration 40)
- **`scripts/run_remote_api_smoketest.sh`:** `SMOKE_REQUEST_ID_HEADER` akzeptiert zusätzlich kompakte Alias-Werte (`request-id`, `correlation-id`, `request_id`, `correlation_id`) und mappt diese deterministisch auf die real gesendeten Header (`X-Request-Id`/`X-Correlation-Id` bzw. `X_Request_Id`/`X_Correlation_Id`).
- **`tests/test_remote_smoke_script.py`:** neue Happy-Path-Tests verifizieren reproduzierbar, dass `request-id` und `correlation_id` robust normalisiert werden und die erwarteten Header-Namen (`request_id_header_name`) im Smoke-Report auftauchen.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`108 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) mit Short-Aliasen (`SMOKE_REQUEST_ID_HEADER="request-id"` im Smoke, `"correlation_id"` in Stabilität).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772117788.json`, `artifacts/worker-1-10m/iteration-40/bl18.1-remote-stability-local-worker-1-10m-1772117788.ndjson`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772117788.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-40 + Short-Alias-Support synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** erlaubte `SMOKE_REQUEST_ID_HEADER`-Werte um Short-Aliasse (`request-id|correlation-id|request_id|correlation_id`) erweitert und Nachweisführung auf Iteration 40 (`108 passed`, Smoke + 3x Stabilität, `request_id_header_name=X-Request-Id` + `X_Correlation_Id`) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Request-ID-Delimiter-Guard + Real-Run, Iteration 39)
- **`src/web_service.py`:** Request-ID-Sanitizer verwirft jetzt zusätzlich Header-Werte mit Trennzeichen `,`/`;`, damit aggregierte/mehrdeutige IDs nicht als gültige Korrelations-ID gespiegelt werden.
- **`scripts/run_remote_api_smoketest.sh`:** `SMOKE_REQUEST_ID` wird fail-fast auch auf Trennzeichen `,`/`;` geprüft (`exit 2` + klare CLI-Meldung).
- **`tests/test_web_e2e.py`:** neuer API-E2E-Fall verifiziert reproduzierbar den Correlation-Fallback bei `X-Request-Id` mit Trennzeichen.
- **`tests/test_remote_smoke_script.py`:** neuer Negativtest deckt fail-fast für `SMOKE_REQUEST_ID` mit Trennzeichen ab.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`106 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) im getrimmten `request`-Header-Mode (`SMOKE_REQUEST_ID_HEADER="request"`, `SMOKE_MODE="RiSk"`).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772117243.json`, `artifacts/worker-1-10m/iteration-39/bl18.1-remote-stability-local-worker-1-10m-1772117243.ndjson`, `artifacts/bl18.1-request-id-delimiter-fallback-worker-1-10m-1772117243.json`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772117243.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-39 + Delimiter-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Request-ID-Regeln um Trennzeichen-Guards (`,`/`;`) erweitert und Nachweisführung auf Iteration 39 (`106 passed`, Smoke + 3x Stabilität + delimiter-fallback real check) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m lowercase `_`-Request-Alias E2E-Abdeckung + Real-Run, Iteration 38)
- **`tests/test_remote_smoke_script.py`:** Happy-Path-Abdeckung ergänzt, dass `SMOKE_REQUEST_ID_HEADER="x_request_id"` (lowercase + getrimmt) robust akzeptiert, als Request-Mode normalisiert und real als `X_Request_Id` gesendet wird (`request_id_header_name=X_Request_Id`).
- **`tests/test_web_e2e.py`:** neuer API-E2E-Fall verifiziert, dass auch ein lowercase Unterstrich-Primärheader (`x_request_id`) für `/analyze` korrekt akzeptiert und in Header+JSON gespiegelt wird.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`104 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) mit getrimmtem lowercase `_`-Request-Alias (`SMOKE_REQUEST_ID_HEADER="x_request_id"`) und getrimmtem `SMOKE_MODE="RiSk"`.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772116556.json`, `artifacts/worker-1-10m/iteration-38/bl18.1-remote-stability-local-worker-1-10m-1772116556.ndjson`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772116556.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-1-10m Iteration-38 + lowercase `_`-Request-Nachweis synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Nachweisführung auf Iteration 38 angehoben (`104 passed`, Smoke + 3x Stabilität), inklusive explizitem Real-Run-Nachweis für `SMOKE_REQUEST_ID_HEADER="x_request_id"` (`request_id_header_name=X_Request_Id`).

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m lowercase `_`-Correlation-Alias + invalides `_`-Primärheader-Fallback, Iteration 37)
- **`tests/test_remote_smoke_script.py`:** Happy-Path-Abdeckung ergänzt, dass `SMOKE_REQUEST_ID_HEADER="x_correlation_id"` (lowercase + getrimmt) robust akzeptiert, als Correlation-Mode normalisiert und real als `X_Correlation_Id` gesendet wird (`request_id_header_name=X_Correlation_Id`).
- **`tests/test_web_e2e.py`:** neuer API-E2E-Fall verifiziert die Fallback-Kette explizit, wenn sowohl `X-Request-Id` als auch `X_Request_Id` ungültig sind (z. B. embedded-whitespace/control-char) und danach deterministisch `X-Correlation-Id` gewinnt.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`102 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) mit getrimmtem lowercase `_`-Correlation-Alias (`SMOKE_REQUEST_ID_HEADER="x_correlation_id"`) und gemischt geschriebenem `SMOKE_MODE="ExTenDeD"`.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772115947.json`, `artifacts/worker-1-10m/iteration-37/bl18.1-remote-stability-local-worker-1-10m-1772115947.ndjson`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772115947.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-1-10m Iteration-37 + lowercase `_`-Correlation-Nachweis synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Nachweisführung auf Iteration 37 angehoben (`102 passed`, Smoke + 3x Stabilität), inklusive explizitem Real-Run-Nachweis für `SMOKE_REQUEST_ID_HEADER="x_correlation_id"` (`request_id_header_name=X_Correlation_Id`) und dokumentierter API-Fallback-Kette bei ungültigen primären Request-ID-Headern.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m lowercase `_`-Header-Alias-Real-Run, Iteration 36)
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`100 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) mit getrimmtem lowercase `_`-Header-Alias (`SMOKE_REQUEST_ID_HEADER="x_request_id"`) und gemischt geschriebenem `SMOKE_MODE="BaSiC"`.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772115249.json`, `artifacts/worker-1-10m/iteration-36/bl18.1-remote-stability-local-worker-1-10m-1772115249.ndjson`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772115249.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-1-10m Iteration-36 + lowercase `_`-Alias-Nachweis synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Nachweisführung auf Iteration 36 angehoben (`100 passed`, Smoke + 3x Stabilität) und explizit um den real gesendeten lowercase `_`-Alias (`request_id_header_name=X_Request_Id`) ergänzt.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Primärheader-Priorität + Correlation-`_`-Real-Run, Iteration 35)
- **`tests/test_web_e2e.py`:** neuer API-E2E-Fall verifiziert die Request-ID-Priorität explizit: ist `X-Request-Id` ungültig, aber `X_Request_Id` gültig, wird deterministisch `X_Request_Id` gespiegelt (vor Correlation-Fallback).
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`100 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) im `_`-Correlation-Header-Mode (`SMOKE_REQUEST_ID_HEADER="X_Correlation_Id"`).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772114701.json`, `artifacts/worker-1-10m/iteration-35/bl18.1-remote-stability-local-worker-1-10m-1772114701.ndjson`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772114701.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-1-10m Iteration-35 + Primärheader-Priorität synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** API-Verhalten und Nachweisführung um die Primärheader-Priorität (`X_Request_Id` vor Correlation bei ungültigem `X-Request-Id`) ergänzt; Real-Run-/Repro-Nachweise auf Iteration 35 (`100 passed`, Smoke + 3x Stabilität, `request_id_header_name=X_Correlation_Id`) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m echte `_`-Request-ID-Header + 3x Stabilität, Iteration 34)
- **`src/web_service.py`:** akzeptiert Request-ID-Header jetzt robust sowohl in `-`- als auch `_`-Notation (`X-Request-Id`/`X_Request_Id`, `X-Correlation-Id`/`X_Correlation_Id`) und behält die bisherige Fallback-Logik + Sanitizer-Grenzen (keine Whitespaces/Control-Chars, max. 128) bei.
- **`scripts/run_remote_api_smoketest.sh`:** `SMOKE_REQUEST_ID_HEADER`-Alias-Mapping erweitert: bei `_`-Aliasen werden die Header nun real als `X_Request_Id`/`X_Correlation_Id` gesendet statt nur intern zu normalisieren; der Smoke-Report enthält dafür das neue Feld `request_id_header_name`.
- **`tests/test_web_e2e.py`:** neue API-E2E-Fälle sichern `_`-Header-Support reproduzierbar ab (primärer `X_Request_Id`-Happy-Path + Fallback auf `X_Correlation_Id`).
- **`tests/test_remote_smoke_script.py`:** Assert-Abdeckung erweitert, sodass für alle Header-Modi auch das tatsächlich gesendete Header-Feld (`request_id_header_name`) verifiziert wird.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`99 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) mit real gesendetem `_`-Header (`SMOKE_REQUEST_ID_HEADER="X_Request_Id"`).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772114297.json`, `artifacts/worker-1-10m/iteration-34/bl18.1-remote-stability-local-worker-1-10m-1772114297.ndjson`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772114297.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-34 + echte `_`-Header-Sendung synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Request-ID-Dokumentation auf `_`-Header-Support im Service aktualisiert, Smoke-Option `SMOKE_REQUEST_ID_HEADER` bzgl. real gesendeter `_`-Header präzisiert und Nachweisführung auf Iteration 34 (`99 passed`, Smoke + 3x Stabilität, `request_id_header_name=X_Request_Id`) synchronisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A case-insensitive `intelligence_mode` + 3x Stabilität, Iteration 33)
- **`src/web_service.py`:** normalisiert `intelligence_mode` jetzt API-seitig mit `strip()+lower()`, sodass robuste Client-Eingaben wie `"  ExTenDeD  "` konsistent als `extended` verarbeitet werden.
- **`tests/test_web_e2e.py`:** neuer E2E-Happy-Path verifiziert reproduzierbar, dass gemischter/case-insensitiver `intelligence_mode` (`"  ExTenDeD  "`) erfolgreich akzeptiert wird.
- **Langlauf-Real-Run (Worker A):** `./scripts/run_webservice_e2e.sh` erfolgreich (`97 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) im `correlation`-Header-Mode mit `SMOKE_MODE="ExTenDeD"`.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-a-1772113545.json`, `artifacts/worker-a/iteration-33/bl18.1-remote-stability-local-worker-a-1772113545.ndjson`.
- **Serverlauf:** `artifacts/bl18.1-worker-a-server-1772113545.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-A Iteration-33 + case-insensitive `intelligence_mode` synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** API-Verhalten für `intelligence_mode` (Trim + case-insensitive), BL-18.1-Nachweisführung und aktuelle Langlauf-Evidenz auf Worker-A Iteration 33 (`97 passed`, Smoke + 3x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Fail-fast-Guards für `SMOKE_REQUEST_ID_HEADER` (whitespace/control) + 5x Stabilität, Iteration 32)
- **`scripts/run_remote_api_smoketest.sh`:** validiert `SMOKE_REQUEST_ID_HEADER` jetzt vor der Alias-Normalisierung zusätzlich auf whitespace-only, eingebettete Whitespaces und Steuerzeichen; Fehlwerte brechen deterministisch mit klarer CLI-Meldung + `exit 2` ab.
- **`tests/test_remote_smoke_script.py`:** neue Negativtests sichern reproduzierbar ab, dass `SMOKE_REQUEST_ID_HEADER` bei whitespace-only, embedded-whitespace und Control-Char-Inputs fail-fast zurückgewiesen wird.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`96 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) mit Alias-Headern (`X_Request_Id`/`X_Correlation_Id`).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772112911.json`, `artifacts/worker-1-10m/iteration-32/bl18.1-remote-stability-local-worker-1-10m-1772112911.ndjson`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772112911.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-32 + Header-Mode-Guards synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Guard-Regeln und BL-18.1-Nachweisführung auf die neuen `SMOKE_REQUEST_ID_HEADER`-Fail-fast-Checks (whitespace/control) sowie den aktuellen Worker-1-10m-Langlauf (`96 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Unterstrich-Header-Aliasse für `SMOKE_REQUEST_ID_HEADER` + 5x Stabilität, Iteration 31)
- **`tests/test_remote_smoke_script.py`:** Happy-Path-Abdeckung um Unterstrich-Aliasse erweitert (`"  X_Request_Id  "`, `"\tX_Correlation_Id\t"`) und damit den bereits dokumentierten Alias-Support (`x_request_id`/`x_correlation_id`) reproduzierbar abgesichert.
- **`scripts/run_remote_api_smoketest.sh`:** CLI-Hinweise für `SMOKE_REQUEST_ID_HEADER` präzisiert; erlaubte Werte in Hilfe-/Fehlermeldung listen jetzt explizit auch `x_request_id|x_correlation_id`.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`93 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) mit Unterstrich-Header-Aliasen (`X_Request_Id`/`X_Correlation_Id`).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772112297.json`, `artifacts/worker-1-10m/iteration-31/bl18.1-remote-stability-local-worker-1-10m-1772112297.ndjson`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772112297.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-31 + Unterstrich-Header-Alias-Support synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** erlaubte `SMOKE_REQUEST_ID_HEADER`-Werte und BL-18.1-Nachweisführung auf Unterstrich-Aliasse (`x_request_id|x_correlation_id`) sowie den aktuellen Worker-1-10m-Langlauf (`93 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Header-Alias-Normalisierung für `SMOKE_REQUEST_ID_HEADER` + 5x Stabilität, Iteration 30)
- **`scripts/run_remote_api_smoketest.sh`:** akzeptiert für `SMOKE_REQUEST_ID_HEADER` jetzt zusätzlich Header-Namen als Alias (`x-request-id`/`x-correlation-id`, inkl. `_`-Varianten) und normalisiert diese robust auf die internen Modi `request|correlation`.
- **`tests/test_remote_smoke_script.py`:** Happy-Path-Abdeckung um Alias-Eingaben (`"  X-Request-Id  "`, `"\tX-Correlation-Id\t"`) erweitert; der Negativtest bleibt bestehen und validiert weiterhin fail-fast bei unbekannten Modi.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`91 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) mit aliasbasiertem Header-Mode (`X-Request-Id`/`X-Correlation-Id`).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772111763.json`, `artifacts/worker-1-10m/iteration-30/bl18.1-remote-stability-local-worker-1-10m-1772111763.ndjson`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772111763.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-30 + Header-Alias-Support synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, erlaubte `SMOKE_REQUEST_ID_HEADER`-Werte und Nachweisführung auf Header-Alias-Normalisierung sowie den aktuellen Worker-1-10m-Langlauf (`91 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m API-Guard für `X-Request-Id`-Überlänge + 5x Stabilität, Iteration 29)
- **`src/web_service.py`:** Request-ID-Sanitizer verwirft jetzt Header-IDs mit mehr als 128 Zeichen statt sie still zu kürzen; damit bleibt die gespiegelt ausgegebene ID token-stabil und fällt bei Überlänge deterministisch auf die nächste gültige Kandidaten-ID zurück.
- **`tests/test_web_e2e.py`:** neuer API-E2E-Fall verifiziert reproduzierbar den Fallback auf `X-Correlation-Id`, wenn `X-Request-Id` 129 Zeichen lang ist.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`89 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`).
- **API-Guard real verifiziert:** `/analyze` verwirft `X-Request-Id` mit Überlänge (`129`) deterministisch und spiegelt stattdessen `X-Correlation-Id` konsistent in Response-Header + JSON.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772111118.json`, `artifacts/worker-1-10m/iteration-29/bl18.1-remote-stability-local-worker-1-10m-1772111118.ndjson`, `artifacts/bl18.1-request-id-length-fallback-worker-1-10m-1772111118.json`.
- **Serverlauf:** `artifacts/bl18.1-worker-1-10m-server-1772111118.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-29 + Request-ID-Längen-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Request-ID-Regeln und Nachweisführung um den neuen Überlängen-Guard (`>128`) sowie den aktuellen Worker-1-10m-Langlauf (`89 passed`, Smoke + 5x Stabilität + realer Fallback-Check) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m API-Guard für eingebetteten Whitespace in `X-Request-Id` + 5x Stabilität, Iteration 28)
- **`src/web_service.py`:** Request-ID-Sanitizer verwirft jetzt zusätzlich Header-IDs mit eingebettetem Whitespace (`X-Request-Id`/`X-Correlation-Id`), damit nur token-stabile Korrelations-IDs gespiegelt werden.
- **`tests/test_web_e2e.py`:** neuer API-E2E-Fall verifiziert reproduzierbar den Fallback auf `X-Correlation-Id`, wenn `X-Request-Id` eingebetteten Whitespace enthält (`"bl18 bad-id"`).
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`88 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`).
- **API-Guard real verifiziert:** `/analyze` verwirft `X-Request-Id: "bl18 bad-id"` deterministisch und spiegelt `X-Correlation-Id` konsistent in Response-Header + JSON.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772110559.json`, `artifacts/worker-1-10m/iteration-28/bl18.1-remote-stability-local-worker-1-10m-1772110559.ndjson`, `artifacts/bl18.1-request-id-fallback-worker-1-10m-1772110577.json`.
- **Serverläufe:** `artifacts/bl18.1-worker-1-10m-server-1772110559.log`, `artifacts/bl18.1-worker-1-10m-requestid-server-1772110577.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-28 + Request-ID-Whitespace-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Request-ID-Regeln und Nachweisführung auf den neuen Embedded-Whitespace-Guard sowie den aktuellen Worker-1-10m-Langlauf (`88 passed`, Smoke + 5x Stabilität + realer Fallback-Check) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Auto-Mkdir für fehlende `STABILITY_REPORT_PATH`-Verzeichnisse + 5x Stabilität, Iteration 27)
- **`scripts/run_remote_api_stability_check.sh`:** akzeptiert `STABILITY_REPORT_PATH` jetzt auch dann, wenn Verzeichnis-Elternpfade noch nicht existieren; fehlende Verzeichnisse werden robust via `mkdir -p` angelegt. Der Fail-Fast-Guard bleibt für Verzeichnisziele und Datei-Elternpfade (`Parent` existiert, aber ist kein Verzeichnis) aktiv.
- **`tests/test_remote_stability_script.py`:** neuer Happy-Path-Test verifiziert reproduzierbar, dass fehlende Elternverzeichnisse für `STABILITY_REPORT_PATH` automatisch erstellt werden und der NDJSON-Report erfolgreich geschrieben wird.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`86 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) mit neuem verschachteltem Reportpfad.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772109315.json`, `artifacts/worker-1-10m/iteration-27/bl18.1-remote-stability-local-worker-1-10m-1772109315.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log unter `artifacts/bl18.1-worker-1-10m-server-1772109315.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-27 + Auto-Mkdir für `STABILITY_REPORT_PATH` synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Stabilitäts-Runbook, Bedienhinweise und BL-18.1-Nachweisführung auf Auto-Mkdir für fehlende `STABILITY_REPORT_PATH`-Verzeichnis-Elternpfade sowie den aktuellen Worker-1-10m-Langlauf (`86 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Datei-Elternpfad-Guard für `STABILITY_REPORT_PATH` + 5x Stabilität, Iteration 26)
- **`scripts/run_remote_api_stability_check.sh`:** validiert `STABILITY_REPORT_PATH` jetzt zusätzlich auf einen gültigen Elternpfad; liegt der Parent als Datei statt Verzeichnis vor, bricht der Runner fail-fast mit klarer CLI-Fehlermeldung + `exit 2` ab, statt erst beim `mkdir -p`/Report-Write mit Shell-Fehler zu scheitern.
- **`tests/test_remote_stability_script.py`:** neuer Guard-Test verifiziert reproduzierbar, dass ein `STABILITY_REPORT_PATH` unterhalb eines Datei-Elternpfads deterministisch mit `exit 2` zurückgewiesen wird.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`85 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772108666.json`, `artifacts/bl18.1-remote-stability-local-worker-1-10m-1772108666.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log unter `artifacts/bl18.1-worker-1-10m-server-1772108666.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-26 + `STABILITY_REPORT_PATH`-Datei-Elternpfad-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Stabilitäts-Runbook, Negativfall-Abdeckung und BL-18.1-Nachweisführung auf den neuen Datei-Elternpfad-Guard für `STABILITY_REPORT_PATH` sowie den aktuellen Worker-1-10m-Langlauf (`85 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Datei-Elternpfad-Guard für `SMOKE_OUTPUT_JSON` + 5x Stabilität, Iteration 25)
- **`scripts/run_remote_api_smoketest.sh`:** prüft `SMOKE_OUTPUT_JSON` jetzt zusätzlich auf einen gültigen Elternpfad; existiert der Parent bereits als Datei (statt Verzeichnis), bricht der Runner fail-fast mit klarer CLI-Fehlermeldung + `exit 2` ab, statt später beim `mkdir`/Write mit Laufzeitfehler zu scheitern.
- **`tests/test_remote_smoke_script.py`:** neuer Guard-Test verifiziert reproduzierbar, dass ein `SMOKE_OUTPUT_JSON`-Ziel unterhalb eines Datei-Elternpfads deterministisch mit `exit 2` zurückgewiesen wird.
- **Langlauf-Real-Run (Worker A):** `./scripts/run_webservice_e2e.sh` erfolgreich (`84 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-a-1772108086.json`, `artifacts/bl18.1-remote-stability-local-worker-a-1772108086.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log unter `artifacts/bl18.1-worker-a-server-1772108086.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-A Iteration-25 + `SMOKE_OUTPUT_JSON`-Datei-Elternpfad-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Negativfall-Abdeckung und BL-18.1-Nachweisführung auf den neuen Datei-Elternpfad-Guard für `SMOKE_OUTPUT_JSON` sowie den aktuellen Worker-A-Langlauf (`84 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Verzeichnis-Guard für `SMOKE_OUTPUT_JSON` + 5x Stabilität, Iteration 24)
- **`scripts/run_remote_api_smoketest.sh`:** validiert `SMOKE_OUTPUT_JSON` jetzt zusätzlich auf Verzeichnisziele (`-d`) und bricht mit klarer CLI-Fehlermeldung + `exit 2` ab, statt erst beim JSON-Write mit einem Laufzeitfehler zu scheitern.
- **`tests/test_remote_smoke_script.py`:** neuer Guard-Test verifiziert reproduzierbar, dass ein existierendes Verzeichnis als `SMOKE_OUTPUT_JSON` deterministisch mit `exit 2` zurückgewiesen wird.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`83 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772107493.json`, `artifacts/bl18.1-remote-stability-local-worker-1-10m-1772107493.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log unter `artifacts/bl18.1-worker-1-10m-server-1772107493.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-24 + `SMOKE_OUTPUT_JSON`-Verzeichnis-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise und BL-18.1-Nachweisführung auf den neuen Verzeichnis-Guard für `SMOKE_OUTPUT_JSON` sowie den aktuellen Worker-1-10m-Langlauf (`83 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Verzeichnis-Guard für `STABILITY_REPORT_PATH` + 5x Stabilität, Iteration 23)
- **`scripts/run_remote_api_stability_check.sh`:** prüft `STABILITY_REPORT_PATH` jetzt vor dem Schreiben explizit auf Verzeichnisziele (`-d`) und bricht mit klarer CLI-Fehlermeldung + `exit 2` ab, statt erst beim Redirect/Truncate mit einem Shell-Fehler zu scheitern.
- **`tests/test_remote_stability_script.py`:** neuer Guard-Test verifiziert reproduzierbar, dass ein existierendes Verzeichnis als `STABILITY_REPORT_PATH` deterministisch mit `exit 2` zurückgewiesen wird.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`82 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772106884.json`, `artifacts/bl18.1-remote-stability-local-worker-1-10m-1772106884.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log unter `artifacts/bl18.1-worker-1-10m-server-1772106884.log`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/README auf Verzeichnis-Guard für `STABILITY_REPORT_PATH` synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md`:** Stabilitäts-Runbook um den neuen Verzeichnis-Guard für `STABILITY_REPORT_PATH` ergänzt und Nachweisführung auf Worker-1-10m Iteration 23 (`82 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m REPO_ROOT-Resolve + File-Guard für `STABILITY_SMOKE_SCRIPT` + 5x Stabilität, Iteration 22)
- **`scripts/run_remote_api_stability_check.sh`:** `STABILITY_SMOKE_SCRIPT` wird nach Trim jetzt robust aufgelöst (relative Overrides werden gegen `REPO_ROOT` normalisiert) und strikt als **ausführbare Datei** validiert (`-f` + `-x`), damit Starts aus fremdem `cwd` reproduzierbar funktionieren und Verzeichnis-Pfade fail-fast mit `exit 2` scheitern.
- **`tests/test_remote_stability_script.py`:** zwei neue Guard-/Happy-Path-Tests decken reproduzierbar ab: (1) relativer Override `./scripts/run_remote_api_smoketest.sh` funktioniert auch bei Lauf aus fremdem `cwd`, (2) Override auf ein Verzeichnis wird klar mit `exit 2` abgewiesen.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`81 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) mit tab-umhülltem, relativem `STABILITY_SMOKE_SCRIPT`-Override aus fremdem `cwd`.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772106342.json`, `artifacts/bl18.1-remote-stability-local-worker-1-10m-1772106342.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-1-10m-server-1772106342.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-22 + `STABILITY_SMOKE_SCRIPT`-Resolve/File-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md`:** Stabilitäts-Runbook, Bedienhinweise und BL-18.1-Nachweisführung auf REPO_ROOT-Resolve + File-Guard für `STABILITY_SMOKE_SCRIPT` sowie den aktuellen Worker-1-10m-Langlauf (`81 passed`, Smoke + 5x Stabilität aus fremdem `cwd`) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Trim-/Guard für `STABILITY_SMOKE_SCRIPT` + 5x Stabilität, Iteration 21)
- **`scripts/run_remote_api_stability_check.sh`:** optionales Script-Override `STABILITY_SMOKE_SCRIPT` wird jetzt vor Nutzung getrimmt und auf Steuerzeichen geprüft; whitespace-only oder Control-Char-Overrides brechen fail-fast mit `exit 2` ab, bevor ein fehlerhafter Runner-Pfad ausgeführt wird.
- **`tests/test_remote_stability_script.py`:** drei neue Guard-Tests decken reproduzierbar ab: (1) getrimmtes `STABILITY_SMOKE_SCRIPT`-Override läuft erfolgreich, (2) whitespace-only Override scheitert mit `exit 2`, (3) Control-Char-Override scheitert mit `exit 2`.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`79 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) mit getrimmtem optionalen Bearer-Token (`printf '  bl18-token\t'`) und tab-umhülltem `STABILITY_SMOKE_SCRIPT`-Override (`printf '  ./scripts/run_remote_api_smoketest.sh\t'`).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772105805.json`, `artifacts/bl18.1-remote-stability-local-worker-1-10m-1772105805.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-1-10m-server-1772105805.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-21 + `STABILITY_SMOKE_SCRIPT`-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Stabilitäts-Runbook, Bedienhinweise und BL-18.1-Nachweisführung auf den neuen `STABILITY_SMOKE_SCRIPT`-Trim/Fail-Fast-Guard sowie den aktuellen Worker-1-10m-Langlauf (`79 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Trim-/Guard für `STABILITY_REPORT_PATH` + 5x Stabilität, Iteration 20)
- **`scripts/run_remote_api_stability_check.sh`:** `STABILITY_REPORT_PATH` wird jetzt vor Nutzung getrimmt; whitespace-only Werte (nach Trim leer) und Pfade mit Steuerzeichen werden fail-fast mit `exit 2` abgewiesen, damit NDJSON-Artefakte reproduzierbar und log-sicher geschrieben werden.
- **`tests/test_remote_stability_script.py`:** drei neue Guard-Tests decken reproduzierbar ab: (1) getrimmter Report-Pfad wird korrekt verwendet, (2) whitespace-only `STABILITY_REPORT_PATH` schlägt mit `exit 2` fehl, (3) Control-Char-Pfade schlagen mit `exit 2` fehl.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`76 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) im getrimmten `request`-Header-Mode mit case-insensitive normalisiertem `SMOKE_MODE="  RiSk  "`, getrimmtem Token/Query und tab-umhülltem `STABILITY_REPORT_PATH`.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772105148.json`, `artifacts/bl18.1-remote-stability-local-worker-1-10m-1772105148.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-1-10m-server-1772105148.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-20 + `STABILITY_REPORT_PATH`-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Stabilitäts-Runbook-Hinweise und BL-18.1-Nachweisführung auf den neuen `STABILITY_REPORT_PATH`-Trim/Fail-Fast-Guard sowie den aktuellen Worker-1-10m-Langlauf (`76 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Whitespace-only-Guard für `SMOKE_OUTPUT_JSON` + 5x Stabilität, Iteration 19)
- **`scripts/run_remote_api_smoketest.sh`:** `SMOKE_OUTPUT_JSON` bricht jetzt zusätzlich fail-fast mit `exit 2` ab, wenn der Wert nach Trim leer wird (whitespace-only Input), statt stillschweigend die Artefaktausgabe zu deaktivieren.
- **`tests/test_remote_smoke_script.py`:** neuer Negativtest verifiziert reproduzierbar, dass whitespace-only `SMOKE_OUTPUT_JSON` mit klarer CLI-Fehlermeldung (`exit 2`) scheitert.
- **Langlauf-Real-Run (Worker A):** `./scripts/run_webservice_e2e.sh` erfolgreich (`73 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) im getrimmten `request`-Header-Mode mit kombinierter Suffix-Kette.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-a-1772104523.json`, `artifacts/bl18.1-remote-stability-local-worker-a-1772104523.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-a-server-1772104523.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-A Iteration-19 + `SMOKE_OUTPUT_JSON`-Whitespace-only-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Negativfall-Abdeckung und Nachweisführung auf den neuen whitespace-only-Guard für `SMOKE_OUTPUT_JSON` sowie den aktuellen Worker-A-Langlauf (`73 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Embedded-Whitespace-Guard für `DEV_API_AUTH_TOKEN` + 5x Stabilität, Iteration 18)
- **`scripts/run_remote_api_smoketest.sh`:** optionales `DEV_API_AUTH_TOKEN` rejectet nach dem Trim jetzt zusätzlich eingebettete Whitespaces fail-fast mit `exit 2`; dadurch bleiben Bearer-Header robust und reproduzierbar, ohne implizite Token-Splits bei fehlerhaften Env-Inputs.
- **`tests/test_remote_smoke_script.py`:** neuer Negativtest verifiziert reproduzierbar, dass `DEV_API_AUTH_TOKEN="bl18 token"` mit klarer CLI-Fehlermeldung (`exit 2`) scheitert.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`72 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) im getrimmten `request`-Header-Mode mit kombiniert normalisierter Suffix-Kette.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772103860.json`, `artifacts/bl18.1-remote-stability-local-worker-1-10m-1772103860.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-1-10m-server-1772103860.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-18 + `DEV_API_AUTH_TOKEN`-Whitespace-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Negativfall-Abdeckung und Nachweisführung auf den neuen Embedded-Whitespace-Guard für `DEV_API_AUTH_TOKEN` sowie den aktuellen Worker-1-10m-Langlauf (`72 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Control-Char-Guard für `SMOKE_OUTPUT_JSON` + 5x Stabilität, Iteration 17)
- **`scripts/run_remote_api_smoketest.sh`:** validiert `SMOKE_OUTPUT_JSON` nach dem Trim jetzt zusätzlich auf Steuerzeichen; Pfade mit Control-Chars (z. B. Zeilenumbruch) werden fail-fast mit `exit 2` abgewiesen, damit Artefaktpfade im Smoke-Runner reproduzierbar und log-sicher bleiben.
- **`tests/test_remote_smoke_script.py`:** neuer Negativtest verifiziert reproduzierbar, dass `SMOKE_OUTPUT_JSON` mit Steuerzeichen klar mit `exit 2` und eindeutiger CLI-Fehlermeldung scheitert.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`71 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) im getrimmten `request`-Header-Mode mit kombiniert normalisierter Suffix-Kette.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772103286.json`, `artifacts/bl18.1-remote-stability-local-worker-1-10m-1772103286.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-1-10m-server-1772103286.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-17 + `SMOKE_OUTPUT_JSON`-Control-Char-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Testabdeckung und Nachweisführung auf den neuen Control-Char-Guard für `SMOKE_OUTPUT_JSON` sowie den aktuellen Worker-1-10m-Langlauf (`71 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Trim-Guard für `SMOKE_OUTPUT_JSON` (inkl. Curl-Fehlpfad) + 5x Stabilität, Iteration 16)
- **`scripts/run_remote_api_smoketest.sh`:** `SMOKE_OUTPUT_JSON` wird jetzt vor der Nutzung getrimmt und dadurch in allen Pfaden konsistent verwendet (inkl. Curl-Fehlerpfad-Report), damit whitespace-umhüllte Artefaktpfade nicht in abweichende/versteckte Zielpfade schreiben.
- **`tests/test_remote_smoke_script.py`:** neuer Curl-Fehlpfad-Test verifiziert reproduzierbar, dass ein whitespace-umhüllter `SMOKE_OUTPUT_JSON`-Pfad korrekt auf den getrimmten Zielpfad schreibt (`reason=curl_error`).
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`70 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) im getrimmten `request`-Header-Mode mit kombiniert normalisierter Suffix-Kette und whitespace-umhülltem `SMOKE_OUTPUT_JSON`.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772102717.json`, `artifacts/bl18.1-remote-stability-local-worker-1-10m-1772102717.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-1-10m-server-1772102717.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-16 + `SMOKE_OUTPUT_JSON`-Trim synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Testabdeckung und Nachweisführung auf den neuen `SMOKE_OUTPUT_JSON`-Trim-Guard sowie den aktuellen Worker-1-10m-Langlauf (`70 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Embedded-Whitespace-Guard für `SMOKE_REQUEST_ID` + 5x Stabilität, Iteration 15)
- **`scripts/run_remote_api_smoketest.sh`:** `SMOKE_REQUEST_ID` rejectet jetzt zusätzlich eingebettete Whitespaces fail-fast mit `exit 2`; dadurch bleiben Request-Header/Trace-IDs reproduzierbar ohne implizite Header-Normalisierung durch Clients/Proxies.
- **`tests/test_remote_smoke_script.py`:** neuer Negativtest verifiziert reproduzierbar, dass `SMOKE_REQUEST_ID` mit eingebettetem Whitespace (`"bl18 bad-request-id"`) klar mit `exit 2` und eindeutiger CLI-Fehlermeldung fehlschlägt.
- **Langlauf-Real-Run (Worker A):** `./scripts/run_webservice_e2e.sh` erfolgreich (`69 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) im getrimmten `request`-Header-Mode mit kombinierter Suffix-Kette.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-a-1772102261.json`, `artifacts/bl18.1-remote-stability-local-worker-a-1772102261.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-a-server-1772102261.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-A Iteration-15 + `SMOKE_REQUEST_ID`-Whitespace-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Negativfall-Abdeckung und Nachweisführung auf den neuen Embedded-Whitespace-Guard für `SMOKE_REQUEST_ID` sowie den aktuellen Worker-A-Langlauf (`69 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Control-Char-Guard für `SMOKE_QUERY` + 5x Stabilität, Iteration 14)
- **`scripts/run_remote_api_smoketest.sh`:** `SMOKE_QUERY` wird nach dem Trim jetzt zusätzlich auf Steuerzeichen validiert; Control-Char-Queries werden fail-fast mit `exit 2` abgewiesen, bevor ein Request gesendet wird.
- **`tests/test_remote_smoke_script.py`:** ergänzt einen neuen Negativtest für `SMOKE_QUERY` mit Steuerzeichen (z. B. Zeilenumbruch), damit Fehlkonfigurationen reproduzierbar als `exit 2` sichtbar werden.
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`68 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) im getrimmten `request`-Header-Mode mit kombinierter Suffix-Kette.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772101465.json`, `artifacts/bl18.1-remote-stability-local-worker-1-10m-1772101465.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-1-10m-server-1772101465.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-14 + `SMOKE_QUERY`-Control-Char-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Testabdeckung und Nachweisführung auf den neuen `SMOKE_QUERY`-Control-Char-Guard sowie den aktuellen Worker-1-10m-Langlauf (`68 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1-10m Trim-/Empty-Guard für `SMOKE_QUERY` + 5x Stabilität, Iteration 13)
- **`scripts/run_remote_api_smoketest.sh`:** `SMOKE_QUERY` wird jetzt vor dem Request getrimmt und whitespace-only Werte werden fail-fast mit `exit 2` abgewiesen, damit Fehlkonfigurationen früh und eindeutig sichtbar sind.
- **`tests/test_remote_smoke_script.py`:** ergänzt einen Happy-Path für getrimmtes `SMOKE_QUERY="  __ok__  "` sowie einen Negativtest für whitespace-only `SMOKE_QUERY` (`exit 2`).
- **Langlauf-Real-Run (Worker 1-10m):** `./scripts/run_webservice_e2e.sh` erfolgreich (`67 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) im getrimmten `request`-Header-Mode mit getrimmtem Query-Input und kombinierter Suffix-Kette.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-10m-1772101014.json`, `artifacts/bl18.1-remote-stability-local-worker-1-10m-1772101014.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-1-10m-server-1772101014.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-1-10m Iteration-13 + `SMOKE_QUERY`-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Testabdeckung und Nachweisführung auf den neuen `SMOKE_QUERY`-Trim/Fast-Fail-Guard sowie den aktuellen Worker-1-10m-Langlauf (`67 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-B Control-Char-Guard für `DEV_API_AUTH_TOKEN` + 5x Stabilität, Iteration 12)
- **`scripts/run_remote_api_smoketest.sh`:** optionales `DEV_API_AUTH_TOKEN` wird nach dem Trim jetzt zusätzlich auf Steuerzeichen validiert; Tokens mit Control-Chars werden fail-fast mit `exit 2` abgewiesen, bevor ein Request gesendet wird.
- **`tests/test_remote_smoke_script.py`:** neuer Negativtest verifiziert reproduzierbar, dass `DEV_API_AUTH_TOKEN` mit Steuerzeichen (z. B. Zeilenumbruch im Token) sauber mit `exit 2` fehlschlägt.
- **Langlauf-Real-Run (Worker B):** `./scripts/run_webservice_e2e.sh` erfolgreich (`65 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) im getrimmten `request`-Header-Mode mit kombinierter Suffix-Kette und getrimmtem optionalen Bearer-Token.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-b-1772100694.json`, `artifacts/bl18.1-remote-stability-local-worker-b-1772100694.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-b-server-1772100694.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-B Iteration-12 + Token-Control-Char-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Testabdeckung und Nachweisführung auf den neuen Control-Char-Guard für `DEV_API_AUTH_TOKEN` sowie den aktuellen Worker-B-Langlauf (`65 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Trim-Guard für `DEV_API_AUTH_TOKEN` + 5x Stabilität, Iteration 11)
- **`scripts/run_remote_api_smoketest.sh`:** trimmt optionales `DEV_API_AUTH_TOKEN` jetzt vor dem Request; whitespace-only Tokenwerte werden fail-fast mit `exit 2` zurückgewiesen, damit Auth-Checks bei Copy/Paste-Inputs reproduzierbar bleiben.
- **`tests/test_remote_smoke_script.py`:** ergänzt E2E-Happy-Path für Space/Tab-umhülltes `DEV_API_AUTH_TOKEN` sowie Negativtest für whitespace-only Token (`exit 2`).
- **Langlauf-Real-Run (Worker A):** `./scripts/run_webservice_e2e.sh` erfolgreich (`64 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) mit getrimmtem `DEV_API_AUTH_TOKEN="  bl18-token\t"`, getrimmtem `request`-Header-Mode und kombinierter Suffix-Kette.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-a-1772100333.json`, `artifacts/bl18.1-remote-stability-local-worker-a-1772100333.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-a-server-1772100333.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-A Iteration-11 + Token-Trim synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Testabdeckung und Nachweisführung auf den neuen `DEV_API_AUTH_TOKEN`-Trim/Fast-Fail-Guard sowie den aktuellen Worker-A-Langlauf (`64 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-C WEB_PORT-Fallback + Request-Header-Mode + 5x Stabilität, Iteration 10)
- **`src/web_service.py`:** Port-Auflösung für den lokalen Service robuster gemacht (`PORT` bleibt primär; fehlt/leer → Fallback auf `WEB_PORT`).
- **`tests/test_web_e2e.py`:** zusätzlicher E2E-Test `TestWebServiceEnvPortFallback` sichert reproduzierbar ab, dass der Service via `WEB_PORT` startet, wenn `PORT` nicht gesetzt ist.
- **Langlauf-Real-Run (Worker C):** `./scripts/run_webservice_e2e.sh` erfolgreich (`62 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) im getrimmten `request`-Header-Mode mit case-insensitive `SMOKE_MODE="  RiSk  "` und kombinierter Suffix-Kette.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-c-1772099864.json`, `artifacts/bl18.1-remote-stability-local-worker-c-1772099864.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-c-server-1772099864.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-C Iteration-10 + WEB_PORT-Fallback synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Runbook-Nachweis und Backlog-Status auf den aktuellen Worker-C-Langlauf (`62 passed`, Smoke + 5x Stabilität) sowie die `WEB_PORT`-Fallback-Kompatibilität synchronisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Langlauf-Recheck mit Tab-Trim + kombinierter Suffix-Kette, Iteration 9)
- **Langlauf-Real-Run (Worker A):** `./scripts/run_webservice_e2e.sh` erfolgreich (`61 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=5`, `fail=0`, Exit `0`) bei Tab-umhüllter Base-URL/Header-/Flag-Eingabe und kombinierter Suffix-Kette (`.../AnAlYzE//health/analyze/health/analyze///`).
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-a-1772099418.json`, `artifacts/bl18.1-remote-stability-local-worker-a-1772099418.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-service-worker-a-1772099418.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-A Iteration-9-Nachweis synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Command/Exit/Evidenz auf den aktuellen Worker-A-Langlauf (`61 passed`, Smoke + 5x Stabilität) mit Tab-getrimmten Inputs und kombinierter Suffix-Kette aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-B case-insensitive `SMOKE_MODE` + 5x Stabilität, Iteration 8)
- **`scripts/run_remote_api_smoketest.sh`:** normalisiert `SMOKE_MODE` nach dem Trim jetzt zusätzlich case-insensitive (`"  ExTenDeD  "` → `extended`), damit robuste Env-Inputs bei manuellen Runbook-Aufrufen reproduzierbar akzeptiert werden.
- **`tests/test_remote_smoke_script.py`:** neuer E2E-Happy-Path verifiziert reproduzierbar, dass gemischt geschriebene `SMOKE_MODE`-Werte erfolgreich verarbeitet werden.
- **Langlauf-Real-Run (Worker B):** `./scripts/run_webservice_e2e.sh` erfolgreich (`61 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` im getrimmten Correlation-Mode erfolgreich (`pass=5`, `fail=0`, Exit `0`) trotz gemischt geschriebenem `SMOKE_MODE="  ExTenDeD  "`.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-b-langlauf-1772099150.json`, `artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772099150.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-b-server-1772099150.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf case-insensitive `SMOKE_MODE` synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Testabdeckung und Nachweisführung auf case-insensitive `SMOKE_MODE`-Normalisierung sowie den aktuellen Worker-B-Langlauf (`61 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-C Request-ID-Control-Char-Fallback + 5x Stabilität, Iteration 7)
- **`tests/test_web_e2e.py`:** neuer API-E2E-Guard verifiziert reproduzierbar, dass `/analyze` bei `X-Request-Id` mit Steuerzeichen (z. B. Tab) deterministisch auf `X-Correlation-Id` zurückfällt und die Fallback-ID konsistent in Header+JSON spiegelt.
- **Langlauf-Real-Run (Worker C):** `./scripts/run_webservice_e2e.sh` erfolgreich (`60 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` im getrimmten Correlation-Mode erfolgreich (`pass=5`, `fail=0`, Exit `0`) mit getrimmten Timeout-/Retry-/Stability-Flags.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-c-langlauf-1772098788.json`, `artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772098788.ndjson`, `artifacts/bl18.1-request-id-control-fallback-worker-c-1772098788.json`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-c-server-1772098788.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Request-ID-Validierung auf "erste gültige ID" gehärtet)
- **`src/web_service.py`:** Request-ID-Auswahl für `/analyze` verwirft jetzt Header-IDs mit Steuerzeichen (zusätzlich zu leer/whitespace-only) und fällt dann deterministisch auf `X-Correlation-Id` bzw. interne ID zurück; verhindert instabile Echo-Werte bei fehlerhaften Header-Inputs.
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Runbook-/Backlog-Nachweis auf den neuen Control-Char-Fallback-Guard sowie den aktuellen Worker-C-Langlauf (`60 passed`, Smoke + 5x Stabilität) synchronisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1 Trim-Recheck für Timeout-Inputs + 5x Stabilität, Iteration 6)
- **`tests/test_remote_smoke_script.py`:** neuer E2E-Happy-Path verifiziert reproduzierbar, dass getrimmte Timeout-Inputs (`SMOKE_TIMEOUT_SECONDS="\t2.5\t"`, `CURL_MAX_TIME=" 15 "`) im dedizierten BL-18.1-Smoke-Runner robust akzeptiert werden.
- **Langlauf-Real-Run (Worker 1):** `./scripts/run_webservice_e2e.sh` erfolgreich (`59 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` im getrimmten Correlation-Mode erfolgreich (`pass=5`, `fail=0`, Exit `0`) trotz absichtlich Space-umhüllter Timeout-/Retry-Flags.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-1-langlauf-1772098485.json`, `artifacts/bl18.1-remote-stability-local-worker-1-langlauf-1772098485.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-1-server-1772098485.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-1 Iteration-6-Nachweis synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Testabdeckung und Nachweisführung auf getrimmte Timeout-Inputs (`SMOKE_TIMEOUT_SECONDS`, `CURL_MAX_TIME`) sowie den aktuellen Worker-1-Langlauf (`59 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-B Trim-Recheck für `SMOKE_MODE` + Retry-Flags, Iteration 5)
- **`scripts/run_remote_api_smoketest.sh`:** trimmt jetzt zusätzlich `SMOKE_MODE`, `SMOKE_TIMEOUT_SECONDS`, `CURL_MAX_TIME`, `CURL_RETRY_COUNT` und `CURL_RETRY_DELAY` vor der Validierung; robuste Env-Inputs wie `"  basic  "` oder `" 1 "` werden damit reproduzierbar akzeptiert.
- **`tests/test_remote_smoke_script.py`:** neue E2E-Happy-Paths verifizieren getrimmtes `SMOKE_MODE` sowie getrimmte Retry-Flags (`CURL_RETRY_COUNT`/`CURL_RETRY_DELAY`) gegen einen lokal gestarteten Service.
- **Langlauf-Real-Run (Worker B):** `./scripts/run_webservice_e2e.sh` erfolgreich (`58 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` im getrimmten Correlation-Mode erfolgreich (`pass=5`, `fail=0`, Exit `0`) trotz absichtlich Space-umhüllter Retry-Flags.
- **Evidenz:** `artifacts/bl18.1-smoke-local-worker-b-langlauf-1772101928.json`, `artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772101928.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-b-server-1772101928.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Worker-B Iteration-5-Nachweis synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Testabdeckung und Nachweisführung auf getrimmte `SMOKE_MODE`-/Retry-Inputs sowie den aktuellen Worker-B-Langlauf (`58 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Tab-Whitespace-Trim-Recheck + 5x Stabilität, Iteration 4)
- **`tests/test_remote_smoke_script.py`:** neuer Happy-Path verifiziert reproduzierbar, dass Tab-umhüllte Inputs (`DEV_BASE_URL="\thttp://.../health\t"`, `SMOKE_REQUEST_ID_HEADER="\tCorrelation\t"`) korrekt vor der Validierung getrimmt und im Correlation-Mode erfolgreich verarbeitet werden.
- **`tests/test_remote_stability_script.py`:** zusätzliche E2E-Abdeckung für Tab-umhüllte numerische Flags (`"\t2\t"`, `"\t0\t"`) ergänzt, damit der Trim-Guard über Space-only Inputs hinaus abgesichert ist.
- **Langlauf-Real-Run (Worker A):** `./scripts/run_webservice_e2e.sh` erfolgreich (`56 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` im getrimmten Correlation-Mode erfolgreich (`pass=5`, `fail=0`, Exit `0`) trotz Tab-umhüllter Header-/Echo-/Stability-Flags. Evidenz in `artifacts/bl18.1-smoke-local-worker-a-langlauf-1772097841.json` und `artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772097841.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-a-server-1772097841.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-A Iteration-4-Nachweis synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Testabdeckung und Nachweisführung auf Tab-Whitespace-Trim-Recheck aktualisiert (E2E `56 passed`, Smoke + 5x Stabilität mit Tab-umhüllten Inputs).

### Added (2026-02-26 — BL-18.1 Iteration: Worker-C Iteration 3 Recheck mit getrimmtem Echo-Flag + 5x Stabilität)
- **Langlauf-Real-Run (Worker C):** `./scripts/run_webservice_e2e.sh` erfolgreich (`54 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` im getrimmten Correlation-Mode erfolgreich (`pass=5`, `fail=0`, Exit `0`) bei explizit getrimmtem Echo-Flag (`SMOKE_ENFORCE_REQUEST_ID_ECHO=" 1 "`). Evidenz in `artifacts/bl18.1-smoke-local-worker-c-langlauf-1772097551.json` und `artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772097551.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-c-server-1772097551.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-C Iteration-3-Nachweis synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Command/Exit/Evidenz auf den aktuellen Worker-C-5x-Langlauf mit getrimmtem Correlation-Header-Mode, getrimmtem Echo-Flag und getrimmten Stability-Flags aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-1 Trim-Guards für Stability-Flags + 5x Stabilität)
- **`scripts/run_remote_api_stability_check.sh`:** trimmt `STABILITY_RUNS`, `STABILITY_INTERVAL_SECONDS`, `STABILITY_MAX_FAILURES` und `STABILITY_STOP_ON_FIRST_FAIL` jetzt vor der Validierung, sodass robuste Env-Inputs wie `" 5 "` bzw. `" 0 "` reproduzierbar akzeptiert werden.
- **`tests/test_remote_stability_script.py`:** neue E2E-Abdeckung sichert den Happy-Path mit getrimmten numerischen Stability-Flags (`runs/max_failures/stop_on_first_fail`) lokal gegen den gestarteten Service.
- **Langlauf-Real-Run (Worker 1):** `./scripts/run_webservice_e2e.sh` erfolgreich (`54 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` im getrimmten Correlation-Mode erfolgreich (`pass=5`, `fail=0`, Exit `0`) trotz absichtlich getrimmter numerischer Stability-Flags. Evidenz in `artifacts/bl18.1-smoke-local-worker-1-langlauf-1772097177.json` und `artifacts/bl18.1-remote-stability-local-worker-1-langlauf-1772097177.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-1-server-1772097177.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf getrimmte Stability-Flags synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Testabdeckung und Nachweisführung auf getrimmte Stability-Flags (`STABILITY_*`) sowie den aktuellen Worker-1-5x-Langlauf (`54 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-C Recheck mit getrimmtem Correlation-Mode + 5x Stabilität)
- **`scripts/run_remote_api_smoketest.sh`:** trimmt `SMOKE_REQUEST_ID_HEADER` und `SMOKE_ENFORCE_REQUEST_ID_ECHO` jetzt vor der Validierung, damit robuste Env-Inputs wie `"  Correlation  "` bzw. `" 1 "` reproduzierbar akzeptiert werden.
- **`tests/test_remote_smoke_script.py`:** neue E2E-Happy-Paths sichern die getrimmten Inputs für Header-Mode und Echo-Flag ab.
- **Langlauf-Real-Run (Worker C):** `./scripts/run_webservice_e2e.sh` erfolgreich (`53 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` im getrimmten Correlation-Mode erfolgreich (`pass=5`, `fail=0`, Exit `0`). Evidenz in `artifacts/bl18.1-smoke-local-worker-c-langlauf-1772096909.json` und `artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772096909.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-c-server-1772096909.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf getrimmte Correlation-Inputs synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Testabdeckung und Nachweisführung auf getrimmte Header-/Echo-Inputs sowie den aktuellen Worker-C-5x-Langlauf (`53 passed`, Smoke + 5x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-B Langlauf-Recheck im Correlation-Mode, 5x Stabilität)
- **Langlauf-Real-Run (Worker B):** dedizierter BL-18.1-Lauf im Correlation-Header-Mode mit robuster Suffix-Kette (`DEV_BASE_URL="  HTTP://127.0.0.1:45757/analyze//health/analyze/health///  "`) erfolgreich ausgeführt.
- **Smoke:** `run_remote_api_smoketest.sh` Exit `0`, `HTTP 200`, `ok=true`, Request-ID-Echo konsistent in Header+JSON (`request_id_header_source=correlation`), Evidenz: `artifacts/bl18.1-smoke-local-worker-b-langlauf-1772096678.json`.
- **Stabilität:** `run_remote_api_stability_check.sh` mit `STABILITY_RUNS=5` erfolgreich (`pass=5`, `fail=0`, Exit `0`), Evidenz: `artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772096678.ndjson`.
- **Serverlauf:** isolierter lokaler Service-Log für denselben Lauf unter `artifacts/bl18.1-worker-b-server-1772096678.log` dokumentiert.

### Changed (2026-02-26 — BL-18.1 Iteration: Nachweisführung auf Worker-B-5x-Langlauf synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Command/Exit/Evidenz auf den aktuellen Worker-B-Recheck mit Correlation-Header-Mode und `5x` Stabilitätslauf aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Correlation-Header-Mode im Smoke-Runner + Langlauf-Nachweis)
- **`scripts/run_remote_api_smoketest.sh`:** neuer Modus `SMOKE_REQUEST_ID_HEADER=request|correlation` (default `request`). Damit kann der BL-18.1-Smoke reproduzierbar entweder über `X-Request-Id` oder gezielt über `X-Correlation-Id` laufen; der gewählte Header-Kanal wird als `request_id_header_source` im JSON-Report ausgegeben.
- **`tests/test_remote_smoke_script.py`:** neue E2E-Abdeckung für den Correlation-Mode inkl. Fail-Fast-Guard bei ungültigen Header-Modi.
- **Langlauf-Real-Run (Worker A):** `./scripts/run_webservice_e2e.sh` erfolgreich (`51 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` im Correlation-Mode erfolgreich (`pass=3`, `fail=0`, Exit `0`). Evidenz in `artifacts/bl18.1-smoke-local-worker-a-langlauf-1772096518.json` und `artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772096518.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Correlation-Header-Mode synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** BL-18.1-Bedienhinweise, Testabdeckung und Nachweisführung auf den neuen `SMOKE_REQUEST_ID_HEADER`-Schalter + aktuellen Worker-A-Langlauf (`51 passed`, Smoke + 3x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-C Request-ID-Fallback auf `X-Correlation-Id` + Langlauf-Nachweis)
- **`src/web_service.py`:** Request-ID-Auswahl für `/analyze` nutzt jetzt deterministisch die erste **nicht-leere** Header-ID (`X-Request-Id` primär, `X-Correlation-Id` Fallback), statt bei whitespace-only `X-Request-Id` auf eine zufällige interne ID zu fallen.
- **`tests/test_web_e2e.py`:** neuer API-E2E-Guard verifiziert reproduzierbar, dass ein leeres/whitespace-only `X-Request-Id` korrekt auf `X-Correlation-Id` zurückfällt und konsistent in Header+JSON gespiegelt wird.
- **Langlauf-Real-Run (Worker C):** `./scripts/run_webservice_e2e.sh` erfolgreich (`49 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-c-langlauf-1772096264.json` und `artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772096264.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Request-ID-Fallback-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Request-Korrelationsverhalten, E2E-Testabdeckung und Nachweisführung auf den neuen Fallback-Guard (`X-Request-Id` leer → `X-Correlation-Id`) sowie den aktuellen Worker-C-Langlauf (`49 passed`, Smoke + 3x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-B Forward-Suffix-Chain mit internem Double-Slash + Langlauf-Nachweis)
- **`tests/test_remote_smoke_script.py`:** neuer E2E-Happy-Path deckt wiederholte Forward-Suffix-Ketten mit internem Double-Slash ab (`"  HTTP://.../health//analyze/health/analyze///  "`) und härtet die iterative `/health`-/`/analyze`-Normalisierung gegen zusätzliche Slash-Segmentierung in Vorwärtsrichtung.
- **Langlauf-Real-Run (Worker B):** `./scripts/run_webservice_e2e.sh` erfolgreich (`48 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-b-langlauf-1772095998.json` und `artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772095998.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Forward-Double-Slash-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Testabdeckung und Nachweisführung auf den neuen Forward-Chain-Guard (`.../health//analyze/health/analyze///`) sowie den aktuellen Worker-B-Langlauf (`48 passed`, Smoke + 3x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Embedded-Whitespace-Guard + Langlauf-Nachweis)
- **`scripts/run_remote_api_smoketest.sh`:** validiert `DEV_BASE_URL` jetzt zusätzlich auf eingebettete Whitespaces/Steuerzeichen und bricht bei fehlerhaften URL-Inputs fail-fast mit `exit 2` ab (statt späterem, weniger präzisem curl-Fehler).
- **`tests/test_remote_smoke_script.py`:** neuer Negativtest sichert reproduzierbar `exit 2` für `DEV_BASE_URL` mit eingebettetem Whitespace (`http://.../hea lth`).
- **Langlauf-Real-Run (Worker A):** `./scripts/run_webservice_e2e.sh` erfolgreich (`47 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-a-langlauf-1772095778.json` und `artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772095778.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Embedded-Whitespace-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Testabdeckung und Nachweisführung auf den neuen `DEV_BASE_URL`-Guard für eingebettete Whitespaces/Steuerzeichen sowie den aktuellen Worker-A-Langlauf (`47 passed`, Smoke + 3x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-C Request-ID-Längen-Guard + Langlauf-Nachweis)
- **`scripts/run_remote_api_smoketest.sh`:** validiert `SMOKE_REQUEST_ID` jetzt zusätzlich auf maximale Länge (`<=128` Zeichen), damit der Request-ID-Echo-Check nicht durch serverseitige Trunkierung in `src/web_service.py` fehlschlägt.
- **`tests/test_remote_smoke_script.py`:** neuer Negativtest sichert reproduzierbar `exit 2` für `SMOKE_REQUEST_ID` mit mehr als 128 Zeichen.
- **Langlauf-Real-Run (Worker C):** `./scripts/run_webservice_e2e.sh` erfolgreich (`46 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-c-langlauf-1772095524.json` und `artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772095524.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Request-ID-Längen-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Testabdeckung und Nachweisführung auf den neuen `SMOKE_REQUEST_ID<=128`-Guard + aktuellen Worker-C-Langlauf (`46 passed`, Smoke + 3x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-B Port-Validierung + Langlauf-Nachweis)
- **`tests/test_remote_smoke_script.py`:** neue Negativtests decken ungültige Ports in `DEV_BASE_URL` ab (`http://127.0.0.1:abc/health` und `http://127.0.0.1:70000/health`) und sichern reproduzierbar `exit 2` mit klarer CLI-Fehlermeldung ab.
- **Langlauf-Real-Run (Worker B):** `./scripts/run_webservice_e2e.sh` erfolgreich (`45 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-b-langlauf-1772095294.json` und `artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772095294.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Smoke-URL-Validierung auf Host/Port gehärtet)
- **`scripts/run_remote_api_smoketest.sh`:** Base-URL-Validierung prüft nach Normalisierung zusätzlich `hostname` und Port-Parsing (`parts.port`), damit nicht-numerische bzw. out-of-range Ports fail-fast mit `exit 2` abgefangen werden (statt späterem curl-Fehler).
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** BL-18.1-Runbook/Testabdeckung/Nachweisführung auf Port-Validierungs-Guard + aktuellen Worker-B-Langlauf (`45 passed`, Smoke + 3x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Userinfo-Guard + Langlauf-Nachweis)
- **`scripts/run_remote_api_smoketest.sh`:** lehnt `DEV_BASE_URL` mit Userinfo (`user:pass@host`) jetzt fail-fast mit `exit 2` ab, um unbeabsichtigte Credential-Leaks in Shell-History/Logs zu verhindern.
- **`tests/test_remote_smoke_script.py`:** neuer Negativtest stellt reproduzierbar sicher, dass Userinfo in `DEV_BASE_URL` mit sauberer CLI-Fehlermeldung zurückgewiesen wird.
- **Langlauf-Real-Run (Worker A):** `./scripts/run_webservice_e2e.sh` erfolgreich (`43 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-a-langlauf-1772095085.json` und `artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772095085.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog/README auf Userinfo-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Testabdeckung und Nachweisführung auf Userinfo-Guard + aktuellen Worker-A-Langlauf (`43 passed`, Smoke + 3x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-C Reverse-Suffix-Chain-Guard mit internem Double-Slash + Langlauf-Nachweis)
- **`tests/test_remote_smoke_script.py`:** neuer E2E-Happy-Path deckt wiederholte Reverse-Suffix-Ketten mit internem Double-Slash ab (`"  HTTP://.../AnAlYzE//health/analyze/health///  "`) und härtet die iterative `/health`-/`/analyze`-Normalisierung gegen zusätzliche Slash-Segmentierung in gemischter Reihenfolge.
- **Langlauf-Real-Run (Worker C):** `./scripts/run_webservice_e2e.sh` erfolgreich (`42 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-c-langlauf-1772094827.json` und `artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772094827.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-C Double-Slash-Langlauf synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Nachweisführung und Testabdeckung auf den aktuellen Worker-C-Langlauf (`42 passed`, Smoke + 3x Stabilität) inkl. Reverse-Suffix-Kette mit internem Double-Slash (`.../AnAlYzE//health/analyze/health///`) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-B Repeat-Reverse-Suffix-Chain-Guard + Langlauf-Nachweis)
- **`tests/test_remote_smoke_script.py`:** neuer E2E-Happy-Path deckt wiederholte Reverse-Suffix-Ketten mit Schema-Case + Whitespace ab (`"  HTTP://.../AnAlYzE/health/analyze/health///  "`) und härtet die iterative `/health`-/`/analyze`-Normalisierung gegen Regressionen in gemischter Reihenfolge.
- **Langlauf-Real-Run (Worker B):** `./scripts/run_webservice_e2e.sh` erfolgreich (`41 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-b-langlauf-1772094625.json` und `artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772094625.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-B Repeat-Reverse-Suffix-Langlauf synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Nachweisführung und Testabdeckung auf den aktuellen Worker-B-Langlauf (`41 passed`, Smoke + 3x Stabilität) inkl. wiederholter Reverse-Suffix-Kette (`.../AnAlYzE/health/analyze/health///`) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Repeat-Suffix-Chain-Guard + Langlauf-Nachweis)
- **`tests/test_remote_smoke_script.py`:** neuer E2E-Happy-Path deckt wiederholte Base-URL-Suffix-Ketten (`.../health/analyze/health/analyze///`) ab und härtet die iterative `/health`-/`/analyze`-Normalisierung gegen Regressionen.
- **Langlauf-Real-Run (Worker A):** `./scripts/run_webservice_e2e.sh` erfolgreich (`40 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-a-langlauf-1772094394.json` und `artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772094394.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-A Repeat-Suffix-Langlauf synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Testabdeckung und Nachweisführung auf den aktuellen Worker-A-Langlauf (`40 passed`, Smoke + 3x Stabilität) inkl. wiederholter Suffix-Kette (`.../health/analyze/health/analyze///`) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-C Reverse-Suffix-Ketten-Guard + Langlauf-Nachweis)
- **`tests/test_remote_smoke_script.py`:** neuer E2E-Happy-Path deckt die kombinierte Reverse-Suffix-Kette `"  HTTP://.../AnAlYzE/health//  "` ab (Schema-Case + gemischte Suffix-Reihenfolge + trailing Slashes + Whitespace in einem Lauf).
- **Langlauf-Real-Run (Worker C):** `./scripts/run_webservice_e2e.sh` erfolgreich (`39 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-c-langlauf-1772094175.json` und `artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772094175.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-C Reverse-Suffix-Langlauf synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Testabdeckung und Nachweisführung auf den aktuellen Worker-C-Langlauf (`39 passed`, Smoke + 3x Stabilität) inkl. kombinierter Reverse-Suffix-Kette aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-B Langlauf-Recheck Reproduzierbarkeit/Stabilität)
- **Langlauf-Real-Run (Worker B):** `./scripts/run_webservice_e2e.sh` erfolgreich (`38 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-b-langlauf-1772094021.json` und `artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772094021.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-B Langlauf-Recheck synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Nachweisführung auf den aktuellen Worker-B-Recheck (`38 passed`, Smoke + 3x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Non-PASS-Report-Guard + Langlauf-Nachweis)
- **`scripts/run_remote_api_stability_check.sh`:** wertet Smoke-Reports jetzt inhaltlich aus; Runs mit vorhandenem JSON, aber `status!=pass` (oder ungültigem JSON/Payload) werden als Fehlrun gezählt, auch wenn das Smoke-Script `rc=0` liefert.
- **`tests/test_remote_stability_script.py`:** neuer E2E-Guard mit Fake-Smoke-Script verifiziert reproduzierbar, dass ein Report mit `status="fail"` trotz `rc=0` den Stabilitätslauf korrekt fehlschlagen lässt.
- **Langlauf-Real-Run (Worker A):** `./scripts/run_webservice_e2e.sh` erfolgreich (`38 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-a-langlauf-1772093853.json` und `artifacts/bl18.1-remote-stability-local-worker-a-langlauf-1772093853.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-A Non-PASS-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Stability-Hinweise auf den erweiterten Fail-Safe (`missing report` + `status!=pass`) und den aktuellen Worker-A-Langlauf (`38 passed`, Smoke + 3x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-C Suffix-Reihenfolge-Guard + Langlauf-Nachweis)
- **`tests/test_remote_smoke_script.py`:** neuer E2E-Happy-Path validiert die gemischte Suffix-Reihenfolge `.../analyze/health//` (inkl. trailing Slashes), damit die Base-URL-Normalisierung nicht nur `.../health/analyze`, sondern auch den umgekehrten Kettenfall regressionssicher abdeckt.
- **Langlauf-Real-Run (Worker C):** `./scripts/run_webservice_e2e.sh` erfolgreich (`37 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-c-langlauf-1772093532.json` und `artifacts/bl18.1-remote-stability-local-worker-c-langlauf-1772093532.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-C Suffix-Reihenfolge synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise und Nachweisführung auf den aktuellen Worker-C-Langlauf (`37 passed`, Smoke + 3x Stabilität) sowie die neue Absicherung für gemischte Suffix-Reihenfolge (`.../analyze/health//`) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-B Stability-Report-Guard + Langlauf-Nachweis)
- **`tests/test_remote_stability_script.py`:** neuer E2E-Fall stellt sicher, dass der Stability-Runner fehlende/leer gebliebene Smoke-Reports auch dann als Fehlrun behandelt, wenn das Smoke-Script `rc=0` liefert.
- **`scripts/run_remote_api_stability_check.sh`:** optionales Override `STABILITY_SMOKE_SCRIPT` ergänzt (Tests/Debug) sowie Fail-Safe für fehlende Smoke-JSON-Artefakte implementiert; `request_id` enthält zusätzlich PID-Suffix (`bl18-stability-<run>-<epoch>-<pid>`) zur Entkopplung paralleler Läufe.
- **Langlauf-Real-Run (Worker B):** `./scripts/run_webservice_e2e.sh` erfolgreich (`36 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-b-langlauf-1772093324.json` und `artifacts/bl18.1-remote-stability-local-worker-b-langlauf-1772093324.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-B Stability-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Stability-Runner-Hinweise auf `STABILITY_SMOKE_SCRIPT`, Missing-Report-Fail-Safe und aktuellen Worker-B-Langlauf (`36 passed`, Smoke + 3x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Request-ID-Guard + Langlauf-Nachweis)
- **`scripts/run_remote_api_smoketest.sh`:** `SMOKE_REQUEST_ID` wird vor dem Request getrimmt und fail-fast validiert (Whitespace-only + Steuerzeichen werden reproduzierbar mit `exit 2` abgewiesen), damit Request-ID-Echo-Checks stabil bleiben.
- **`tests/test_remote_smoke_script.py`:** neue E2E-Abdeckung für getrimmte Request-ID (Happy-Path) sowie Negativfälle für Whitespace-only und Steuerzeichen in `SMOKE_REQUEST_ID`.
- **Langlauf-Real-Run (Worker A):** `./scripts/run_webservice_e2e.sh` erfolgreich (`35 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-a-1772093014.json` und `artifacts/bl18.1-remote-stability-local-worker-a-1772093014.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-A Request-ID-Guard synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise, Validierungsregeln und Nachweisführung auf den aktuellen Worker-A-Langlauf mit Request-ID-Trim/Fast-Fail aktualisiert (`35 passed`, Smoke + 3x Stabilität).

### Added (2026-02-26 — BL-18.1 Iteration: Worker-C trailing-Slash-Härtung + Langlauf-Nachweis)
- **`scripts/run_remote_api_smoketest.sh`:** Base-URL-Normalisierung trimmt nach jedem Schritt jetzt **alle** trailing Slashes, sodass auch Inputs wie `.../health//analyze//` reproduzierbar zu `/analyze` normalisiert werden.
- **`tests/test_remote_smoke_script.py`:** neuer E2E-Happy-Path deckt redundante trailing-Slash-Ketten (`.../health//analyze//`) ab und schützt vor Regressionen.
- **Langlauf-Real-Run (Worker C):** `./scripts/run_webservice_e2e.sh` erfolgreich (`32 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-c-1772092769.json` und `artifacts/bl18.1-remote-stability-local-worker-c-1772092769.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-C trailing-Slash-Recheck synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Hinweise und Nachweise auf redundante trailing-Slash-Normalisierung aktualisiert; Reproduzierbarkeits-Status auf den aktuellen Worker-C-Langlauf (`32 passed`, Smoke + 3x Stabilität) gehoben.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-B2 Langlauf-Recheck kombinierte Base-URL-Normalisierung)
- **Langlauf-Real-Run (Worker B2):** `./scripts/run_webservice_e2e.sh` erfolgreich (`31 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-b2-1772092596.json` und `artifacts/bl18.1-remote-stability-local-worker-b2-1772092596.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-B2-Recheck synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Nachweisführung und Reproduzierbarkeits-Status auf den aktuellen Worker-B2-Langlauf (`31 passed`, Smoke + 3x Stabilität, kombinierter `HTTP://.../HeAlTh/AnAlYzE/`-Input) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Kombi-Normalisierung + Validierungsabdeckung)
- **`tests/test_remote_smoke_script.py`:** neuer Happy-Path für kombinierte Base-URL-Normalisierung (`"  HTTP://.../HeAlTh/AnAlYzE/  "`) ergänzt; zusätzliche Negativtests für `CURL_RETRY_DELAY=-1` und ungültiges `SMOKE_ENFORCE_REQUEST_ID_ECHO=2` sichern Fail-fast-Verhalten reproduzierbar ab.
- **Langlauf-Real-Run (Worker A):** `./scripts/run_webservice_e2e.sh` erfolgreich (`31 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-a-1772092447.json` und `artifacts/bl18.1-remote-stability-local-worker-a-1772092447.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-A-Kombi-Recheck synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Nachweisführung und E2E-Abdeckung auf den aktuellen Worker-A-Langlauf mit kombinierter URL-Normalisierung (`HTTP://.../HeAlTh/AnAlYzE/`, Whitespace, trailing Slash) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-C Langlauf-Recheck `HTTP://.../HeAlTh`)
- **Langlauf-Real-Run (Worker C):** `./scripts/run_webservice_e2e.sh` erfolgreich (`28 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-c-1772092067.json` und `artifacts/bl18.1-remote-stability-local-worker-c-1772092067.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-C-Recheck synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** BL-18.1-Nachweisführung auf den aktuellen Worker-C-Recheck mit gemischtem Base-URL-Input (`HTTP://.../HeAlTh`) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-B Suffix-Case-Härtung + Langlauf-Nachweis)
- **`scripts/run_remote_api_smoketest.sh`:** normalisiert `DEV_BASE_URL`-Suffixe `/health` und `/analyze` jetzt case-insensitive (z. B. `.../HeAlTh/AnAlYzE`) bevor `/analyze` aufgerufen wird.
- **`tests/test_remote_smoke_script.py`:** neuer E2E-Happy-Path sichert reproduzierbar ab, dass case-gemischte Suffixe korrekt normalisiert werden.
- **Langlauf-Real-Run (Worker B):** `./scripts/run_webservice_e2e.sh` erfolgreich (`28 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-b-1772091885.json` und `artifacts/bl18.1-remote-stability-local-worker-b-1772091885.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Suffix-Case-Langlauf synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Hinweise und Nachweise auf case-insensitive Suffix-Normalisierung, neue E2E-Abdeckung und aktuellen Worker-B-Langlauf (`28 passed`, Smoke + 3x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Whitespace-Trim-Härtung + Langlauf-Nachweis)
- **`scripts/run_remote_api_smoketest.sh`:** normalisiert `DEV_BASE_URL` jetzt zusätzlich per Whitespace-Trim; whitespace-only Inputs werden reproduzierbar früh mit `exit 2` abgewiesen.
- **`tests/test_remote_smoke_script.py`:** E2E-Happy-Path für getrimmte `DEV_BASE_URL` (`"  http://.../health  "`) sowie Negativfall für whitespace-only `DEV_BASE_URL` ergänzt.
- **Langlauf-Real-Run (Worker A):** `./scripts/run_webservice_e2e.sh` erfolgreich (`27 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-a-1772091687.json` und `artifacts/bl18.1-remote-stability-local-worker-a-1772091687.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Doku/Runbook auf Whitespace-Trim-Langlauf synchronisiert)
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedienhinweise und Nachweise auf Whitespace-Trim-Verhalten, neue E2E-Abdeckung und aktuellen Worker-A-Langlauf (`27 passed`, Smoke + 3x Stabilität) aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-C HTTP-Scheme-Case-Härtung + Langlauf-Nachweis)
- **`scripts/run_remote_api_smoketest.sh`:** http(s)-Schema-Check akzeptiert jetzt auch grossgeschriebene Varianten (`HTTP://`, `HTTPS://`) für robustere Runbook-Ausführung bei manuellen Copy/Paste-Inputs.
- **`tests/test_remote_smoke_script.py`:** neuer E2E-Happy-Path sichert reproduzierbar ab, dass `DEV_BASE_URL` mit `HTTP://.../health` erfolgreich normalisiert und getestet wird.
- **Langlauf-Real-Run (Worker C):** `./scripts/run_webservice_e2e.sh` erfolgreich (`25 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-c-1772091468.json` und `artifacts/bl18.1-remote-stability-local-worker-c-1772091468.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-C-Scheme-Case-Langlauf synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Command/Exit/Evidenz auf aktuellen Worker-C-Langlauf aktualisiert (`25 passed`, Smoke + 3x Stabilität) und die neue Schema-Case-Abdeckung dokumentiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-B Query/Fragment-Guard + Langlauf-Nachweis)
- **`tests/test_remote_smoke_script.py`:** E2E-Happy-Path für verkettete Base-URL-Suffixe (`.../health/analyze`) ergänzt sowie Negativtest für `DEV_BASE_URL` mit Query/Fragment (`exit 2`).
- **Langlauf-Real-Run (Worker B):** `./scripts/run_webservice_e2e.sh` erfolgreich (`24 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-b-1772091225.json` und `artifacts/bl18.1-remote-stability-local-worker-b-1772091225.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Smoke-Runner robust gegen URL-Query/Fragment)
- **`scripts/run_remote_api_smoketest.sh`:** Base-URL-Normalisierung verarbeitet verkettete `/health`-/`/analyze`-Suffixe; Query/Fragment-Komponenten werden fail-fast mit `exit 2` abgewiesen, damit der abgeleitete `/analyze`-Pfad reproduzierbar bleibt.
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Runbook/Backlog auf Query/Fragment-Guard, neue E2E-Abdeckung und aktuellen Worker-B-Real-Run (`24 passed`, Smoke + 3x Stabilität) synchronisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Langlauf-Check `/health`-Normalisierung + 3x Stabilität)
- **`tests/test_remote_smoke_script.py`:** zusätzlicher E2E-Happy-Path, dass `DEV_BASE_URL` mit Suffix `.../health` robust auf `/analyze` normalisiert wird.
- **Langlauf-Real-Run (Worker A):** `./scripts/run_webservice_e2e.sh` erneut erfolgreich (`22 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`) inkl. Request-ID-Echo Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-a-1772090927.json` und `artifacts/bl18.1-remote-stability-local-worker-a-1772090927.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-A-Langlauf synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Command/Exit/Evidenz und BL-18.1-Nachweis auf den aktuellen Worker-A-Langlauf aktualisiert (E2E `22 passed`, Smoke + 3x Stabilität).

### Added (2026-02-26 — BL-18.1 Iteration: Worker-C Langlauf-Recheck, 3x Stabilität)
- **Langlauf-Reproduzierbarkeits-Check (Worker C):** `./scripts/run_webservice_e2e.sh` erneut erfolgreich (`21 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`), inklusive Request-ID-Echo in Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-c-1772090698.json` und `artifacts/bl18.1-remote-stability-local-worker-c-1772090698.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-C-Langlauf synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Command/Exit/Evidenz auf den aktuellen Worker-C-Langlauf-Recheck aktualisiert (Smoke + 3x Stabilität + frischer E2E-Precheck).

### Added (2026-02-26 — BL-18.1 Iteration: Worker-B Langlauf-Real-Run, 3x Stabilität + Flake-Recheck)
- **Langlauf-Reproduzierbarkeits-Check (Worker B):** dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=3`, `fail=0`, Exit `0`), inklusive Request-ID-Echo in Header+JSON. Evidenz in `artifacts/bl18.1-smoke-local-worker-b-1772090574.json` und `artifacts/bl18.1-remote-stability-local-worker-b-1772090574.ndjson`.
- **Stabilitäts-Recheck E2E:** `./scripts/run_webservice_e2e.sh` im selben Lauf zusätzlich 5x wiederholt, jeweils erfolgreich (`21 passed`, Exit `0`).

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-B-Langlauf synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Command/Exit/Evidenz um den aktuellen Worker-B-Langlauf ergänzt (Smoke + 3x Stabilität + 5x E2E-Recheck).

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Isolated Real-Run, 3x Stabilität + E2E-Recheck)
- **Isolierter Reproduzierbarkeits-Check (Worker A):** `./scripts/run_webservice_e2e.sh` erfolgreich (`21 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` mit `STABILITY_RUNS=3` erfolgreich (`pass=3`, `fail=0`, Exit `0`). Evidenz in `artifacts/bl18.1-smoke-local-worker-a-1772090470.json` und `artifacts/bl18.1-remote-stability-local-worker-a-1772090470.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-A-Isolated-Nachweis synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Command/Exit/Evidenz um den isolierten Worker-A-Lauf erweitert (Smoke + 3x Stabilität + E2E-Recheck).

### Added (2026-02-26 — BL-18.1 Iteration: Worker-B2 Real-Run-Nachweis, 3x Stabilität + E2E-Recheck)
- **Lokaler Reproduzierbarkeits-Check (Worker B2):** `./scripts/run_webservice_e2e.sh` erfolgreich (`21 passed`, Exit `0`) sowie dedizierter BL-18.1-Lauf via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` mit `STABILITY_RUNS=3` erfolgreich (`pass=3`, `fail=0`, Exit `0`). Evidenz in `artifacts/bl18.1-smoke-local-worker-b2-1772090073.json` und `artifacts/bl18.1-remote-stability-local-worker-b2-1772090073.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Runbook/Backlog auf Worker-B2-Nachweis synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Command/Exit/Evidenz um den aktuellen Worker-B2-Lauf erweitert (Smoke + 3x Stabilität + E2E-Recheck).

### Added (2026-02-26 — BL-18.1 Iteration: Worker-A Real-Run-Nachweis, 3x Stabilität)
- **Lokaler Real-Run (Worker A):** `run_remote_api_smoketest.sh` erfolgreich (Exit `0`, HTTP `200`, `ok=true`, Request-ID-Echo Header+JSON konsistent) sowie `run_remote_api_stability_check.sh` mit `STABILITY_RUNS=3` erfolgreich (`pass=3`, `fail=0`, Exit `0`). Evidenz in `artifacts/bl18.1-smoke-local-worker-a.json` und `artifacts/bl18.1-remote-stability-local-worker-a.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Doku auf Worker-A-Nachweis synchronisiert)
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** BL-18.1-Runbook und Backlog-Nachweis um den aktuellen Worker-A-Real-Run ergänzt.

### Added (2026-02-26 — BL-18/BL-18.1 Iteration: API-Timeout-Guard + Worker-C-Nachweis)
- **`tests/test_web_e2e.py`:** Negativfall für non-finite `timeout_seconds` (`nan`) ergänzt; API muss reproduzierbar mit `400 bad_request` antworten.
- **Lokaler Real-Run (Worker C):** `./scripts/run_webservice_e2e.sh` erneut erfolgreich (`21 passed`) sowie dedizierte BL-18.1-Läufe via `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` erfolgreich (`pass=2`, `fail=0`, Request-ID-Echo Header+JSON konsistent); Evidenz in `artifacts/bl18.1-smoke-local-worker-c.json` und `artifacts/bl18.1-remote-stability-local-worker-c.ndjson`.

### Changed (2026-02-26 — BL-18 Iteration: Endliche Timeout-Validierung im API-Pfad)
- **`src/web_service.py`:** `timeout_seconds` sowie `ANALYZE_DEFAULT_TIMEOUT_SECONDS`/`ANALYZE_MAX_TIMEOUT_SECONDS` auf endliche Zahlen `> 0` gehärtet (`nan`/`inf` werden als `400 bad_request` abgewiesen statt spätem Folgefehler).
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Doku/Runbook/Backlog auf API-seitige Numerik-Validierung und Worker-C-Real-Run-Nachweis synchronisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Non-finite Numerik-Guards + Worker-B-Nachweis)
- **`tests/test_remote_smoke_script.py`:** Negativtests für non-finite Timeouts ergänzt (`SMOKE_TIMEOUT_SECONDS=nan`, `CURL_MAX_TIME=inf`) mit reproduzierbarem `exit 2`.
- **Lokaler Real-Run (Worker B):** `run_remote_api_smoketest.sh` + `run_remote_api_stability_check.sh` gegen lokale Webservice-Instanz erfolgreich ausgeführt (`pass=2`, `fail=0`, Request-ID-Echo Header+JSON konsistent), Evidenz in `artifacts/bl18.1-smoke-local-worker-b.json` und `artifacts/bl18.1-remote-stability-local-worker-b.ndjson`.

### Changed (2026-02-26 — BL-18.1 Iteration: Striktere Numerik-Validierung + sauberer Workspace)
- **`scripts/run_remote_api_smoketest.sh`:** Numerische Eingabeprüfung auf endliche positive Zahlen gehärtet (`nan`/`inf` werden nun früh mit `exit 2` abgewiesen).
- **`.gitignore`:** Laufzeit-/Smoke-Artefakte (`artifacts/`) explizit ignoriert, damit wiederholte BL-18.1-Runs den Git-Status nicht verschmutzen.
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Runbook-/Backlog-Doku auf endliche Numerik-Validierung synchronisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Input-Validierung für Remote-Smoke-Runner)
- **`tests/test_remote_smoke_script.py`:** Negativfälle für ungültige numerische Smoke-Parameter ergänzt (`SMOKE_TIMEOUT_SECONDS`, `CURL_RETRY_COUNT`) und auf reproduzierbaren `exit 2` abgesichert.

### Changed (2026-02-26 — BL-18.1 Iteration: Fail-fast bei fehlerhaften Smoke-Parametern)
- **`scripts/run_remote_api_smoketest.sh`:** Harte Eingabevalidierung ergänzt (`SMOKE_TIMEOUT_SECONDS`/`CURL_MAX_TIME` > 0, `CURL_RETRY_COUNT`/`CURL_RETRY_DELAY` Ganzzahl >= 0) statt später Python-Tracebacks.
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Runbook-/Backlog-Doku auf neue Parameter-Validierung + Real-Run-Nachweis synchronisiert.

### Added (2026-02-26 — BL-18.1 Iteration: URL-Normalisierung im Remote-Smoke abgesichert)
- **`tests/test_remote_smoke_script.py`:** Zusätzliche E2E-Checks für normalisierte Base-URLs (`.../analyze`) und harten Negativfall für ungültiges URL-Schema (`exit 2`).
- **`tests/test_remote_stability_script.py`:** E2E-Check ergänzt, dass der Stabilitätsrunner auch mit `DEV_BASE_URL`-Suffix `.../health` reproduzierbar erfolgreich läuft.

### Changed (2026-02-26 — BL-18.1 Iteration: Smoke-Runbook robuster gegen URL-Fehlkonfiguration)
- **`scripts/run_remote_api_smoketest.sh`:** Vor dem Request robuste Base-URL-Normalisierung (`/health`/`/analyze`-Suffix) und harte Validierung auf `http(s)` + gültige URL-Struktur ergänzt.
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Runbook-/Backlog-Doku auf neue URL-Normalisierung und Eingabevalidierung synchronisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Stabilitätsrunner-Inputvalidierung)
- **`tests/test_remote_stability_script.py`:** Negativtest ergänzt, der ungültiges `STABILITY_STOP_ON_FIRST_FAIL` (`!= 0|1`) mit Exit-Code `2` absichert.

### Changed (2026-02-26 — BL-18.1 Iteration: Fail-Fast-Flag reproduzierbar validiert)
- **`scripts/run_remote_api_stability_check.sh`:** `STABILITY_STOP_ON_FIRST_FAIL` wird jetzt strikt auf `0|1` validiert; Fehleingaben brechen früh und eindeutig mit Exit `2` ab.
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Doku auf validiertes Fail-Fast-Flag und Testnachweis aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Request-ID-Echo-Abnahme im Smoke-Runner)
- **`tests/test_remote_smoke_script.py`:** Happy-Path erweitert um harte Assertions auf Request-ID-Korrelation (`request_id`, `response_request_id`, `response_header_request_id`).
- **`tests/test_remote_stability_script.py`:** NDJSON-Validierung um Request-ID-Echo-Nachweis pro Run ergänzt.

### Changed (2026-02-26 — BL-18.1 Iteration: Smoke-Runner prüft Header+JSON-Korrelation)
- **`scripts/run_remote_api_smoketest.sh`:** Response-Header werden jetzt mit ausgewertet; default wird Request-ID-Echo gegen `SMOKE_REQUEST_ID` erzwungen (Header `X-Request-Id` + JSON `request_id`), inkl. neuer Fehlgründe `request_id_header_mismatch` / `request_id_body_mismatch` und Schalter `SMOKE_ENFORCE_REQUEST_ID_ECHO=0|1`.
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** BL-18.1-Nachweisführung auf Request-ID-Echo-Abnahme aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: Stabilitätsrunner-E2E-Härtung)
- **`tests/test_remote_stability_script.py`:** Neue lokale E2E-Tests für `run_remote_api_stability_check.sh` (Happy Path mit zwei erfolgreichen Runs + Abbruchpfad via `STABILITY_STOP_ON_FIRST_FAIL=1`).

### Changed (2026-02-26 — BL-18.1 Iteration: Test-Runner-/Doku-Abgleich)
- **`scripts/run_webservice_e2e.sh`:** Lokalen BL-18-Testlauf um `tests/test_remote_stability_script.py` erweitert.
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Testabdeckung und Nachweisführung für BL-18.1-Stabilitätsläufe aktualisiert.

### Added (2026-02-26 — BL-18.1 Iteration: API Request-ID-Korrelation)
- **`tests/test_web_e2e.py`:** E2E-Abdeckung für Request-ID-Echo auf `/analyze` ergänzt (Header `X-Request-Id` + JSON-Feld `request_id` in Erfolgs- und Auth-Fehlpfad).

### Changed (2026-02-26 — BL-18.1 Iteration: Endpoint-Verhalten `/analyze` observability)
- **`src/web_service.py`:** `/analyze` antwortet jetzt konsistent mit korrelierbarer Request-ID (`X-Request-Id`/`X-Correlation-Id` Echo als Response-Header + JSON-Feld `request_id`), inklusive Fehlerpfaden (401/400/500/504).
- **`README.md` / `docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md`:** Bedien- und Nachweisdoku um Request-ID-Korrelation ergänzt.

### Added (2026-02-26 — BL-18.1 Iteration: Remote-Smoke-Härtung + Stabilitätslauf)
- **`scripts/run_remote_api_stability_check.sh`:** Neuer Mehrfach-Runner für BL-18.1. Führt mehrere `/analyze`-Smoke-Requests aus, schreibt NDJSON-Report und erzwingt über `STABILITY_MAX_FAILURES` eine klare Pass/Fail-Abnahme.
- **`tests/test_remote_smoke_script.py`:** Neue lokale E2E-Tests für das Remote-Smoke-Skript (Happy Path mit Token + erwarteter 401-Fehlpfad ohne Token).

### Changed (2026-02-26 — BL-18.1 Iteration: Reproduzierbarkeit + CI-Nachweis)
- **`scripts/run_remote_api_smoketest.sh`:** Um Retry-Handling, Request-ID, stricte Mode-Validierung und optionale JSON-Artefaktausgabe (`SMOKE_OUTPUT_JSON`) erweitert.
- **`scripts/run_webservice_e2e.sh`:** Lokalen BL-18-Testlauf um `tests/test_remote_smoke_script.py` ergänzt.
- **`tests/test_web_e2e_dev.py`:** Dev-Auth-Negativfall mit bewusst falschem Bearer-Token ergänzt.
- **`.github/workflows/deploy.yml`:** Optionaler `/analyze`-Smoke-Test nach ECS-Deploy ergänzt (Base-URL via `SERVICE_BASE_URL` bzw. ableitbar aus `SERVICE_HEALTH_URL`, optional mit Secret `SERVICE_API_AUTH_TOKEN`).
- **`docs/BL-18_SERVICE_E2E.md` / `docs/BACKLOG.md` / `README.md`:** Runbook, Backlog-Nachweis und Bedienhinweise für BL-18.1 aktualisiert.

### Changed (2026-02-26 — BL-15 Iteration: 8h-Recheck + AssumeRole-Korrelation)
- **`docs/LEGACY_IAM_USER_READINESS.md`:** Read-only Recheck ergänzt (`audit_legacy_*`, `LOOKBACK_HOURS=8 audit_legacy_cloudtrail_consumers.sh`, `check_bl17_oidc_assumerole_posture.sh`) inkl. Befund „OIDC-Workflows korrekt, Runtime-Caller weiterhin Legacy“.
- **`docs/LEGACY_CONSUMER_INVENTORY.md`:** Basislage + Fingerprint-Sektion auf 6h/8h-Recheck erweitert; `sts:AssumeRole`-Signal dokumentiert, aber weiterhin kein AssumeRole-first-Default bestätigt.
- **`docs/BACKLOG.md`:** BL-15-Nachweise/Blocker/Next-Actions um vertieften 8h-Recheck und klare AssumeRole-first-Next-Step (`scripts/aws_exec_via_openclaw_ops.sh`) aktualisiert.
- **`docs/OPERATIONS.md`:** Agent-Autopilot-Kurzfassung um verbindlichen AssumeRole-first-Aufrufpfad via `scripts/aws_exec_via_openclaw_ops.sh` ergänzt.

### Added (2026-02-26 — BL-15 Iteration: CloudTrail-Consumer-Fingerprints)
- **`scripts/audit_legacy_cloudtrail_consumers.sh`:** Neues read-only Audit-Script für Legacy-IAM-Attribution via CloudTrail (`lookup-events` auf Username). Gruppiert Events nach `source_ip` + `user_agent`, zeigt `event_source`/`event_name`, filtert `LookupEvents` standardmäßig heraus und liefert klare Exit-Codes (`0` kein Legacy-Event, `10` Legacy-Aktivität, `20` Fehler).

### Changed (2026-02-26 — BL-15 Iteration: Attribution präzisiert)
- **`docs/LEGACY_IAM_USER_READINESS.md`:** Um Abschnitt „CloudTrail-Fingerprint Audit“ mit verifiziertem 6h-Lauf ergänzt (dominanter Non-AWS-Fingerprint `76.13.144.185`, zusätzliche AWS-Service-Delegation via `lambda.amazonaws.com`).
- **`docs/LEGACY_CONSUMER_INVENTORY.md`:** Basislage + Fingerprint-Hinweise um neue CloudTrail-Evidenz erweitert.
- **`docs/BACKLOG.md`:** BL-15-Nachweis/Blocker/Next-Actions um das neue Fingerprint-Audit konkretisiert.
- **`docs/OPERATIONS.md` / `docs/DEPLOYMENT_AWS.md` / `docs/AWS_INVENTORY.md`:** Runbook-Verweise auf `audit_legacy_cloudtrail_consumers.sh` ergänzt.

### Added (2026-02-26 — BL-18 Iteration: Webservice-E2E + Auth/Timeout-Abdeckung)
- **`tests/test_web_e2e.py`:** Neue lokale End-to-End-Test-Suite mit Prozessstart des Webservice und Abdeckung für Health/Version, 404, Auth (401), Bad Request (400), Timeout (504), Internal Error (500) und Happy Path für `/analyze`.
- **`tests/test_web_e2e_dev.py`:** Neue dev-E2E-Suite gegen `DEV_BASE_URL` (optional `DEV_API_AUTH_TOKEN`) für reproduzierbare Endpoint-Checks in der laufenden Umgebung.
- **`scripts/run_webservice_e2e.sh`:** Runner-Script für lokal + optional dev in einem Kommando.
- **`docs/BL-18_SERVICE_E2E.md`:** Ist-Analyse, Testdesign und Runbook für BL-18 dokumentiert.

### Changed (2026-02-26 — BL-18 Iteration: Service-Handling erweitert)
- **`src/web_service.py`:**
  - Optionales Bearer-Token-Auth-Gate für `/analyze` via `API_AUTH_TOKEN`.
  - Validierung von `intelligence_mode` auf `basic|extended|risk`.
  - Konfigurierbares Timeout-Handling via `ANALYZE_DEFAULT_TIMEOUT_SECONDS`, `ANALYZE_MAX_TIMEOUT_SECONDS` und Request-Feld `timeout_seconds`.
  - Explizites Fehler-Mapping `TimeoutError -> 504`.
  - Kontrollierte E2E-Fault-Injection für Testzwecke via `ENABLE_E2E_FAULT_INJECTION=1` (`__timeout__`, `__internal__`).
- **`README.md`:** `/analyze`-Requestformat, optionales Auth-Handling und E2E-Test-Runner ergänzt; Doku-Index um BL-18-Dokument erweitert.

### Added (2026-02-26 — BL-17 Iteration: OIDC/AssumeRole-Posture Quick-Check)
- **`scripts/check_bl17_oidc_assumerole_posture.sh`:** Neues Read-only Check-Script für BL-17. Prüft OIDC-Marker in aktiven Workflows (`configure-aws-credentials`, `id-token: write`), erkennt statische AWS-Key-Referenzen, klassifiziert den aktuellen AWS-Caller (AssumeRole `openclaw-ops-role` vs. Legacy-User) und führt bestehende Audit-Skripte als Kontextlauf mit aus.
- **`docs/OPENCLAW_OIDC_FIRST_FALLBACK_PLAN.md`:** Verifikationssektion um automatisierten BL-17 Quick-Check ergänzt.
- **`docs/OPERATIONS.md`:** Agent-Autopilot-Kurzfassung auf BL-17 Quick-Check als Standard vor AWS-Ops umgestellt.
- **`docs/BACKLOG.md`:** BL-17 Umsetzungsstand um das neue Posture-Check-Script erweitert.

### Added (2026-02-25 — BL-12 HTTP Uptime Probe aktiv)
- **`infra/lambda/health_probe/lambda_function.py`:** Lambda-Probe (Python 3.12). Löst öffentliche IP des laufenden ECS-Tasks dynamisch auf (kein ALB/stabile Domain erforderlich), führt HTTP GET `/health` durch, publiziert CloudWatch-Metrik `HealthProbeSuccess` (1=ok, 0=fail). Kein externer Dependency-Overhead (nur stdlib + boto3).
- **`scripts/setup_health_probe_dev.sh`:** Idempotentes Setup-Script. Erstellt IAM-Role (`swisstopo-dev-health-probe-role`, Minimal-Privilege), Lambda `swisstopo-dev-health-probe`, EventBridge Scheduled Rule (rate 5 min) und CloudWatch Alarm (`swisstopo-dev-api-health-probe-fail` → SNS → Telegram). Kein `zip`-Binary nötig (ZIP via Python stdlib). Inkl. sofortigem Lambda-Testlauf nach Deployment.
- **`scripts/check_health_probe_dev.sh`:** Read-only Status-Check: Lambda-State, EventBridge-Rule, letzte Invocations, HealthProbeSuccess-Metrik, Alarm-Zustand. Exit Codes: `0` OK, `10` Warn, `20` kritisch.
- **AWS (live, non-destructive):** IAM-Role, Lambda, EventBridge Rule, CW Alarm erstellt und verifiziert. Erster Testlauf erfolgreich: IP dynamisch aufgelöst (`18.184.115.244`), HTTP 200 erhalten, `HealthProbeSuccess = 1` publiziert.
- **`docs/OPERATIONS.md`:** Sektion 3 „HTTP Health Check Guidance" vollständig durch operativen Probe-Abschnitt ersetzt (Architektur, Ressourcen, Kommandos, Kosten, ALB-Hinweis).
- **`docs/DEPLOYMENT_AWS.md`:** Ressourcen-Tabelle um Lambda + EventBridge erweitert; Monitoring-Tabelle aktualisiert (`Uptime/HTTP Health` = ✅ aktiv); neue Sektion „HTTP Uptime Probe — GET /health (BL-12)" mit Komponenten, Setup-Kommandos und Testnachweis.
- **`docs/BACKLOG.md`:** BL-12 neu angelegt und als abgeschlossen markiert.

### Added (2026-02-26 — BL-11 AWS-Inventory & Konfigurationsdokumentation)
- **`docs/AWS_INVENTORY.md`:** Vollständiges, verifiziertes AWS-Ressourcen-Inventar für die `dev`-Umgebung. Enthält alle Bereiche (IAM, ECR, ECS, CloudWatch, S3, Lambda, SNS, SSM, Netzwerk/VPC) mit Name/ARN, Region, Zweck, Tags, zentralen Konfig-Parametern, IaC-Status (`🔧 Terraform` vs. `🖐️ Manuell`) und Rebuild-Hinweisen inkl. Abhängigkeitsreihenfolge. Alle Werte direkt via read-only AWS-Abfragen verifiziert. Keine Secrets oder sensitiven Inhalte enthalten.
- **`README.md`:** Doku-Index und Projektbaum um `docs/AWS_INVENTORY.md` erweitert.
- **`docs/DEPLOYMENT_AWS.md`:** Verweis auf `docs/AWS_INVENTORY.md` als zentrales Ressourcen-Inventar ergänzt.
- **`docs/BACKLOG.md`:** BL-11 auf abgeschlossen gesetzt inkl. Nachweis.

### Added (2026-02-26 — BL-15 gestartet: Legacy-IAM Decommission Readiness dokumentiert)
- **`docs/LEGACY_IAM_USER_READINESS.md`:** Neues read-only Runbook mit verifizierter Ist-Lage des Legacy-Users `swisstopo-api-deploy` (aktiver Key, Last-Used, Policy-Set, Access-Advisor-Auszug, CloudTrail-Hinweise), risikoarmer 3-Phasen-Decommission-Checkliste und Go/No-Go-Entscheidungsvorlage.
- **`docs/AWS_INVENTORY.md`:** Abschnitt 1.1 von Annahme auf verifizierten Status aktualisiert; Decommission-Status + Link auf das neue Readiness-Runbook ergänzt.
- **`docs/BACKLOG.md`:** BL-15 auf „in Umsetzung" gesetzt, Nachweise/Blocker/Next-Actions ergänzt.

### Added (2026-02-26 — BL-15 Iteration: Legacy-Consumer-Inventar automatisiert)
- **`scripts/audit_legacy_aws_consumer_refs.sh`:** Neues read-only Audit-Script zur reproduzierbaren Erfassung von Legacy-IAM-Key-Consumern (Caller-ARN, OIDC-vs-Static-Key-Check in aktiven Workflows, Repo-Referenzen, AWS-CLI-Skripte). Exit-Codes: `0` (kein harter Befund), `10` (Legacy-Caller aktiv), `20` (statische Keys in aktiven Workflows).

### Added (2026-02-26 — BL-15 Iteration: Runtime-Consumer-Baseline automatisiert)
- **`scripts/audit_legacy_runtime_consumers.sh`:** Neues read-only Audit-Script für Runtime-Quellen außerhalb des Repos (sanitisiertes Environment, Shell-/Environment-Profile, AWS Credential-Files, User/System-Cron, Systemd Units, OpenClaw-Konfig-Dateien). Exit-Codes: `0` (kein Befund), `10` (Legacy-Caller aktiv), `20` (Runtime-Referenzen), `30` (beides).

### Added (2026-02-26 — BL-15 Iteration: Externe Consumer-Matrix)
- **`docs/LEGACY_CONSUMER_INVENTORY.md`:** Neues Tracking-Dokument für offene Legacy-Consumer außerhalb des bereits migrierten OIDC-CI/CD-Pfads (Known Consumers, offene externe Targets, Migrationspfade, Exit-Kriterien für BL-15).

### Changed (2026-02-26 — BL-15 Iteration: Consumer-Blocker präzisiert)
- **`docs/LEGACY_IAM_USER_READINESS.md`:** Um Verweis auf die neue Consumer-Matrix erweitert; Phase-A-Checkliste präzisiert (Host-Baseline erledigt, externe Targets weiterhin offen).
- **`docs/BACKLOG.md`:** BL-15-Nachweis um Consumer-Matrix ergänzt, Blocker um Runtime-Credential-Injection konkretisiert, Next Actions auf externe Target-Inventarisierung geschärft; BL-17-Status auf „offen (Start nach BL-15)" konsolidiert.
- **`docs/DEPLOYMENT_AWS.md` / `docs/AWS_INVENTORY.md` / `docs/OPERATIONS.md`:** Verweise auf die neue Consumer-Matrix ergänzt.
- **`docs/ARCHITECTURE.md`:** Abschnitt „Offene Punkte“ auf aktuelle offene Blöcke (`BL-15`, `BL-17`, `BL-18`) aktualisiert.

### Changed (2026-02-26 — BL-15 Fortschritt + Folge-Sequenz konsolidiert)
- **`docs/LEGACY_IAM_USER_READINESS.md`:** Neue Section „Repo-scope Consumer-Inventar" ergänzt; Befund dokumentiert: aktive Workflow-Pipeline läuft OIDC-only, aktiver OpenClaw-Caller bleibt Legacy-User.
- **`docs/BACKLOG.md`:** BL-15 Nachweise/Blocker/Next-Actions auf Audit-Stand aktualisiert (Repo-Inventar abgeschlossen, Runtime-Inventar offen). Folge-Sequenz um BL-17/BL-18 als nächste priorisierte Blöcke konkretisiert.
- **`docs/AWS_INVENTORY.md`:** Legacy-IAM-Abschnitt um reproduzierbaren Repo-Consumer-Check (`./scripts/audit_legacy_aws_consumer_refs.sh`) ergänzt.
- **`docs/DEPLOYMENT_AWS.md`:** Backlog-Referenz auf aktuelle Range (`BL-01` bis `BL-18`) aktualisiert; Hinweis auf neuen Consumer-Audit ergänzt.
- **`docs/OPERATIONS.md`:** Agent-Autopilot-Kurzfassung um verpflichtenden Legacy-Principal-Check (`./scripts/audit_legacy_aws_consumer_refs.sh`) erweitert.

### Changed (2026-02-26 — BL-15 Iteration: Runtime-Baseline dokumentiert)
- **`docs/LEGACY_IAM_USER_READINESS.md`:** Neue Section „Runtime-Consumer Baseline (host-level)“ ergänzt, inklusive verifizierter Befunde aus `./scripts/audit_legacy_runtime_consumers.sh` und präzisierter Interpretation (aktuelle Legacy-Nutzung ist laufzeitgebunden, nicht über persistierte Host-Profile/Configs).
- **`docs/BACKLOG.md`:** BL-15 Nachweis um Runtime-Baseline erweitert; Next Action 2 auf konkreten Restscope (externe Runner/Hosts) präzisiert.
- **`docs/AWS_INVENTORY.md`:** Legacy-IAM-Abschnitt um reproduzierbaren Runtime-Baseline-Check (`./scripts/audit_legacy_runtime_consumers.sh`) ergänzt.
- **`docs/DEPLOYMENT_AWS.md`:** BL-15 Statushinweis um Runtime-Baseline-Script ergänzt.
- **`docs/OPERATIONS.md`:** Agent-Autopilot-Kurzfassung um Runtime-Audit-Check (`./scripts/audit_legacy_runtime_consumers.sh`) erweitert.

### Changed (2026-02-26 — BL-14 abgeschlossen: Terraform-Plan verifiziert, Import-Runbook präzisiert)
- **`infra/terraform/health_probe.tf`:** Terraform-Definition für Health-Probe finalisiert (Fix `target_id` statt ungültigem `id` bei `aws_cloudwatch_event_target`; `statement_id` auf bestehenden Wert `allow-eventbridge-health-probe` abgestimmt; Beschreibungen auf Live-Setup harmonisiert).
- **`infra/terraform/outputs.tf`:** Safe-Output-Fix: fehlerhafte `coalesce(...)`-Ausdrücke durch robuste `try(..., null)`-Varianten ersetzt, damit `terraform plan` im Safe-Default (`manage_* = false`) ohne Fehler läuft.
- **`infra/terraform/README.md`:** Vollständige Import-Reihenfolge für BL-14 ergänzt (inkl. `aws_iam_role_policy`, `aws_iam_role_policy_attachment`, `aws_lambda_permission`).
- **`docs/DEPLOYMENT_AWS.md`:** Terraform-Import-Kommandos für Health-Probe vervollständigt; BL-14-Status auf verifiziert abgeschlossen aktualisiert.
- **`docs/BACKLOG.md`:** BL-14 von „in Umsetzung“ auf ✅ abgeschlossen gesetzt; Nachweis um ausgeführte Terraform-Validierung und Plan-Ergebnis ergänzt (**0 add / 4 change / 0 destroy**, keine destruktiven Aktionen).

### Changed (2026-02-26 — BL-13 gestartet und abgeschlossen: Doku-Konsistenz nach Nacht-Plan)
- **`docs/BACKLOG.md`:** Neue Folge-Sequenz nach abgeschlossenem Nacht-Plan angelegt (`BL-13` bis `BL-15`), `BL-13` als abgeschlossen dokumentiert und Nachweise ergänzt.
- **`docs/DEPLOYMENT_AWS.md`:** Abschnitt „Offene Punkte / TODOs“ konsolidiert; veralteter Restpunkt zur bereits aktiven HTTP-Uptime-Probe entfernt; Backlog-Referenz auf aktuelle BL-Range (`BL-01` bis `BL-15`) aktualisiert.

### Changed (2026-02-26 — BL-03 final abgeschlossen, Least-Privilege OIDC-Doku finalisiert)
- **`infra/iam/trust-policy.json`:** Neu — Trust-Policy der OIDC-Deploy-Role versioniert (`repo:nimeob/geo-ranking-ch:ref:refs/heads/main`, verifiziert identisch mit live AWS-Konfiguration).
- **`infra/iam/README.md`:** Status auf `✅ Final abgeschlossen` aktualisiert; bisheriger „Vorbereitung"-Hinweis (misleading) entfernt; neuen Nachweis-Abschnitt ergänzt (Role ARN, Policy-Version, Trust-Bedingung, E2E-Run-Links, Policy-Drift-Verifikation — kein Drift); Hinweise für Staging/Prod-OIDC-Rollen ergänzt.
- **`docs/DEPLOYMENT_AWS.md`:** AWS-Basis-Tabelle: OIDC-Deploy-Role als aktueller CI/CD-Principal eingetragen; IAM-User `swisstopo-api-deploy` als Legacy markiert (nicht mehr für CI/CD genutzt). IAM-Sektion umbenannt auf „OIDC Deploy-Role — BL-03 ✅ abgeschlossen"; Minimalrechte-Tabelle um Scope-Spalte ergänzt.
- **`docs/BACKLOG.md`:** BL-03 finaler Eintrag ergänzt (Trust-Policy-Artefakt, README/Doku-Update als Done nachgeführt).

### Changed (2026-02-25 — BL-08 final abgeschlossen, Empfangsnachweis erbracht)
- **`docs/BACKLOG.md`:** BL-08 von „in Umsetzung“ auf **abgeschlossen** gesetzt; Blocker/Next-Actions entfernt; Deploy- + Empfangsnachweis (`ALARM` und `OK`) dokumentiert.
- **`docs/DEPLOYMENT_AWS.md`:** Status für Lambda/Alert-Kanal auf **verifiziert aktiv** aktualisiert; offene Punkte entsprechend bereinigt.
- **`docs/OPERATIONS.md`:** Monitoring-Kapitel um klaren End-to-End-Status ergänzt (`CloudWatch → SNS → Lambda → Telegram` verifiziert).

### Changed (2026-02-25 — BL-08 Telegram-Alerting IaC implementiert)
- **`infra/lambda/sns_to_telegram/lambda_function.py`:** Lambda-Handler (Python 3.12) für CloudWatch-Alarm → Telegram. Liest Bot-Token sicher aus SSM SecureString zur Laufzeit. Nachrichtenformat: Alarmname, State, Reason, Region, Account, Timestamp — robust bei fehlenden Feldern. Kein externer Dependency-Overhead (nur stdlib + boto3).
- **`infra/terraform/lambda_telegram.tf`:** Terraform-Ressourcen für Lambda-Funktion, IAM-Role (Minimal-Privilege: CloudWatch Logs + SSM GetParameter + KMS Decrypt), Lambda-Permission für SNS und SNS → Lambda-Subscription. Aktivierung via Flag `manage_telegram_alerting = true`. Zip wird automatisch via `archive_file` erzeugt.
- **`infra/terraform/variables.tf`:** Neue Variablen `manage_telegram_alerting`, `aws_account_id`, `sns_topic_arn`, `telegram_chat_id`.
- **`infra/terraform/outputs.tf`:** Neue Outputs `telegram_lambda_arn`, `telegram_lambda_function_name`, `telegram_sns_subscription_arn`, erweitertes `resource_management_flags`.
- **`infra/terraform/terraform.tfvars.example`:** Telegram-Alerting-Block mit Kommentaren zu manueller SSM-Anlage und Aktivierungsschritten ergänzt.
- **`scripts/setup_telegram_alerting_dev.sh`:** Neu — idempotentes Setup-Script als Fallback zu Terraform. Legt SSM-Parameter, IAM-Role, Lambda und SNS-Subscription in einem Durchgang an. Erwartet `TELEGRAM_BOT_TOKEN` und `TELEGRAM_CHAT_ID` als Umgebungsvariablen (nie auf Disk oder im Repo).
- **`scripts/check_monitoring_baseline_dev.sh`:** Telegram-Alerting-Checks ergänzt: Lambda-State, SNS-Subscription aktiv, `TELEGRAM_CHAT_ID` in Lambda-Env, SSM-Parameter-Existenz.
- **`docs/DEPLOYMENT_AWS.md`:** Monitoring-Tabelle auf Telegram-Status aktualisiert; neue Sektion „Telegram-Alerting — Architektur & Deployment" mit Deploy-Optionen A/B, Testalarm-Kommandos und Secret-Hinweis.
- **`docs/OPERATIONS.md`:** Alarm-Kanal-Sektion auf SNS + Lambda → Telegram erweitert; Kontrollierter Testalarm und SNS-Publish-Snippet ergänzt.
- **`docs/BACKLOG.md`:** BL-08 auf aktuellen Stand gebracht: Telegram-IaC als umgesetzt; konkrete Next-Actions für Nico (SSM anlegen → Deploy → Testalarm → Verifikation).

### Changed (2026-02-25 — BL-08 Monitoring-Checklauf operationalisiert)
- **`scripts/check_monitoring_baseline_dev.sh`:** Neues read-only Prüfscript ergänzt (ECS/Logs/Metric-Filters/Alarme/SNS inkl. Subscriber-Status) mit klaren Exit-Codes (`0` OK, `10` Warn, `20` Fail).
- **`docs/OPERATIONS.md`:** Monitoring-Abschnitt um den Baseline-Check inkl. Exit-Code-Interpretation erweitert.
- **`docs/DEPLOYMENT_AWS.md`:** Ops-Helper und Alert-Kanal-Status um den neuen Read-only Check ergänzt.
- **`docs/BACKLOG.md`:** BL-08 Fortschritt und aktueller Checkstand dokumentiert (`keine SNS Subscriber vorhanden`).

### Changed (2026-02-25 — BL-09 Promotion-Strategie für staging/prod vorbereitet)
- **`docs/ENV_PROMOTION_STRATEGY.md`:** Neu angelegt mit Zielarchitektur pro Umgebung, Promotion-Gates (`dev`→`staging`→`prod`), Freigaberegeln und Rollback-Standard.
- **`docs/BACKLOG.md`:** BL-09 auf abgeschlossen gesetzt und Nachweisdokument verlinkt.
- **`README.md` / `docs/ARCHITECTURE.md` / `docs/DEPLOYMENT_AWS.md`:** Referenzen auf die neue Promotion-Strategie ergänzt.

### Changed (2026-02-25 — BL-08 Monitoring-Baseline umgesetzt, externer Receiver offen)
- **`scripts/setup_monitoring_baseline_dev.sh`:** Neues idempotentes Setup-Script für dev-Monitoring (SNS Topic, Log Metric Filters, Alarme für Service-Ausfall + 5xx-Fehlerquote, SNS-Testpublishing).
- **AWS (live, non-destructive):** Topic `swisstopo-dev-alerts`, Metric Filters (`HttpRequestCount`, `Http5xxCount`) und Alarme (`swisstopo-dev-api-running-taskcount-low`, `swisstopo-dev-api-http-5xx-rate-high`) angelegt; Kanaltest via SNS Publish durchgeführt.
- **`docs/BACKLOG.md`:** BL-08 auf „in Umsetzung“ gesetzt inkl. Blocker (kein bestätigter externer Subscriber) und konkreten Next Actions.
- **`docs/DEPLOYMENT_AWS.md` / `docs/OPERATIONS.md`:** Monitoring-Status auf tatsächlich angelegte Ressourcen aktualisiert; Setup-/Runbook-Kommandos ergänzt.

### Changed (2026-02-25 — BL-06/BL-07 Datenhaltung & API-Sicherheit abgeschlossen)
- **`docs/DATA_AND_API_SECURITY.md`:** Neu angelegt mit verbindlicher Entscheidung „stateless in dev“, definiertem DynamoDB-first-Pfad bei Persistenztriggern sowie AuthN/AuthZ-, Rate-Limit- und Secret-Handling-Standards für `/analyze`.
- **`docs/BACKLOG.md`:** BL-06 und BL-07 auf abgeschlossen gesetzt, Nachweis auf das neue Entscheidungsdokument verlinkt.
- **`docs/ARCHITECTURE.md` / `docs/DEPLOYMENT_AWS.md` / `README.md`:** Referenzen auf das neue Sicherheits-/Datenhaltungsdokument ergänzt.

### Changed (2026-02-25 — BL-05 Netzwerk-/Ingress-Zielbild abgeschlossen)
- **`docs/NETWORK_INGRESS_DECISIONS.md`:** Neu angelegt mit verifiziertem Ist-Stand (Default VPC/public subnets, SG-Ingress) und beschlossenem Zielbild (ALB vor ECS, private Tasks, Route53/ACM-Pflicht in `staging`/`prod`).
- **`docs/BACKLOG.md`:** BL-05 auf abgeschlossen gesetzt und Nachweisdokument verlinkt.
- **`docs/ARCHITECTURE.md`:** Architekturentscheid um Referenz auf Netzwerk-/Ingress-Zielbild ergänzt.
- **`README.md`:** Doku-Index und Projektbaum um `docs/NETWORK_INGRESS_DECISIONS.md` erweitert.

### Changed (2026-02-25 — BL-01 IaC dev Source-of-Truth abgeschlossen)
- **`infra/terraform/main.tf` / `variables.tf` / `outputs.tf` / `terraform.tfvars.example`:** Import-first-IaC auf dev-Kernressourcen erweitert (zusätzlich `aws_s3_bucket.dev`), Drift-arme Defaults an verifizierten Ist-Stand angepasst (`managed_by=openclaw`, Log Group `/swisstopo/dev/ecs/api`, Retention 30d, `ecs_container_insights_enabled=false`).
- **`infra/terraform/README.md`:** Runbook auf ECS+ECR+CloudWatch+S3 aktualisiert, inkl. verifiziertem Ist-Stand und Import-IDs.
- **`scripts/check_import_first_dev.sh`:** Read-only-Precheck um S3-Bucket erweitert; zusätzliche tfvars-Empfehlungen + Import-Kommando ergänzt.
- **`docs/BACKLOG.md`:** BL-01 auf abgeschlossen gesetzt, Nachweise (IaC-Artefakte + Deploy-Run) ergänzt.
- **`docs/DEPLOYMENT_AWS.md`:** BL-02/BL-01 Nachweisteile aktualisiert (Run `22417749775` und `22417939827` als erfolgreich, Terraform-Scope inkl. S3 + Precheck-Script).
- **`docs/ARCHITECTURE.md`:** IaC-Fundament von ECS/ECR/CloudWatch auf ECS/ECR/CloudWatch/S3 präzisiert.

### Added (2026-02-25 — GitHub App Auth Wrapper + Agent-Autopilot)
- **`scripts/gh_app_token.sh`:** Erzeugt on-demand GitHub App Installation Tokens aus `GITHUB_APP_ID`, `GITHUB_APP_INSTALLATION_ID`, `GITHUB_APP_PRIVATE_KEY_PATH`.
- **`scripts/gha`:** Wrapper für `gh` mit frischem App-Token (`GH_TOKEN`), damit CLI-Operationen ohne User-Login laufen.
- **`scripts/gpush`:** Wrapper für `git push` über HTTPS + App-Token (`x-access-token`), ohne persistente User-Credentials.
- **`docs/AUTONOMOUS_AGENT_MODE.md`:** Verbindlicher Arbeitsmodus für Nipa (Subagent-first, Parallelisierung, Modellvorgabe `openai-codex/gpt-5.3-codex` + `thinking=high` bei komplexen Aufgaben).
- **`README.md` / `docs/OPERATIONS.md`:** Verlinkung und Kurzreferenz auf den neuen Agent-Autopilot-Standard ergänzt.

### Changed (2026-02-25 — BL-03 OIDC Least-Privilege Korrektur)
- **`infra/iam/deploy-policy.json`:** ECS-Leserechte präzisiert; `ecs:DescribeTaskDefinition` auf `Resource: "*"` umgestellt (kompatibel mit API-IAM-Evaluierung), `ecs:DescribeServices` scoped auf dev-Service belassen.
- **AWS IAM (live):** `swisstopo-dev-github-deploy-policy` auf Version `v2` aktualisiert und als Default gesetzt.
- **`docs/DEPLOYMENT_AWS.md` / `docs/BACKLOG.md`:** Validierungsstand ergänzt; ehemals fehlerhafter Deploy-Schritt `Register new task definition revision` im Run `22417749775` als erfolgreich dokumentiert.

### Changed (2026-02-25 — CI/CD Doku auf OIDC aktualisiert)
- **`README.md`:** Falsche ECS-Deploy-Voraussetzung mit statischen AWS-Secrets entfernt; OIDC-Role-Assume als aktueller Standard dokumentiert.
- **`docs/DEPLOYMENT_AWS.md`:** GitHub-Secrets-Sektion auf OIDC-Realität korrigiert (`keine AWS Access Keys erforderlich`), OIDC-Role-ARN + Verweis auf Minimalrechte ergänzt.
- **`docs/ARCHITECTURE.md`:** Abschnitt „Secrets & Variables“ auf OIDC umgestellt (keine statischen AWS-Keys, Role-Assume dokumentiert).

### Changed (2026-02-25 — BL-02 CI/CD-Deploy-Verifikation)
- **`.github/workflows/deploy.yml`:** Push-Trigger auf `main` wieder aktiviert (zusätzlich zu `workflow_dispatch`), damit BL-02 per Commit/Push verifiziert werden kann.
- **`.github/workflows/deploy.yml`:** ECR-Image-URI auf feste AWS Account ID (`523234426229`) umgestellt, um leere `AWS_ACCOUNT_ID`-Repo-Variable im Build-Schritt zu umgehen.
- **`docs/DEPLOYMENT_AWS.md`:** Verifikationsnachweis mit Run-URLs ergänzt (`22416418587`, `22416878804`, `22416930879`) inkl. Ergebnis und Schrittstatus (`services-stable`, Smoke-Test `/health`).

### Added (2026-02-25 — Terraform IaC-Fundament für dev)
- **`infra/terraform/`:** Minimales Terraform-Startpaket ergänzt (`versions.tf`, `providers.tf`, `variables.tf`, `main.tf`, `outputs.tf`, `terraform.tfvars.example`).
- **`infra/terraform/README.md`:** Sicheres Import-first-Runbook ergänzt (`init` → `plan` → `import` → `apply`) inkl. Hinweise zu bestehenden dev-Ressourcen.
- **`docs/DEPLOYMENT_AWS.md`:** Terraform-Startpaket und sichere Reihenfolge (`init/plan/import/apply`) dokumentiert.
- **`docs/ARCHITECTURE.md`:** IaC-Fundament als aktueller Architekturbaustein ergänzt.

### Added (2026-02-25 — Container + Webservice MVP)
- **`Dockerfile`:** Container-Build für ECS/Fargate ergänzt (Python 3.12, Port 8080).
- **`src/web_service.py`:** Minimaler HTTP-Service mit Endpoints `/health`, `/version`, `/analyze`.

### Added (2026-02-25 — BL-03 Least-Privilege IAM Vorarbeit)
- **`infra/iam/deploy-policy.json`:** Konkrete Least-Privilege-Policy für den aktuellen ECS/ECR-dev-Deploypfad ergänzt (inkl. `iam:PassRole` nur für Task/Execution-Role).
- **`infra/iam/README.md`:** Herleitung aus GitHub-Workflow, sichere Migrationsreihenfolge ohne Breaking Change und read-only Drift-Check-Notizen ergänzt.

### Changed (2026-02-25 — BL-03 Statusdoku aktualisiert)
- **`docs/DEPLOYMENT_AWS.md`:** IAM-Sektion auf workflow-basierte Minimalrechte umgestellt und auf neue Artefakte unter `infra/iam/` verlinkt; Hinweis auf risikoarme Umsetzung (keine sofortige Secret-Umschaltung) ergänzt.
- **`docs/BACKLOG.md`:** BL-03 mit Statusnotiz „Track D Vorarbeit“ ergänzt (erledigte Vorarbeiten + offene Restschritte bis Done).

### Changed (2026-02-25 — ECS Deploy Workflow umgesetzt)
- **`.github/workflows/deploy.yml`:** Deploy-Job auf ECS/Fargate (dev) konkretisiert: ECR Login, Docker Build+Push, neue ECS Task-Definition registrieren, Service-Update, Stabilitäts-Wait.
- **`README.md`:** CI/CD-Sektion auf ECS-Deploy aktualisiert inkl. benötigter GitHub Secrets/Variables.
- **`README.md`:** Lokale Docker-/Webservice-Nutzung dokumentiert.
- **`docs/DEPLOYMENT_AWS.md`:** Stack-Entscheid auf ECS/Fargate dokumentiert; Runtime-Konvention (Port 8080, Healthcheck) ergänzt.

### Changed (2026-02-25 — Lizenzstatus korrigiert)
- **README.md:** Lizenz-Badge von `MIT` auf `proprietär` geändert.
- **README.md:** Lizenzsektion auf „vorerst proprietär (alle Rechte vorbehalten)“ umgestellt; Verweis auf nicht vorhandene `LICENSE`-Datei entfernt.

### Changed (2026-02-25 — CI/CD Workflow aktiviert)
- **`.github/workflows/deploy.yml`:** Workflow aus `scripts/ci-deploy-template.yml` nach `.github/workflows/` überführt und aktiviert. Trigger: ausschliesslich `workflow_dispatch` (manuell). Auto-Trigger (push/release) bleibt deaktiviert bis Secrets und Stack-Schritte konfiguriert sind. Keine Secrets eingetragen.
- **`README.md`:** CI/CD-Badge und neue Sektion „CI/CD" mit Setup-Checkliste ergänzt; Verzeichnisbaum aktualisiert.

### Changed (2026-02-25 — Doku-Update: AWS-Naming, Tagging, Umgebungen)
- **DEPLOYMENT_AWS.md:** Neue Sektion „Tagging Standard" mit verbindlichen AWS-Tags (`Environment=dev`, `ManagedBy=openclaw`, `Owner=nico`, `Project=swisstopo`)
- **DEPLOYMENT_AWS.md:** Ist-Stand-Ressourcen (`swisstopo-dev-*`) als verifiziert eingetragen; ECS/ECR-Befehle auf korrekte Cluster-/Service-Namen aktualisiert
- **DEPLOYMENT_AWS.md:** Klarstellung: AWS-Naming `swisstopo` ist intern und intentional; keine Umbenennung nötig
- **DEPLOYMENT_AWS.md:** Explizit festgehalten: nur `dev`-Umgebung vorhanden; `staging` und `prod` noch nicht aufgebaut
- **ARCHITECTURE.md:** Swisstopo-Ressourcen korrekt als Ressourcen dieses Projekts (nicht Schwesterprojekt) eingetragen; Naming-Konvention und Umgebungs-Status ergänzt
- **README.md:** Hinweise zu AWS-Naming (`swisstopo`) und aktuellem Umgebungs-Stand (`dev` only) ergänzt
- **OPERATIONS.md:** Hinweise zu Umgebung (`dev` only) und AWS-Naming an prominenter Stelle ergänzt; Post-Release-Checkliste auf `dev`-Deployment angepasst

### Changed (2026-02-25 — ECS Smoke-Test + Push-Trigger)
- **`.github/workflows/deploy.yml`:** Trigger für Push auf `main` aktiviert (zusätzlich zu `workflow_dispatch`).
- **`.github/workflows/deploy.yml`:** Nach `aws ecs wait services-stable` Smoke-Test auf `SERVICE_HEALTH_URL` ergänzt (HTTP-Check auf `/health`); bei fehlender/leer gesetzter Variable wird der Schritt mit Notice übersprungen.
- **`README.md`:** CI/CD-Beschreibung auf aktiven Push-Trigger aktualisiert; neue Variable `SERVICE_HEALTH_URL` dokumentiert.
- **`docs/DEPLOYMENT_AWS.md`:** Workflow-Trigger, Smoke-Test-Schritt und Variable `SERVICE_HEALTH_URL` ergänzt.

### Changed (2026-02-25 — Architektur-Doku auf Ist-Stand gebracht)
- **`docs/ARCHITECTURE.md`:** Von Planungsstand auf aktuellen MVP-Betriebsstand aktualisiert (ECS/Fargate Deploy via GitHub Actions, Trigger, Webservice-Endpunkte, Task-Definition-Update-Flow, optionale Smoke-Tests, relevante GitHub Secrets/Variables).

### Changed (2026-02-25 — Backlog-Konsolidierung)
- **`docs/BACKLOG.md`:** Neu angelegt; alle offenen Punkte aus README + `docs/*.md` in priorisierten, umsetzbaren Backlog überführt (P0/P1/P2, Aufwand, Abhängigkeiten, Akzeptanzkriterien).
- **`docs/ARCHITECTURE.md`:** Redundante Liste „Offene Punkte“ auf zentrale Backlog-Pflege umgestellt.
- **`docs/DEPLOYMENT_AWS.md`:** Redundante TODO-Liste auf zentrale Backlog-Pflege umgestellt.
- **`docs/OPERATIONS.md`:** Verweis auf zentrale Backlog-Pflege ergänzt; lokaler TODO-Hinweis im Setup auf Backlog referenziert.
- **`README.md`:** Dokumentationsübersicht um `docs/BACKLOG.md` ergänzt.

### Changed (2026-02-25 — Monitoring/Alerting MVP für ECS)
- **`docs/OPERATIONS.md`:** Monitoring-MVP ergänzt (CloudWatch Log Group + Retention-Standard, minimale Alarmdefinitionen, HTTP-Health-Check-Guidance, Incident-Runbook mit konkreten AWS-CLI-Kommandos).
- **`docs/DEPLOYMENT_AWS.md`:** Monitoring-Status auf MVP-Stand aktualisiert; Teilfortschritt für BL-08 dokumentiert (inkl. klarer Restarbeiten).

### Added (2026-02-25 — Read-only Ops Scripts)
- **`scripts/check_ecs_service.sh`:** Read-only ECS-Triage-Helper (Service-Status, letzte Events, laufende Tasks/Containerzustände).
- **`scripts/tail_logs.sh`:** Read-only CloudWatch-Log-Tail-Helper (Region/LogGroup/Since/Follow parametrisierbar).

### Changed (2026-02-25 — BL-04 Tagging-Audit abgeschlossen)
- **`docs/TAGGING_AUDIT.md`:** Neu angelegt mit Inventar und Audit-Tabelle für dev-Ressourcen (ECS Cluster/Service, Task Definition Family inkl. aktiver Revisionen, ECR, relevante CloudWatch Log Groups).
- **AWS Ressourcen:** Fehlende Standard-Tags (`Environment`, `ManagedBy`, `Owner`, `Project`) auf aktiven ECS Task Definitions `swisstopo-dev-api:1` bis `:10` ergänzt (nicht-destruktiv).
- **`docs/BACKLOG.md`:** BL-04 auf „abgeschlossen“ gesetzt und auf Audit-Dokument verlinkt.

---

## [0.1.0] — 2026-02-25

### Added
- Initial Commit: Repository-Grundstruktur angelegt

[Unreleased]: https://github.com/nimeob/geo-ranking-ch/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/nimeob/geo-ranking-ch/releases/tag/v0.1.0
