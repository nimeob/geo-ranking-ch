# Night Worker Log — 2026-03-25

## 02:15–02:25 CET
- Validated current in-flight auth/UI hardening patchset with focused pytest run:
  - `tests/test_web_service_coordinate_input.py`
  - `tests/test_ui_service.py`
  - `tests/test_web_service_bff_gui_guard.py`
  - `tests/test_async_worker_runtime_compat.py`
  - `tests/test_web_service_phase1_auth.py`
  - plus `tests/test_check_ui_login_start.py`
- Result: pass (`64 passed, 16 subtests passed`).

## UI live check
- Browser tool was unavailable (`gateway timeout`); attempted gateway diagnosis via `openclaw gateway status`.
- Fallback to HTTP smoke checks against live dev UI:
  - `https://www.dev.georanking.ch`
  - `https://www.dev.geo-ranking.ch`
- Found alias host returns canonical **307** redirect first (expected infra behavior), which caused `check_ui_login_start.py` to fail on alias with `unexpected_entry_status_307` (false negative).

## Fix implemented
- Updated `scripts/smoke/check_ui_login_start.py` to tolerate **one canonical host redirect (307/308)** when path/query stay identical, then continue contract validation.
- Added tests in `tests/test_check_ui_login_start.py` for entry/start canonical redirect handling.
- Re-ran smoke checks against both domains; both now pass.

## Notes
- Did not touch forbidden WIP files:
  - `reports/consistency_report.json`
  - `reports/consistency_report.md`
  - `triage_add_labels.sh`
