# GUI Auth BFF Session Flow (BL-948.wp1)

Diese Doku beschreibt den kanonischen Auth-Flow für die GUI, wenn die Session über den BFF geführt wird (kein manuelles Bearer-Token im Browser-UI-Flow).

## Ziel und Scope

- **In Scope:** Login-Entry, Callback, Session-Lebenszyklus, Logout, typische Fehlerbilder.
- **Out of Scope:** Cognito/Terraform-Provisioning-Details (siehe OIDC-Runbooks), Mobile-spezifische Flows.

## End-to-End Flow

1. **User öffnet geschützte GUI-Route** (`/`, `/gui`, `/history`, `/results/<id>`)
2. **Keine gültige Session vorhanden** -> Redirect auf `GET /login?next=<zielpfad>` (UI-owned Entry auf derselben Domain)
3. **OIDC-Login beim Provider** (Hosted UI)
4. **Callback trifft auf `GET /auth/callback`**
   - Code/State werden serverseitig validiert
   - Session wird im BFF erzeugt/aktualisiert
   - Browser erhält Session-Cookie
5. **Redirect zurück auf `next`**
6. **Folgerequests laufen session-basiert über den BFF-Proxy**
   - GUI sendet für Standard-Flow **keinen** manuellen `Authorization: Bearer ...` Header
   - `/analyze` und `/analyze/history` nutzen Login-/Session-Cookie statt Token-Paste im UI

## Dev-Einstiegspfad (verbindlich)

- Empfohlener Login-Entrypoint in Dev ist **ausschließlich** der UI/BFF-Flow über `GET /login` (direkt oder via Redirect von `/gui`, `/history`, `/results/<id>`).
- `GET /login` bleibt UI-owned und leitet intern auf den BFF-Auth-Start weiter, ohne den API-Host in der Browser-Adresszeile zu zeigen.
- Legacy-Direktpfade bleiben zwar erreichbar, sind aber **deprecated** und liefern bewusst `403` mit Deprecation-Hinweis auf den UI-Pfad.
- Betroffene Direktpfade (Blocker-Fokus, max. 3):
  - `GET /login`
  - `GET /signin`
  - `POST /auth/signin`

## Session-Lebenszyklus

- **created:** Session nach erfolgreichem Callback erzeugt.
- **active:** Session gültig, Requests werden delegiert.
- **refreshing:** BFF versucht Token-Refresh (transparent für GUI).
- **expired:** Session nicht mehr gültig (Re-Login erforderlich).
- **terminated:** Explizites Logout oder serverseitige Invalidierung.

## Logout-Flow

1. GUI triggert `GET /auth/logout`.
2. BFF invalidiert Session serverseitig.
3. Session-Cookie wird im Browser gelöscht (`Max-Age=0`).
4. Redirect-Verhalten:
   - **mit IdP-Logout-Konfiguration** (`BFF_OIDC_ISSUER` + `BFF_OIDC_CLIENT_ID`): 302 auf den Provider-Logout-Endpunkt (`.../logout?client_id=...&logout_uri=...`).
   - `logout_uri` kommt bevorzugt aus `BFF_OIDC_POST_LOGOUT_REDIRECT_URI`; wenn nicht gesetzt, wird aus `BFF_OIDC_REDIRECT_URI=.../auth/callback` deterministisch `.../login` abgeleitet.
   - **ohne IdP-Logout-Konfiguration:** lokaler Clear-Cookie-Logout ohne externen Provider-Redirect.

## UX-/Redirect-Konvention (Issue #998)

Für Session-Recovery nutzen `/gui` und `/history` dieselben UX-Messages und denselben Redirect-Contract:

- Session fehlt/abgelaufen (`401`, `no_session_cookie`, `session_not_found`, `token_error`):
  - Meldung: **„Session ungültig oder abgelaufen — bitte erneut einloggen.“**
  - Redirect: `/login?next=<current-path>&reason=session_expired`
- Refresh fehlgeschlagen (`refresh_*`, `no_refresh_token`):
  - Meldung: **„Session konnte nicht erneuert werden — bitte erneut einloggen.“**
  - Redirect: `/login?next=<current-path>&reason=refresh_failed`
- Consent/Auth verweigert (`access_denied`, `consent_denied`):
  - Meldung: **„Anmeldung abgebrochen oder verweigert — bitte erneut einloggen.“**
  - Redirect: `/login?next=<current-path>&reason=consent_denied`
