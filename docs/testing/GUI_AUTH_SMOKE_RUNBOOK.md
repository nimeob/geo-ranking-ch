# GUI Auth Smoke Runbook (Login/Logout/Session-Expiry)

**Issue:** [#954](https://github.com/nimeob/geo-ranking-ch/issues/954)  
**Parent:** [#948](https://github.com/nimeob/geo-ranking-ch/issues/948)  
**Ziel:** Reproduzierbarer Smoke-/Abnahmeablauf für GUI-Auth-UX (BFF + OIDC), damit Login/Logout/Session-Expiry vor Merge systematisch geprüft werden können.

---

## 1) Scope

Dieses Runbook prüft den GUI-Auth-MVP-End-to-End:

- Redirect auf Login bei nicht authentifizierter GUI-Nutzung
- Erfolgreicher Login-Flow (OIDC via BFF)
- Nutzbarkeit von `/analyze` und `/analyze/history` aus der GUI nach Login
- Robuster Logout
- Session-Expiry/invalid Session als Negative-Flow

Nicht im Scope:

- Tiefgehende Provider-/Cognito-Konfiguration (siehe `../OIDC_COGNITO_STAGING_RUNBOOK.md`)
- Last-/Performance-Tests
- Vollständige API-Funktionstests außerhalb GUI-Auth

### 1.1 Automatisierte Guard-/Session-Regression (WP #997)

Vor oder parallel zum manuellen Smoke soll die folgende Regression laufen:

```bash
python3 -m pytest -q tests/test_web_service_bff_gui_guard.py tests/test_bff_integration.py
```

Diese Suite deckt insbesondere ab:
- Protected-Route-Redirects (`/gui`, `/history`) auch bei ungültigem Session-Cookie
- Session-basierte BFF-Delegation für `GET /portal/api/analyze/history`
- Session-basierte BFF-Delegation für `POST /portal/api/analyze` (inkl. CSRF-Header-Pfad)

### 1.2 Automatisierter Auth/Core-Flow-Regression-Smoke (WP #1019 / #1087 / #1116)

Für den vollständigen Kernpfad `login -> protected route -> logout -> relogin` gibt es einen reproduzierbaren Integration-Smoke:

```bash
python3 -m pytest -q tests/test_auth_regression_smoke_issue_1019.py
```

Abdeckung:
- unauthenticated `/gui` Redirect auf `/auth/login`
- `/auth/login` + `/auth/callback` Session-Aufbau inkl. Cookie-Set
- `/auth/me` 200 nach Login
- authentifizierte `/gui`-Shell mit stabilen Selektoren (`#analyze-form`, `#query`, `#submit-btn`, `#results-list`, `#results-body`)
- `POST /analyze` (deterministische Smoke-Query `__ok__`) + `GET /analyze/history` 200
- Öffnen der Ranking-/Result-Ansicht über `/results/<result_id>` inkl. stabiler Tab-Selektoren
- `/auth/logout` Redirect + Cookie-Clear + `/auth/me` 401 nach Logout
- Re-Login nach Logout bleibt stabil (`next=/history` wird wiederhergestellt)
- Failure-Modes ohne Redirect-Loop: `invalid_state`, `consent_denied`, `session_expired`
- CI-Guardrail: **kein API-Host im browser-sichtbaren Auth-Flow** (Login/Callback/Logout/Error-CTA)

Hinweis: Der Smoke ist in den PR-Required-Gate (`dev-smoke-required` via `check_bl334_split_smokes.sh`) eingebunden und bleibt zusätzlich über `scripts/run_webservice_e2e.sh` lokal ausführbar. Der bisherige Pfad `login -> analyze/history -> logout` bleibt als Teilmenge des erweiterten Kernpfads erhalten.

Bei Failures schreibt `check_bl334_split_smokes.sh` automatisch Debug-Artefakte nach `reports/evidence/core-flow-smoke/<STAMP>/` (mindestens `core-flow-failure-trace.md` und – falls Chromium verfügbar – `core-flow-failure-gui.png`). Damit sind Fehler im Kernfluss direkt mit Trace/Screenshot belegbar.

Aktueller Referenzlauf (Issue #1253): `reports/evidence/issue-1253-auth-no-api-host-guard-20260304T233008Z.md`.

---

## 2) Standardisierte Evidence-Pfade

Lege pro Lauf einen Zeitstempel an und sammle alle Nachweise unter:

- `reports/evidence/gui-auth-smoke/<STAMP>/preflight.md`
- `reports/evidence/gui-auth-smoke/<STAMP>/positive-flow.md`
- `reports/evidence/gui-auth-smoke/<STAMP>/negative-flow.md`
- `reports/evidence/gui-auth-smoke/<STAMP>/rollback-check.md`

Empfohlener `STAMP`: UTC-Format `YYYYMMDDTHHMMSSZ`.

Beispiel:

```bash
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="reports/evidence/gui-auth-smoke/${STAMP}"
mkdir -p "${EVIDENCE_DIR}"
```

---

## 3) Preflight

### 3.1 Voraussetzungen

- Laufende GUI/API-Umgebung mit aktivem BFF-Flow (`/auth/login`, `/auth/callback`, `/auth/logout` erreichbar)
- Testnutzer im OIDC-Provider vorhanden
- Browser mit DevTools (Cookie-/Network-Inspection)
- Schreibrechte für `reports/evidence/`

Optional hilfreiche Variablen:

```bash
export APP_BASE_URL="https://www.dev.georanking.ch"
export API_BASE_URL="https://api.dev.georanking.ch"
```

### 3.2 Health + Redirect-Baseline

```bash
curl -fsS "${APP_BASE_URL}/healthz" | tee "${EVIDENCE_DIR}/preflight.md"
curl -fsS "${API_BASE_URL}/health" | tee -a "${EVIDENCE_DIR}/preflight.md"

# Ungeloggt muss /gui auf Login redirecten
curl -sSI "${APP_BASE_URL}/gui" | tee -a "${EVIDENCE_DIR}/preflight.md"
```

Preflight-PASS, wenn:

- Health-Endpoints 200 liefern
- `GET /gui` unauthenticated auf `/auth/login?next=...` umleitet
- Redirect-URL optional den Diagnoseparameter `reason` enthält (z. B. `session_expired`)

---

## 4) Positive-Flow (Login → Analyze/History nutzbar)

1. Browser im Inkognito-/frischen Profil öffnen.
2. `GET ${APP_BASE_URL}/gui` aufrufen.
3. Erwartung: Redirect auf Login (OIDC-Flow).
4. Mit Testnutzer einloggen.
5. Nach Rückkehr in die GUI eine Analyse auslösen.
6. Danach `/history` öffnen und prüfen, dass der neue Eintrag sichtbar ist.
7. In DevTools prüfen:
   - Session-Cookie ist `HttpOnly`
   - `Secure` aktiv (bei HTTPS)
   - `SameSite` gesetzt
   - Kein langlebiger Access Token im Browser-Storage

Positive-PASS, wenn:

- GUI nach Login ohne manuelles Bearer-Copy/Paste nutzbar ist
- Analyze + History direkt funktionieren
- Cookie-/Storage-Guardrails eingehalten sind

Dokumentiere Beobachtungen + Screenshots/Headers in `positive-flow.md`.

---

## 5) Negative-Flow (Session-Expiry / invalid Session)

Prüfe mindestens zwei Fehlerszenarien:

### 5.1 Invalid Session (Cookie löschen)

1. Nach erfolgreichem Login Session-Cookie in DevTools löschen.
2. `/history` oder `/gui` neu laden.
3. Erwartung: Redirect auf Login oder konsistente Session-Fehlermeldung (kein stiller Hard-Fail).
4. Redirect-Ziel prüfen: `/auth/login?next=...&reason=<...>` (typisch `session_expired` oder `session_missing`).

### 5.2 Logout-Validity

1. Eingeloggt `GET/POST /auth/logout` über UI auslösen.
2. Redirect-Ziel prüfen:
   - mit IdP-Logout-Konfiguration: Provider-Logout-URL (`.../logout?client_id=...&logout_uri=...`), wobei `logout_uri` aus `BFF_OIDC_POST_LOGOUT_REDIRECT_URI` oder aus dem abgeleiteten `.../auth/login` stammt.
   - ohne IdP-Logout-Konfiguration: lokaler Logout/Cookie-Clear ohne externen Redirect
3. Direkt danach geschützte Seite (`/gui`, `/history`) öffnen.
4. Erwartung: Kein Zugriff ohne erneuten Login.

Negative-PASS, wenn:

- Keine inkonsistenten Zwischenzustände auftreten
- Session-Verlust sauber behandelt wird (Redirect/Re-Login statt kaputter UI)

Ergebnisse in `negative-flow.md` festhalten.

---

## 6) Rollback-Hinweise (bei Regression)

Wenn der Smoke fehlschlägt:

1. **Symptom dokumentieren** (welcher Schritt, erwartetes vs. beobachtetes Verhalten).
2. **Sofortmaßnahme:** letzten stabilen Stand/Artefakt der GUI/Auth-Änderung wiederherstellen (service-lokal, kein Blind-Rollback anderer Services).
3. **Verifikation nach Rollback:**
   - Health (`/health`, `/healthz`)
   - Unauth-Redirect auf Login
   - Basis-Flow aus Abschnitt 4
4. **Nachweis** in `rollback-check.md` ergänzen (inkl. Zeitpunkt + Commit/Task-Revision).

Für Deployment-spezifische Details siehe:

- `../BL31_DEPLOY_ROLLBACK_RUNBOOK.md`
- `../OPERATIONS.md`

---

## 7) Abnahme-Template (Kurzfassung)

```markdown
# GUI Auth Smoke Evidence

- Datum (UTC): <...>
- Umgebung: <dev/local>
- Build/Commit: <...>

## Preflight
- [ ] APP /healthz 200
- [ ] API /health 200
- [ ] /gui unauth -> /auth/login redirect

## Positive Flow
- [ ] Login erfolgreich
- [ ] /analyze via GUI erfolgreich
- [ ] /history zeigt neue Daten
- [ ] Cookie-Flags/Storage geprüft

## Negative Flow
- [ ] Cookie gelöscht -> Re-Login/Fehlerbild korrekt
- [ ] Re-Login-Redirect enthält `reason` (session_expired / refresh_failed / consent_denied)
- [ ] Logout invalidiert Session zuverlässig
- [ ] Logout-Redirect (IdP vs lokal) entspricht der Env-Konfiguration

## Ergebnis
- [ ] PASS
- [ ] FAIL (Grund + Rollback)
```

---

## 8) Verwandte Doku

- BFF Session-Flow: [`docs/gui/GUI_AUTH_BFF_SESSION_FLOW.md`](../gui/GUI_AUTH_BFF_SESSION_FLOW.md)
- AC-Matrix zu #978: [`docs/gui/GUI_AUTH_MVP_AC_MATRIX_978.md`](../gui/GUI_AUTH_MVP_AC_MATRIX_978.md)

