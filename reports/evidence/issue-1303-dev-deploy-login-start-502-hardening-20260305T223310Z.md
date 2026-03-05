# Issue #1303 — Dev Deploy login-start smoke flake (502 on auth hop)

## Trigger
- Failed run: https://github.com/nimeob/geo-ranking-ch/actions/runs/22738183884
- Failed step: `Smoke-Test UI login start redirects to IdP authorize`
- Error payload: `{"ok": false, "reason": "auth_login_hop_unexpected_status_502", ...}`

## Root Cause
Der Login-Start-Smoke lief direkt nach dem UI-Rollout. In diesem kurzen Warm-up-Fenster lieferte der `/auth/login`-Zwischenschritt wiederholt HTTP 502, obwohl der Service kurz danach stabil wurde.

Mit den bisherigen Parametern (`--max-attempts 3`, `--retry-delay 2`) war das Retry-Budget für diese transienten 5xx-Spitzen zu klein.

## Fix
Deploy-Workflow für den Login-Start-Smoke gehärtet:

- `--max-attempts`: `3 -> 8`
- `--retry-delay`: `2 -> 5`
- bestehendes fail-closed Verhalten bleibt unverändert (bei echten Vertragsverletzungen weiterhin sofortiger Fail)

Datei:
- `.github/workflows/deploy.yml`

## Verifikation (lokal)
```bash
pytest -q tests/test_check_ui_login_start.py
# 8 passed
```

## Erwarteter Effekt
Der stündliche Dev-Deploy toleriert kurze 502-Warm-up-Phasen im Login-Start-Hop robuster und bricht nur noch bei persistenten Fehlern ab.