- Berechtigungsfehler (`403`):
  - Meldung: **„Session ungültig oder abgelaufen — bitte erneut einloggen.“**
    (Fallback-Text im UI bleibt für explizite Forbidden-Cases: „Zugriff verweigert — bitte Berechtigungen/Session prüfen.“)
  - Redirect: `/login?next=<current-path>&reason=session_expired`
- **Vorwarnung vor Session-Ablauf (GUI):**
  - `/auth/me` liefert `session_expires_at` + `session_expires_in_seconds`
  - GUI zeigt **einmalig** vor Ablauf einen Warnhinweis mit CTA „Jetzt neu anmelden"
  - Warnung wird pro Session-Expiry-Epoch nur einmal gezeigt (kein Toast-Spam)
- **Kein stiller Datenverlust bei Session-Recovery:**
  - GUI speichert Eingaben vor Auto-Redirect lokal (`sessionStorage`, Key `geo-ranking-ui-analyze-draft-v1`)
  - Nach Rückkehr via `next` werden Draft-Eingaben automatisch wiederhergestellt

Hinweis: Der zusätzliche Query-Parameter `reason` ist für reproduzierbare Diagnose gedacht (Runbook/Evidence) und ersetzt nicht die Server-seitige Prüfung von `next`.

## Failure-Modes (Kurzmatrix)

| Fehlerbild | Typisches Symptom | Wahrscheinliche Ursache | Sofortmaßnahme |
|---|---|---|---|
| Callback fehlgeschlagen | Genau eine verständliche Fehlerseite mit Re-Login-CTA (kein Auto-Redirect) | Ungültiger/abgelaufener Auth-Code oder State-Mismatch | CTA „Erneut einloggen" nutzen; Request-ID + Callback-Diagnostics prüfen |
| Consent/Auth verweigert | Login kehrt mit Fehler zurück, GUI fordert Re-Login | Nutzer hat Consent/Anmeldung abgebrochen (`access_denied`/`consent_denied`) | Erneut einloggen; bei wiederholtem Fehler Provider-/Client-Konfiguration prüfen |
| Session abgelaufen | GUI-Action zeigt Session-Hinweis und leitet auf Login weiter | Session-TTL erreicht, Cookie fehlt/ungültig | Neu einloggen, Session-/Cookie-Parameter prüfen |
| Token-Refresh fehlgeschlagen | Hinweis „Session konnte nicht erneuert werden" + Re-Login-Redirect | Refresh-Grant fehlerhaft (`refresh_*`, `no_refresh_token`) | Refresh-Token-Path + IdP-Config prüfen, danach Re-Login |
| Logout ohne Wirkung | Nach Logout weiter „eingeloggt" | Cookie nicht gelöscht oder alte Session noch aktiv | Cookie-Flags + Server-Invalidierung prüfen |
| 401 im BFF-Proxy | GUI zeigt Auth-Fehler trotz Login | Upstream-Token ungültig / Delegation fehlgeschlagen | BFF-Token-Refresh-/Delegationspfad prüfen |

## Security-Guardrails (verbindlich)

- Session-Cookie als **httpOnly** setzen (kein JS-Zugriff).
- **SameSite** bewusst setzen (mind. `Lax`, abhängig vom Redirect-Pattern).
- In produktionsnahen Umgebungen **Secure** aktivieren (nur HTTPS).
- CSRF-Schutz für zustandsändernde BFF-Endpunkte sicherstellen.
- `next`/Redirect-Ziele auf erlaubte Pfade/Hosts begrenzen (Open-Redirect vermeiden).
- Keine Access-/Refresh-Tokens in Browser-Logs oder URL-Fragmente schreiben.

## Nachweis-/Abnahme-Checkliste

- Login von geschützter Route -> Callback -> Rückkehr auf Zielroute funktioniert.
- Logout invalidiert Session sichtbar (erneuter Zugriff erfordert Login).
- Session-Expiry wird deterministisch behandelt (kein endloses Loading/Looping).
- Refresh-Fehlercodes (`refresh_*`, `no_refresh_token`) triggern denselben Re-Login-Recovery-Flow wie Session-Expiry.
- Keine sensitiven Tokenwerte in UI-Logs/Devtools-Network-Payloads.

## Reproduzierbarer Dev-E2E-Nachweis (Issue #947)

Die folgenden Checks liefern einen wiederholbaren Nachweis für den GUI-Auth-Flow (Login-Redirect -> geschützter Zugriff -> Logout inklusive Cookie-Clear):

