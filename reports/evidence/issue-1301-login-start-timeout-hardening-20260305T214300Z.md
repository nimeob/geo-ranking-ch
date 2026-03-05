# Issue #1301 — Dev deploy login-start smoke timeout hardening

## Trigger
- Failed run: https://github.com/nimeob/geo-ranking-ch/actions/runs/22737145775
- Failed step: `Smoke-Test UI login start redirects to IdP authorize`
- Error payload: `{"ok": false, "reason": "request_failed", "error": "The read operation timed out", ...}`

## Root Cause
`check_ui_login_start.py` performed single-shot network checks per hop. After ECS UI deploy, transient network conditions (timeouts / temporary 502/503 from edge/upstream) can occur briefly even when the flow recovers moments later.

## Fix
- Add retry/backoff support to login-start smoke checks (`--max-attempts`, `--retry-delay`).
- Retry transient request exceptions and transient HTTP upstream errors (`502/503/504`) before failing hard.
- Keep fail-closed behavior for contract violations (non-302 final contract, missing Location, login_unavailable fallback, non-authorize target).
- Wire deploy workflow step with explicit robust settings:
  - `--timeout 20`
  - `--max-attempts 3`
  - `--retry-delay 2`

## Tests
```bash
./.venv/bin/python -m pytest -q tests/test_check_ui_login_start.py
# 8 passed
```

## Added regression coverage
- retry on transient timeout exception
- retry on transient HTTP 502 before succeeding
- retries exhausted => deterministic RuntimeError (`request_failed_after_retries`)
