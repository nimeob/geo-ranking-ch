# Night Worker Evidence — UI Login Entry Contract Guard

- **Timestamp (UTC):** 2026-03-20T01:36:00Z
- **Branch:** `fix/login-entry-contract-smoke-guard`
- **Scope:** Harden deploy/runtime smoke for UI-owned login entry (`/login`) + login start (`/login?start=1`).

## Motivation / Decision

During runtime probe of `https://www.dev.georanking.ch`, `/login?next=%2Fgui` returned a **302 redirect from ALB** (`server: awselb/2.0`) to `/auth/login`, instead of serving the UI-owned login entry HTML.

This breaks the intended contract from earlier auth-boundary work (UI-owned entry page), and existing smoke only validated the `start=1` hop — so the regression could pass unnoticed.

## Change Implemented

1. Extended `scripts/smoke/check_ui_login_start.py` to validate **both** phases:
   - **Entry phase:** `/login?next=...&reason=...` must be `200`, `text/html`, and include a `start=1` login-start link.
   - **Start phase:** existing `/login?...&start=1` authorize redirect flow retained (direct or via `/auth/login`).
2. Extended `tests/test_check_ui_login_start.py` with entry-contract coverage and `main()` failure phase assertion.

## Validation

### Unit tests

```bash
./.venv/bin/python -m pytest -q tests/test_check_ui_login_start.py
```

Result: **11 passed**.

### Live runtime check (dev UI)

```bash
./.venv/bin/python scripts/smoke/check_ui_login_start.py \
  --base-url https://www.dev.georanking.ch \
  --next /gui \
  --reason manual_login \
  --timeout 20 \
  --max-attempts 3 \
  --retry-delay 2
```

Result:

```json
{"ok": false, "phase": "entry", "reason": "unexpected_entry_status_302", "status_code": 302, "request_url": "https://www.dev.georanking.ch/login?next=%2Fgui&reason=manual_login", "location": "https://www.dev.georanking.ch:443/auth/login?next=%2Fgui&reason=manual_login", "content_type": "text/html", "request": {"base_url": "https://www.dev.georanking.ch", "next": "/gui", "reason": "manual_login", "timeout": 20.0, "max_attempts": 3, "retry_delay": 2.0}}
```

Interpretation: deploy/runtime guard now reliably catches the current frontdoor/login-entry regression.