```bash
python3 -m unittest tests.test_web_service_bff_gui_guard
```

Erwartung:
- `GET /gui` ohne Session -> `302` nach `/login?next=%2Fgui`
- `GET /history?limit=5` ohne Session -> `302` nach `/login?next=%2Fhistory%3Flimit%3D5`
- `GET /auth/callback` mit ungültigem/abgelaufenem `state` -> `400` HTML-Fehlerseite mit genau einem Re-Login-CTA (`/login?next=...&reason=session_expired`), ohne Redirect-Loop
- `GET /auth/logout` löscht Session-Cookie (`Max-Age=0`) und liefert IdP-Logout-Redirect

## Automatisierter Guard- und Session-Proxy-Nachweis (Issue #997)

Für das Work-Package „Protected Routes + session-basierter `/analyze`/`/analyze/history`-Flow" wird zusätzlich folgende Regression-Suite ausgeführt:

```bash
python3 -m pytest -q tests/test_web_service_bff_gui_guard.py tests/test_bff_integration.py
```

Abgedeckte Kernpunkte:
- Ungültige Session-Cookies auf `/gui` und `/history` führen deterministisch auf `/login?next=...` zurück.
- Eingeloggte Session kann `GET /portal/api/analyze/history` und `POST /portal/api/analyze` über den BFF-Proxy ausführen.
- Downstream-Delegation enthält `Authorization: Bearer <token>` (kein Browser-Token-Handling notwendig).

## Cookie-Security-Evidenz (Issue #947)

| Attribut | Nachweis | Quelle |
|---|---|---|
| `HttpOnly` | Logout-Cookie enthält `HttpOnly`; Session-Set/Clear-Helper sind regressionsgetestet | `tests/test_web_service_bff_gui_guard.py`, `tests/test_bff_session.py` |
| `SameSite` | Logout-Header nutzt `SameSite=Lax`; Session-Cookies prüfen `SameSite=Lax` | `tests/test_web_service_bff_gui_guard.py`, `tests/test_bff_session.py` |
| `Secure` | `Secure` wird bei aktiviertem `BFF_SESSION_SECURE_COOKIE=1` gesetzt und bei `0` nicht gesetzt; `__Host-*`-Namen werden bei `Secure=0` auf `bff-session` gedowngraded (kein ungültiger Host-Prefix-Cookie) | `tests/test_bff_session.py`, `tests/test_bff_portal_proxy.py` |
| Session-Store Guards | Session-ID/Cookie-Name werden auf zulässiges Token-Format geprüft; invalide Werte werden verworfen bzw. als `ValueError` geblockt | `src/api/bff_session.py`, `src/api/bff_portal_proxy.py`, `tests/test_bff_session.py`, `tests/test_bff_portal_proxy.py` |

Konkreter Test-/Output-Nachweis: [`reports/evidence/issue-947-gui-auth-e2e-cookie-evidence-20260303T171208Z.md`](../../reports/evidence/issue-947-gui-auth-e2e-cookie-evidence-20260303T171208Z.md)

## Parent-Acceptance-Referenz (#939 / #978)

Dieses Work-Package deckt den E2E-/Security-Dokumentationsanteil von #939 ab; die aktualisierte AC-Reconciliation für #978 ist separat dokumentiert.

- Parent-AC "Kurzer E2E-Nachweis in dev dokumentiert" -> erfüllt über obigen Dev-E2E-Nachweis + Evidence-Artefakt.
- Parent-AC "Session-Cookie ist `HttpOnly`, `Secure`, `SameSite` konfiguriert" -> erfüllt über Cookie-Attribut-Matrix + Regressionstests.
- AC-Matrix #978 (vollständiger Snapshot inkl. Verify-Run): [`docs/gui/GUI_AUTH_MVP_AC_MATRIX_978.md`](./GUI_AUTH_MVP_AC_MATRIX_978.md)

## Verweise

- GUI State Flow: [`docs/gui/GUI_MVP_STATE_FLOW.md`](./GUI_MVP_STATE_FLOW.md)
- User API Usage (Auth-Abschnitt): [`docs/user/api-usage.md`](../user/api-usage.md)
- OIDC Staging Runbook: [`docs/OIDC_COGNITO_STAGING_RUNBOOK.md`](../OIDC_COGNITO_STAGING_RUNBOOK.md)
