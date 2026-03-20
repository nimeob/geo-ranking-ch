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
