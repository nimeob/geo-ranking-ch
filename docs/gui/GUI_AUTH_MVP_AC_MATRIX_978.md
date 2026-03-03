# GUI Auth MVP — Acceptance-Matrix für Issue #978

Diese Matrix prüft die ACs aus [#978](https://github.com/nimeob/geo-ranking-ch/issues/978) gegen den aktuellen Repo-Stand.

Stand: 2026-03-03 (Issue #995 + #998)

## Quellen

- Flow-/Security-Referenz: [`docs/gui/GUI_AUTH_BFF_SESSION_FLOW.md`](./GUI_AUTH_BFF_SESSION_FLOW.md)
- E2E-Smoke-Runbook: [`docs/testing/GUI_AUTH_SMOKE_RUNBOOK.md`](../testing/GUI_AUTH_SMOKE_RUNBOOK.md)
- BFF-Implementierung: `src/api/bff_oidc.py`, `src/api/bff_session.py`, `src/api/bff_portal_proxy.py`, `src/api/web_service.py`
- Reproduzierbarer Verifikationslauf: [`reports/evidence/issue-995-auth-ac-matrix-20260303T185411Z.md`](../../reports/evidence/issue-995-auth-ac-matrix-20260303T185411Z.md)
- UX-/Runbook-Sync-Nachweis (Issue #998): [`reports/evidence/issue-998-auth-ux-runbook-sync-20260303T1949Z.md`](../../reports/evidence/issue-998-auth-ux-runbook-sync-20260303T1949Z.md)

## AC-Matrix

1. **GUI ohne manuelles Bearer-Token nutzbar**  
   **Status:** erfüllt  
   **Nachweis:** GUI-Flow beschreibt explizit Session-Cookie statt Token-Paste (`GUI_AUTH_BFF_SESSION_FLOW.md`, Abschnitt End-to-End Flow); GUI-State- und History-Seiten nutzen Session-Flow (`src/shared/gui_mvp.py`, `src/shared/ui_pages.py`).

2. **Login/Callback/Logout End-to-End in dev verifiziert**  
   **Status:** erfüllt  
   **Nachweis:** Runbook mit reproduzierbarem Login/Callback/Logout-Szenario (`GUI_AUTH_SMOKE_RUNBOOK.md`), plus grüne Testabdeckung in `tests/test_bff_oidc.py`, `tests/test_bff_integration.py`, `tests/test_web_service_bff_gui_guard.py` und Nachweislauf `issue-995-auth-ac-matrix-20260303T185411Z.md`.

3. **Session-Cookie korrekt gesetzt (`HttpOnly`, `Secure`, `SameSite`)**  
   **Status:** erfüllt  
   **Nachweis:** Security-Guardrails + Cookie-Evidenz in `GUI_AUTH_BFF_SESSION_FLOW.md` (Cookie-Security-Evidenz), technische Umsetzung in `src/api/bff_session.py`, Regressionen in `tests/test_bff_session.py` und `tests/test_web_service_bff_gui_guard.py`.

4. **`/analyze` und `/analyze/history` funktionieren nach Login**  
   **Status:** erfüllt  
   **Nachweis:** Session-basierter GUI-Flow und History-Pfade dokumentiert (`GUI_AUTH_BFF_SESSION_FLOW.md`, `GUI_AUTH_SMOKE_RUNBOOK.md`), Tests in `tests/test_history_navigation_integration.py`, `tests/test_history_pagination_and_guards.py`, `tests/test_bff_portal_proxy.py`.

5. **Expired/invalid Session führt sauber zurück auf Login**  
   **Status:** erfüllt  
   **Nachweis:** Recovery-/Failure-Flow dokumentiert (`GUI_AUTH_BFF_SESSION_FLOW.md`, Abschnitt „UX-/Redirect-Konvention"), inklusive konsolidiertem Redirect-Contract `/auth/login?next=...&reason=...`; Guard/Redirect-Tests in `tests/test_web_service_bff_gui_guard.py` und `tests/test_bff_portal_proxy.py`.

6. **Kurze Doku im README/Runbook ergänzt (lokal + dev)**  
   **Status:** erfüllt  
   **Nachweis:** README enthält aktualisierten BFF-Auth-Abschnitt (Auth-Recovery + Logout-Varianten); Runbook unter `docs/testing/GUI_AUTH_SMOKE_RUNBOOK.md` deckt `reason`-Redirects sowie IdP-vs-lokalen Logout ab; diese AC-Matrix ergänzt die Parent-Nachweisspur.

## Gap-Bewertung

Aktuell **keine neuen funktionalen Gaps** gegenüber den ACs aus #978 identifiziert.

- Folgeissues aus dieser AC-Analyse: **keine notwendig**.
- Wenn künftig Drift auftritt, werden neue Follow-up-Issues direkt aus #978 heraus erstellt/verlinkt.

## Reproduzierbarer Check (Snapshot)

Siehe Evidence-Datei: [`reports/evidence/issue-995-auth-ac-matrix-20260303T185411Z.md`](../../reports/evidence/issue-995-auth-ac-matrix-20260303T185411Z.md)

Kurzfazit aus dem Lauf:

- Command: `./.venv/bin/python -m pytest -q <auth/history/docs-scope>`
- Ergebnis: **209 passed**, Exit **0**
