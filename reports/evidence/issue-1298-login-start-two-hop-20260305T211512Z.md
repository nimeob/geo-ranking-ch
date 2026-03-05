# Issue #1298 — Dev deploy login-start smoke false positive (two-hop redirect)

## Context
- Failed scheduled deploy run: https://github.com/nimeob/geo-ranking-ch/actions/runs/22736000848
- Failing step: `Smoke-Test UI login start redirects to IdP authorize`
- Observed redirect from `/login?...&start=1`:
  - `302 -> https://www.dev.georanking.ch:443/auth/login?next=%2Fgui&reason=manual_login&start=1`

## Root Cause
The smoke checker `scripts/smoke/check_ui_login_start.py` only accepted a **direct** `authorize` redirect in the first hop. 
After UI-owned login flow hardening, `/login?...&start=1` can validly do an intermediate hop to `/auth/login` before redirecting to IdP `/oauth2/authorize`.

Result: healthy flow was flagged as failed (`location_is_not_authorize_redirect`).

## Fix
- Accept two valid contracts:
  1. direct first-hop authorize redirect, or
  2. first-hop `/auth/login` followed by second-hop authorize redirect.
- Keep fail-closed checks for:
  - non-302 status,
  - missing `Location`,
  - `reason=login_unavailable`,
  - non-authorize final hop.

## Regression Coverage
- Updated: `tests/test_check_ui_login_start.py`
- Added/covered cases:
  - direct authorize pass
  - `/auth/login` intermediate hop pass
  - fallback `reason=login_unavailable` fail
  - non-redirect status fail
  - `/auth/login` hop that does not reach authorize fail

## Verification
```bash
./.venv/bin/python -m pytest -q tests/test_check_ui_login_start.py
# 5 passed

./scripts/smoke/check_ui_login_start.py --base-url https://www.dev.georanking.ch --next /gui --reason manual_login
# {"ok": true, "reason": "ok", ... "location": "https://auth.dev.georanking.ch/oauth2/authorize?..."}
```
