# Testing Catch-up: Regression + Smoke Priorisierung (Issue #337)

## Zielbild für den nächsten Sprint
Der Catch-up fokussiert auf zwei Ebenen:

1. **Regression (Plan-/Balance-Logik stabil halten)**
2. **Smoke (BL-31 UI/API-Runtime-Pfade frühzeitig absichern)**

Damit bleibt der bereits erreichte Workstream-Balance-Stand belastbar, während BL-31-Folgearbeit (#329/#330/#331) nicht ohne Testleitplanken startet.

## Priorisierte Szenarien

### P1 — Regression (zuerst)
1. `test_build_workstream_catchup_plan_returns_minimal_delta_per_category`
   - schützt die Delta-Plan-Berechnung aus #335
2. `test_print_workstream_balance_report_json_renders_machine_readable_payload`
   - schützt den maschinenlesbaren Report-Pfad (`--print-workstream-balance --format json`)

### P1 — Smoke (direkt danach)
3. `TestBl31RoutingTlsSmokeScript::test_smoke_baseline_mode_is_reproducible_with_structured_output`
   - prüft reproduzierbaren Baseline-Smoke mit strukturierter Evidenz
4. `TestBl31RoutingTlsSmokeScript::test_strict_mode_matches_cors_baseline_result`
   - stellt den Strict-Gate-Pfad für #329/#330 deterministisch sicher

## Feste pytest-Sequenz (verbindlich)

```bash
./scripts/check_testing_catchup_sequence.sh
```

Der Runner kapselt die Reihenfolge explizit und ist für lokale Läufe sowie CI-nahe Verifikation gedacht.

## QA-Validierungsschritt (Abschlussnachweis)
Ein Catch-up-Lauf gilt erst als abgeschlossen, wenn **alle drei** Nachweise im Issue-/PR-Kommentar stehen:

1. **Runner-Nachweis**
   - Kommando: `./scripts/check_testing_catchup_sequence.sh`
   - Erwartung: `testing catch-up sequence: PASS`
2. **BL-31 Smoke-Referenzstatus**
   - Verweis auf `docs/testing/bl31-routing-tls-smoke-catchup.md`
   - Angabe, ob Strict-Modus aktuell blockiert oder grün ist (abhängig von #329/#330)
3. **Backlog-/Parent-Sync**
   - `docs/BACKLOG.md` aktualisiert
   - Parent-Checklist (falls vorhanden) synchronisiert

## Referenzen
- `scripts/check_testing_catchup_sequence.sh`
- `tests/test_github_repo_crawler.py`
- `tests/test_bl31_routing_tls_smoke_script.py`
- `docs/testing/bl31-routing-tls-smoke-catchup.md`
