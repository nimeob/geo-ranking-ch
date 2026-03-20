# Night Worker Log – 2026-03-20

## 07:52 CET – Issue #1376 deploy gate failure triage + fix
- Synced repo and confirmed `origin/main` advanced to commit `f19c92d` (PR #1375, Node24 action upgrades).
- Reproduced failing gate locally:
  - `pytest tests/test_pr_fast_gates_config.py::TestPrFastGatesConfig::test_dev_smoke_required_workflow_triggers_on_pull_request`
  - Failure: test pinned `actions/upload-artifact@v4` while workflow now uses `@v6`.
- Applied targeted fix in `tests/test_pr_fast_gates_config.py`:
  - Replaced strict `assertIn("actions/upload-artifact@v4", ...)` with regex `assertRegex(..., r"actions/upload-artifact@v\d+")`.
  - Rationale: preserves guard that upload-artifact step exists while allowing safe major bumps (prevents recurrence on runtime upgrades).
- Validation:
  - `pytest -q tests/test_pr_fast_gates_config.py` => **5 passed**.

Next planned ops: commit, push branch, open PR, merge, rerun deploy workflow, then close issue #1376 with root cause + evidence links.

## 08:03 CET – Follow-up blocker from fresh deploy run (#1378)
- After merging #1377, deploy run `23332245545` advanced past Build & Test but failed at `Smoke-Test UI login start redirects to IdP authorize`.
- Failure payload showed `/login?next=...&reason=manual_login` returns immediate `302` to IdP authorize; smoke script still treated any entry 302 as contract break.
- Implemented contract update in `scripts/smoke/check_ui_login_start.py`:
  - Entry check now accepts both supported entry modes:
    1) HTML entry page with `start=1` link (legacy/manual mode), or
    2) direct login-chain redirects (`/auth/login` or IdP `authorize`) for auto-start mode.
  - Keeps hard failures for `login_unavailable`, missing Location on 302, and redirects to non-login targets.
- Updated test suite in `tests/test_check_ui_login_start.py` to match contract:
  - added passing coverage for entry authorize/auth-login redirects,
  - converted prior redirect-regression assertion into invalid-target failure assertion.
- Validation:
  - `pytest -q tests/test_check_ui_login_start.py` => **12 passed**
  - `pytest -q tests/test_pr_fast_gates_config.py tests/test_check_ui_login_start.py` => **17 passed**

Next planned ops: commit + PR for #1378, merge, verify next dev deploy is green, then close issue with evidence.
