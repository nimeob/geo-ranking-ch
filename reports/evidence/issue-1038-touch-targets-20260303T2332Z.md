# Issue #1038 — Mobile Touch-Targets Evidence (2026-03-03)

## Scope
- Touch-targets für Kern-Controls im GUI-MVP auf Mobile vereinheitlicht (`<=768px`, min. `44x44` CSS px).
- Zentrale CSS-Guardrails in `src/shared/gui_mvp.py`.

## Before/After Screenshots (390x844)
- Before: `reports/evidence/issue-1038-touch-targets-before-20260303T2328Z.png`
- After: `reports/evidence/issue-1038-touch-targets-after-20260303T2331Z.png`

## Testnachweis
- UI/CSS-Contract-Test ergänzt: `tests/test_web_service_gui_mvp.py::test_gui_mobile_touch_target_css_contract_present`
- Verifikation:
  - `./.venv/bin/python -m pytest -q tests/test_web_service_gui_mvp.py tests/test_markdown_links.py`
  - Ergebnis: `6 passed`

## Hinweise
- Desktop-Layout wurde nicht global aufgeweitet; Touch-Target-Mindestgröße greift nur im Mobile-Breakpoint (`@media (max-width: 768px)`).
