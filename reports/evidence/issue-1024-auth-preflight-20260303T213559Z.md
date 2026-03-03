# Issue #1024 — Auth-Preflight Runner Evidence

- Timestamp (UTC): 20260303T213559Z
- Scope: `scripts/smoke/auth_preflight.sh` + Tests + Runbook-Verlinkung

## Implementiert
- Neuer Preflight-Runner: `scripts/smoke/auth_preflight.sh`
  - Unterstützt `SMOKE_AUTH_MODE=oidc_client_credentials|none`
  - Fail-fast mit Exit-Code `42` und Marker `auth-preflight-failed`
  - Mintet OIDC Access-Token per Client-Credentials
  - Schreibt Contract-Datei mit `SMOKE_AUTH_MODE` + `SMOKE_BEARER_TOKEN`
- Neue Tests: `tests/test_auth_preflight_script.py`
- Doku-Sync: `docs/testing/REMOTE_API_SMOKE_RUNBOOK.md`

## Verifikation

Ausgeführt:

```bash
/data/.openclaw/workspace/geo-ranking-ch/.venv/bin/python -m pytest -q \
  tests/test_auth_preflight_script.py \
  tests/test_markdown_links.py \
  tests/test_user_docs.py
```

Ergebnis:

```text
.............                                                            [100%]
13 passed in 1.96s
```
