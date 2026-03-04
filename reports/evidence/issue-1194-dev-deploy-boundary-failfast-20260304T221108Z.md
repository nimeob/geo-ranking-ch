# Issue #1194 — Dev-Deploy Failure RCA + Guardrail Evidence

- Issue: https://github.com/nimeob/geo-ranking-ch/issues/1194
- Timestamp (UTC): 2026-03-04T22:11:08Z

## 1) Root Cause (job/step/failure class)

- Failed run: https://github.com/nimeob/geo-ranking-ch/actions/runs/22686285180
- Job: `Build & Test`
- Step: `Run unit tests`
- Fehlerklasse: `service-boundary policy violation`
- Konkreter Befund:
  - `API route policy violation in 'api/web_service.py': exact route '/trace' is outside API ownership`
  - Failing test: `tests/test_check_bl31_service_boundaries.py::TestCheckBl31ServiceBoundaries::test_current_repo_src_passes_boundary_guard`

## 2) Minimal Fix für diese Fehlerklasse

Die konkrete Boundary-Korrektur wurde bereits auf `main` über den Legacy-Trace-Contract konsolidiert:

- PR: https://github.com/nimeob/geo-ranking-ch/pull/1235
- Ergebnis: `GET /trace` ist als Deprecation-Only-Alias sauber im Boundary-Contract verankert; nachfolgende Deploy-Runs auf `main` wurden wieder grün.

## 3) Neuer Guardrail (fail-fast vor langem Testlauf)

Zusätzlich wurde im Deploy-Workflow ein früher Boundary-Preflight ergänzt:

- Workflow-Änderung: `.github/workflows/deploy.yml`
- Neuer Schritt vor `Run unit tests`:
  - `Preflight boundary guard (fail-fast)`
  - `python3 scripts/check_bl31_service_boundaries.py --src-dir src`

Ziel: gleiche Fehlerklasse sofort und klar sichtbar machen, bevor der komplette Testlauf (~95s+) durchläuft.

## 4) Verifikation

### Workflow-/Docs-Guard

```bash
/data/.openclaw/workspace/geo-ranking-ch/.venv/bin/python -m pytest -q \
  tests/test_deploy_version_trace_docs.py \
  tests/test_markdown_links.py \
  tests/test_user_docs.py
```

### Kontext-Referenz: nachgelagerte grüne Deploy-Runs auf main

- https://github.com/nimeob/geo-ranking-ch/actions/runs/22690695697
- https://github.com/nimeob/geo-ranking-ch/actions/runs/22690690695

## Kurzfazit

- Ursache eindeutig eingegrenzt (`Build & Test` / `Run unit tests` / Boundary-Verstoß `/trace`).
- Fehlerklasse inhaltlich auf `main` behoben (PR #1235).
- Zusätzlicher fail-fast-Guardrail im Deploy-Workflow ergänzt, damit dieselbe Klasse früher blockt.
