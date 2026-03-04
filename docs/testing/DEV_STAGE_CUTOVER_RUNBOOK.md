# Dev→Stage Cutover Runbook (kanonisch)

Status: 2026-03-04  
Owner-Issue: #1175  
Gilt für: Dev→Stage-Cutover im API/UI-Entkopplungsstrang

## 1) Ziel, Scope, Stop-Regel

Dieses Runbook ist die **eine kanonische Ausführungsdatei** für den Dev→Stage-Cutover.

- Ziel: reproduzierbarer Go/No-Go-Entscheid mit klaren Gates, harten Rollback-Triggern und Nachweisführung.
- Scope: Dev→Stage (kein Prod-Rollout).
- Stop-Regel: Bei einem roten Pre-Gate oder hartem Rollback-Trigger wird **kein Cutover** freigegeben.

## 2) Rollen & SLA

- **Incident Commander (IC):** Release-Verantwortung, Go/No-Go, Rollback-Freigabe
- **Operator:** führt Kommandos aus, dokumentiert Outputs
- **Observer:** validiert Ergebnisse und Log-Konsistenz
- **SLA bei Trigger:** Entscheidung „weiter vs rollback" in **<= 10 Minuten**

## 3) Pre-Gates (verbindlich)

> Jeder Gate hat genau ein Primary-Verify-Kommando (+ optional 1 Fallback).  
> Erwartete Ausgabe muss im Cutover-Log dokumentiert werden.

### Gate 1 — Auth-Smoke (UI-Login + Session-Check 200)

**Primary Verify**

```bash
./.venv/bin/python -m pytest -q \
  tests/test_auth_regression_smoke_issue_1019.py::TestAuthRegressionSmokeIssue1019::test_login_search_ranking_logout_regression_smoke
```

Erwartung (PASS):
- Exit-Code `0`
- `1 passed` im Pytest-Output
- enthaltene Assertions decken UI-Login-Flow + Session-/Auth-Checks ab

FAIL:
- Exit-Code `!= 0` oder fehlendes `1 passed`

**Fallback (optional)**

```bash
./.venv/bin/python -m pytest -q \
  tests/test_web_service_bff_gui_guard.py::TestWebServiceBffGuiGuard::test_gui_redirects_to_login_when_no_session \
  tests/test_web_service_bff_gui_guard.py::TestWebServiceBffGuiGuard::test_history_redirect_preserves_next_query
```

---

### Gate 2 — Kritischer UI-Happy-Path vollständig durchlaufbar

**Primary Verify**

```bash
./scripts/run_webservice_e2e.sh
```

Erwartung (PASS):
- Exit-Code `0`
- lokale E2E-Suite inkl. Auth-/Analyze-Happy-Path ohne ungeklärte Fehler

FAIL:
- Exit-Code `!= 0` oder reproduzierbarer Bruch im UI-Happy-Path

**Fallback (optional)**

```bash
./.venv/bin/python -m pytest -q tests/test_history_navigation_integration.py
```

---

### Gate 3 — Dev-Error-Rate über 10 Minuten < 1%

**Primary Verify**

```bash
DEV_BASE_URL="${DEV_BASE_URL:?set DEV_BASE_URL}" \
STABILITY_RUNS=40 \
STABILITY_INTERVAL_SECONDS=15 \
STABILITY_MAX_FAILURES=0 \
./scripts/run_remote_api_stability_check.sh
```

Erwartung (PASS):
- Exit-Code `0`
- im Report (`artifacts/bl18.1-remote-stability.ndjson`) Fehlerrate `< 1%`
  (bei 40 Läufen bedeutet das: **0 Fehlläufe**)

FAIL:
- Exit-Code `!= 0` oder Fehlerrate `>= 1%`

**Fallback (optional)**

```bash
DEV_BASE_URL="${DEV_BASE_URL:?set DEV_BASE_URL}" \
./scripts/run_remote_api_smoketest.sh
```

## 4) Linearer Cutover-Ablauf (Stop/Go)

| Schritt | Owner | Erwartete Dauer | Ausführung | Stop/Go-Regel |
|---|---|---:|---|---|
| 0 | IC | 5 min | Scope + Change-Fenster + Kommunikationskanal bestätigen | Stop, wenn Zuständigkeiten unklar |
| 1 | Operator | 10 min | Gate 1 ausführen und protokollieren | Nur bei PASS weiter |
| 2 | Operator | 15 min | Gate 2 ausführen und protokollieren | Nur bei PASS weiter |
| 3 | Operator | 12 min | Gate 3 (10-Minuten-Fenster) ausführen | Nur bei PASS weiter |
| 4 | IC | 3 min | Go/No-Go auf Basis Gate 1-3 | Go nur bei 3/3 PASS |
| 5 | Operator | 5 min | Stage-Cutover gemäß Deployment-Workflow starten | Bei Fehler sofort Trigger-Prüfung |
| 6 | Observer | 15 min | Post-Cutover-Checks Minute 5/10/15 | Bei Trigger sofort Rollback-Pfad |

## 5) Rollback (harte Trigger + Minimalpfad)

### Harte Trigger (mind. einer reicht)

1. Gate 1 oder Gate 2 schlägt fehl (kein valider UI/Auth-Happy-Path)
2. Gate 3 oder Post-Cutover-Checks zeigen Fehlerquote `>= 1%`
3. Auth-Smoke nach Cutover liefert nicht stabil `200` auf Session-/Protected-Checks

### Minimalpfad (linear, verpflichtend)

1. **Trigger erkannt** (T0)
2. **Entscheidung <= 10 Min** durch IC: rollback erforderlich ja/nein
3. **Rücksetzschritte ausführen** (letzten stabilen Stage-Stand wiederherstellen)
4. **Auth-Smoke Re-Check** (Gate 1 Primary erneut laufen lassen)
5. Ergebnis + Zeitstempel im Cutover-Log dokumentieren

## 6) Post-Cutover-Checks (Minute 5/10/15)

| Zeitpunkt | Check | PASS | FAIL |
|---|---|---|---|
| +5 min | Auth + kritischer UI-Pfad | Gate 1/2 bleiben grün | sofort Trigger 1 |
| +10 min | Fehlerquote | `< 1%` im laufenden Fenster | sofort Trigger 2 |
| +15 min | Stabilität + Nutzerfluss | keine neuen roten Signale | Trigger + Rollback-Pfad |

## 7) Kompaktes Dry-Run-Protokoll (Dev)

> Format verbindlich: Zeitstempel, Ergebnis je Gate, Go/No-Go, Follow-ups.

| Zeitstempel (UTC) | Gate 1 | Gate 2 | Gate 3 | Entscheidung | Follow-ups |
|---|---|---|---|---|---|
| 2026-03-04T16:20:00Z | PASS | PASS | NO-GO (fehlende DEV_BASE_URL auf Runner) | NO-GO | `DEV_BASE_URL` + Auth-Secret im Runner ergänzen, Dry-Run erneut durchführen |

## 8) Evidenz-Checkliste (pro Cutover ausfüllen)

- [ ] Gate-Outputs/Exit-Codes gespeichert
- [ ] Go/No-Go mit IC-Namen + Zeit dokumentiert
- [ ] (Falls ausgelöst) Rollback-Entscheid innerhalb 10 Minuten dokumentiert
- [ ] Post-Cutover Minute 5/10/15 protokolliert
- [ ] Verweis auf Artefakte/Logs im zugehörigen Issue/PR ergänzt
