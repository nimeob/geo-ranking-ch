# Night Worker Log — 2026-03-24

## 00:35 CET — CI/UI canonical-host hardening (in progress)
- Basis geprüft: `origin/main` ist auf `37c9e64` (PR #1477 bereits gemerged, Deploy grün).
- Live-Check DEV per curl durchgeführt:
  - `https://www.dev.georanking.ch/healthz` = 200
  - `https://www.dev.geo-ranking.ch/healthz` = 200
  - Alias-Login (`www.dev.geo-ranking.ch/login?...start=1`) liefert `307` auf kanonische Domain.
- Browser-Tool-Check versucht, aber OpenClaw Browser-Gateway timeout; daher auf CLI-/HTTP-Smokes ausgewichen.

## 00:48 CET — Umsetzung
- Neues Smoke-Skript hinzugefügt: `scripts/smoke/check_ui_canonical_redirect.py`
  - Prüft Alias-Host → Canonical-Host Redirect-Vertrag für `/login?...&start=1` inkl. Query-Erhalt.
  - Unterstützt Retry-Budget und JSON-Artefakt-Ausgabe.
  - Behandelt fehlende Alias-Hosts als expliziten `skipped_no_alias_hosts` (exit 0).
- Workflows erweitert:
  - `.github/workflows/deploy.yml`
  - `.github/workflows/deploy-staging.yml`
  - Neuer Step: **Smoke-Test UI canonical-host redirect**
  - Artefaktpfade ergänzt:
    - `artifacts/dev-canonical-host-redirect-smoke.json`
    - `artifacts/staging-canonical-host-redirect-smoke.json`
- Testabdeckung ergänzt:
  - `tests/test_check_ui_canonical_redirect.py`
  - `tests/test_deploy_version_trace_docs.py` um Canonical-Host-Smoke-Guardrails erweitert.

## 00:52 CET — Verifikation
- `pytest -q tests/test_check_ui_canonical_redirect.py tests/test_deploy_version_trace_docs.py` → **23 passed**.
- `pytest -q tests/test_check_ui_login_start.py tests/test_check_ui_canonical_redirect.py tests/test_deploy_version_trace_docs.py` → **46 passed**.
- Live-Skriptcheck DEV:
  - `python3 scripts/smoke/check_ui_canonical_redirect.py --base-url https://www.dev.georanking.ch --canonical-origin https://www.dev.georanking.ch --canonical-hosts 'www.dev.geo-ranking.ch,www.dev.georanking.ch'`
  - Ergebnis: `{"ok": true, "reason": "ok", "status_code": 307, ...}`.

## 01:12 CET — Canonical-host Parser-Hardening + Live-Recheck
- ROI-Strang fortgeführt: Parser-Hardening für Canonical-Host-Konfiguration, damit `UI_CANONICAL_HOSTS` robust bleibt, auch wenn Einträge versehentlich als volle Origins/mit Port gesetzt werden.
- Änderungen umgesetzt:
  - `src/ui/service.py`
    - `_normalize_host(...)` nutzt jetzt URL-Parsing statt `split(':', 1)`.
    - Ergebnis: Host-Normalisierung funktioniert für `host:port` **und** `https://host[:port]` korrekt.
  - `scripts/smoke/check_ui_canonical_redirect.py`
    - neue Host-Normalisierung für `--canonical-hosts` (Origin-/Port-Inputs werden korrekt auf Host reduziert).
    - Canonical-Host-Vergleich nutzt dieselbe robuste Normalisierung.
  - Tests erweitert:
    - `tests/test_ui_service.py::UiCanonicalConfigTests`
    - `tests/test_check_ui_canonical_redirect.py`
- Verifikation lokal:
  - `.venv/bin/python -m pytest -q tests/test_check_ui_canonical_redirect.py tests/test_ui_service.py::UiCanonicalConfigTests` → **9 passed**.
  - `python3 -m compileall -q src/ui/service.py scripts/smoke/check_ui_canonical_redirect.py` → **ok**.
- Live-UI-Checks DEV (CLI, da Browser-Gateway weiter timeout):
  - `python3 scripts/smoke/check_ui_canonical_redirect.py --base-url https://www.dev.georanking.ch --canonical-origin https://www.dev.georanking.ch --canonical-hosts 'www.dev.geo-ranking.ch,www.dev.georanking.ch' --next '/results/demo-result' --reason 'night_worker_probe'` → **ok=true, status_code=307**.
  - `https://www.dev.geo-ranking.ch/healthz` → **200** (kein Redirect, wie erwartet).
  - `https://www.dev.geo-ranking.ch/results/demo-result?from=night-worker` → **307** auf `https://www.dev.georanking.ch/...`.

## 02:15–02:22 CET — BFF-Guard Hardening: Callback ebenfalls Host-trusted fail-closed
- Security-Gap geschlossen: `/auth/callback` wurde bisher mit Proxy-Marker akzeptiert, auch wenn `X-Forwarded-Host` untrusted war (Login/Logout waren bereits geschützt).
- Änderung:
  - `src/api/web_service.py`
    - Trust-Guard auf **alle drei** BFF-Routen erweitert: `/auth/login`, `/auth/logout`, `/auth/callback`.
- Tests erweitert/angepasst:
  - `tests/test_web_service_bff_gui_guard.py`
    - neuer Regressionstest: callback + untrusted forwarded host ⇒ `403 external_direct_login_disabled`.
    - bestehender Callback-Error-Test auf trusted host + scheme mismatch umgestellt (Diagnostik bleibt sichtbar, ohne den neuen Trust-Guard zu umgehen).
- Verifikation:
  - `pytest -q tests/test_web_service_bff_gui_guard.py` → **18 passed**
  - `pytest -q tests/test_web_service_phase1_auth.py tests/test_web_service_oidc_loader.py tests/test_ui_service.py` → **32 passed**
- UI-Beobachtung/Blocker:
  - Browser-Tool weiterhin nicht nutzbar (Gateway timeout). Aktiv versucht zu entstören via `openclaw gateway status/restart`; CLI meldet Runtime-/Config-Anomalie, RPC probe zwar `ok`, Browser-Control aber weiter timeout. Daher weiterhin CLI-smokes als Fallback.

## 2026-03-24 02:58 CET — Auth-Proxy Guard Smoke hardening (ROI: deploy regression coverage)
- Entscheidung: statt weiterer UI-Flicker-Suche ein messbares Deploy-Gate ergänzt, das die zuletzt gefixten `X-Forwarded-Host`-Guards auf `/auth/login|logout|callback` live absichert.
- Neue Smoke-Check-Implementierung: `scripts/smoke/check_bff_auth_proxy_guard.py` (trusted login-redirect + untrusted/chain fail-closed Assertions).
- CI-Verdrahtung erweitert in `deploy.yml` und `deploy-staging.yml`; Artifact ergänzt: `*-auth-proxy-guard-smoke.json`.
- Tests ergänzt/aktualisiert: `tests/test_check_bff_auth_proxy_guard.py`, `tests/test_deploy_version_trace_docs.py`.
- Verifikation lokal: `pytest -q tests/test_check_bff_auth_proxy_guard.py tests/test_deploy_version_trace_docs.py` → 23 passed.
- Live-dev Probe: `check_bff_auth_proxy_guard.py --api-base-url https://api.dev.georanking.ch --ui-base-url https://www.dev.georanking.ch` → ok (alle 6 Checks grün).
- Zusatz-UI-Verifikation: login-start bundle + canonical redirect smoke gegen `https://www.dev.georanking.ch` erneut grün.
- Push: `night/worker-20260324-0246` @ `8332928`.
- PR: #1483 "Deploy smoke: add auth-proxy forwarded-host guard coverage".

## 03:49 CET — Live-Deploy-Verifikation + Browser-Blocker aktiv abgefangen
- Laufenden Scheduled Deploy-Run `23470675695` (main, Deploy to AWS dev) bis Abschluss überwacht; Ergebnis **grün** inkl. Login-Start- und Auth-Proxy-Smokes.
- Browser-UI-Tool blieb blockiert (Gateway-Start timeout / `openclaw gateway restart` Config-Fehler), daher gezielt auf CLI-smokes gewechselt statt auf blindes Warten.

## 03:58 CET — Login-start Smoke gegen Query-Only "authorize" gehärtet
- ROI-Entscheidung: False-Positive-Lücke im Smoke-Parser geschlossen (`check_ui_login_start.py` akzeptierte bisher auch Redirects, die "authorize" nur im Query trugen).
- Umsetzung: `_is_authorize_redirect` prüft jetzt nur noch den Redirect-**Pfad**; Tests in `tests/test_check_ui_login_start.py` für Entry+Start ergänzt.

## 04:02 CET — Re-Tests + Live-Verifikation DEV
- Lokal erfolgreich: `pytest -q tests/test_check_ui_login_start.py` (25 passed) sowie Contract-Suite `tests/test_run_login_start_smoke_bundle_script_contract.py tests/test_run_deploy_smoke.py` (11 passed).
- Live DEV erneut geprüft: `run_login_start_smoke_bundle.sh` und `check_bff_auth_proxy_guard.py` gegen `www.dev.georanking.ch`/`api.dev.georanking.ch` beide **ok**; Artefakte unter `artifacts/nightly-20260324-024611-after-authz-path-fix/`.

## 07:05 CET — Retry-After HTTP-date Regression-Gap geschlossen (ROI)
- Fokus: letzte Smoke-Hardening-Welle auf **Regression-Schutz** erweitert, damit `Retry-After` im RFC-Date-Format nicht unbemerkt kaputtgeht.
- Ergänzt in Tests:
  - `tests/test_check_ui_canonical_redirect.py`
    - HTTP-date `Retry-After` wird geparst und durch `--max-retry-delay` gecappt.
    - Stale HTTP-date fällt auf Default-Retry-Delay zurück.
  - `tests/test_check_bff_auth_proxy_guard.py`
    - gleiche zwei Fälle (cap + stale fallback) für Auth-Proxy-Guard-Smoke.
- Verifikation lokal:
  - `/data/.openclaw/workspace/geo-ranking-ch/.venv/bin/pytest -q tests/test_check_ui_canonical_redirect.py tests/test_check_bff_auth_proxy_guard.py` → **23 passed**.
- Live-DEV Re-Checks (UI-/BFF-nah) durchgeführt:
  - `check_ui_canonical_redirect.py` gegen `www.dev.georanking.ch`/Alias → **ok=true, status=307**.
  - `check_bff_auth_proxy_guard.py` gegen `api.dev.georanking.ch` + UI-Origin → **ok=true** (alle 6 Checks grün).
  - Artefakte: `artifacts/nightly-20260324T060411Z/`.

## 07:40 CET — Login-start Smoke für Canonical-Host-Hop robust gemacht (ROI)
- Beobachteter Blocker reproduziert: `check_ui_login_start.py` schlug für Alias-Entrypoint `https://www.dev.geo-ranking.ch` fehl (`entry_redirect_non_login_target`), weil der erste Hop legitimer `307` auf den kanonischen Host (`www.dev.georanking.ch`) war.
- Umsetzung (Branch `fix/login-smoke-canonical-host-hop`):
  - `scripts/smoke/check_ui_login_start.py`
    - neue Erkennung `_is_same_login_entry_redirect(...)` für legitime `/login`-Weiterleitungen mit identischem `next/reason` (optional `start=1`).
    - `check_login_entry(...)` folgt genau einem solchen Canonical-Hop und validiert danach wie bisher (`/auth/login` oder `authorize`).
    - `check_login_start(...)` folgt ebenfalls einem legitimen Canonical-Hop für `start=1`, bevor der auth/login/authorize-Vertrag geprüft wird.
    - Diagnostik (`request_url`) zeigt den tatsächlich geprüften finalen Hop.
  - `tests/test_check_ui_login_start.py`
    - neue Regressionstests für Entry- und Start-Phase mit vorgeschaltetem Canonical-Hop.
- Verifikation lokal:
  - `/data/.openclaw/workspace/geo-ranking-ch/.venv/bin/python -m pytest -q tests/test_check_ui_login_start.py` → **34 passed**.
  - `python3 -m compileall -q scripts/smoke/check_ui_login_start.py` → **ok**.
- Live-DEV Re-Tests:
  - `python3 scripts/smoke/check_ui_login_start.py --base-url https://www.dev.geo-ranking.ch --expected-authorize-host auth.dev.georanking.ch,www.dev.georanking.ch --next /gui` → **ok=true** (vorher fail).
  - `python3 scripts/smoke/check_ui_login_start.py --base-url https://www.dev.georanking.ch --expected-authorize-host auth.dev.georanking.ch,www.dev.georanking.ch --next /gui` → **ok=true**.
  - Artefakte: `artifacts/nightworker/20260324T0740Z-dev-login-alias-after-fix.json`, `artifacts/nightworker/20260324T0741Z-dev-login-main-after-fix.json`.
