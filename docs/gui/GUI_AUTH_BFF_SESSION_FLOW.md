# GUI Auth BFF Session Flow (BL-948.wp1)

Diese Doku beschreibt den kanonischen Auth-Flow für die GUI, wenn die Session über den BFF geführt wird (kein manuelles Bearer-Token im Browser-UI-Flow).

## Ziel und Scope

- **In Scope:** Login-Entry, Callback, Session-Lebenszyklus, Logout, typische Fehlerbilder.
- **Out of Scope:** Cognito/Terraform-Provisioning-Details (siehe OIDC-Runbooks), Mobile-spezifische Flows.

## End-to-End Flow

1. **User öffnet geschützte GUI-Route** (`/`, `/gui`, `/history`, `/results/<id>`)
2. **Keine gültige Session vorhanden** -> Redirect auf `GET /auth/login?next=<zielpfad>`
3. **OIDC-Login beim Provider** (Hosted UI)
4. **Callback trifft auf `GET /auth/callback`**
   - Code/State werden serverseitig validiert
   - Session wird im BFF erzeugt/aktualisiert
   - Browser erhält Session-Cookie
5. **Redirect zurück auf `next`**
6. **Folgerequests laufen session-basiert über den BFF-Proxy**
   - GUI sendet für Standard-Flow **keinen** manuellen `Authorization: Bearer ...` Header
   - `/analyze` und `/analyze/history` nutzen Login-/Session-Cookie statt Token-Paste im UI

## Session-Lebenszyklus

- **created:** Session nach erfolgreichem Callback erzeugt.
- **active:** Session gültig, Requests werden delegiert.
- **refreshing:** BFF versucht Token-Refresh (transparent für GUI).
- **expired:** Session nicht mehr gültig (Re-Login erforderlich).
- **terminated:** Explizites Logout oder serverseitige Invalidierung.

## Logout-Flow

1. GUI triggert `GET /auth/logout`.
2. BFF invalidiert Session serverseitig.
3. Session-Cookie wird im Browser gelöscht.
4. Redirect auf Login-Seite oder öffentliche Landing-Page.

## Failure-Modes (Kurzmatrix)

| Fehlerbild | Typisches Symptom | Wahrscheinliche Ursache | Sofortmaßnahme |
|---|---|---|---|
| Callback fehlgeschlagen | Redirect-Loop `/auth/login` <-> `/auth/callback` | Ungültiger/abgelaufener Auth-Code oder State-Mismatch | Callback-Logs prüfen, neuen Login starten |
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

## Verweise

- GUI State Flow: [`docs/gui/GUI_MVP_STATE_FLOW.md`](./GUI_MVP_STATE_FLOW.md)
- User API Usage (Auth-Abschnitt): [`docs/user/api-usage.md`](../user/api-usage.md)
- OIDC Staging Runbook: [`docs/OIDC_COGNITO_STAGING_RUNBOOK.md`](../OIDC_COGNITO_STAGING_RUNBOOK.md)
