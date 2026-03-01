# Minimum-Compliance-Set — Externer Direktzugriff / Login-Sperre v1

Stand: 2026-03-01  
Geltung: API-Runtime `src/api/web_service.py` (BL-342 / Issue #524)

## Ziel

Externe Parteien dürfen **keinen Direktlogin** gegen den Service durchführen. Zugriff erfolgt ausschließlich über interne Bereitstellung bzw. definierte Export-Workflows.

## Verbindliche Runtime-Regel

Der Service blockiert bekannte Direktlogin-Routen explizit mit `403` und Fehlercode `external_direct_login_disabled`.

Blockierte Pfade (normalisiert, inkl. Trailing-Slash-Toleranz):

- `/login`
- `/signin`
- `/sign-in`
- `/auth/login`
- `/auth/signin`
- `/auth/sign-in`
- `/oauth/login`
- `/oauth2/login`

Antwortformat:

- HTTP: `403 Forbidden`
- JSON: `{"ok": false, "error": "external_direct_login_disabled", "message": "...", "request_id": "..."}`

Zusätzlich wird ein strukturierter Audit-Logeintrag erzeugt:

- Event: `api.auth.direct_login.blocked`
- Status: `blocked`
- Pflichtfelder: `route`, `method`, `request_id`, `reason`

## Konfigurationstest (Akzeptanzkriterium)

Der Konfigurationstest gilt als bestanden, wenn Login-Routen reproduzierbar mit `403` blockiert werden:

```bash
curl -sS -i http://127.0.0.1:8080/login
curl -sS -i -X POST http://127.0.0.1:8080/auth/login -H 'Content-Type: application/json' -d '{"username":"x","password":"y"}'
curl -sS -i -X OPTIONS http://127.0.0.1:8080/signin
```

Erwartung in allen Fällen:

- Statuszeile enthält `403`
- Body enthält `error=external_direct_login_disabled`

## Nachweis im Repo

- Runtime-Guard: `src/api/web_service.py`
- E2E-Test: `tests/test_web_e2e.py::test_external_direct_login_routes_blocked_for_get_and_post`
- Compliance-Doku-Guard: `tests/test_compliance_external_direct_access_control_docs.py`
