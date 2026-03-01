# Async Result-Permalink Tenant-Guard + Snapshot-Projektion v1

Stand: 2026-03-01  
Issue: #599 (Parent #594)

## Ziel

Den Result-Permalink (`GET /analyze/results/{result_id}`) für den produktiven Betrieb
härten, sodass:

1. Resultate tenant-sicher gelesen werden,
2. ein deterministischer Snapshot-Modus für Result-Pages verfügbar ist
   (`final` bevorzugt, sonst letzter `partial`-Snapshot).

## Tenant-Guard

### Header

- Primär: `X-Org-Id`
- Alias: `X-Tenant-Id`
- Ohne Header: Fallback auf `default-org`

### Zugriffspfad

- `GET /analyze/jobs/{job_id}` und `GET /analyze/results/{result_id}` prüfen,
  ob die `org_id` des Jobs zur angefragten Org passt.
- Bei Mismatch wird bewusst `404 not_found` zurückgegeben
  (keine Existenz-Leaks über fremde Tenant-Daten).

### Validierung

- `X-Org-Id` darf nur Zeichen aus `[A-Za-z0-9_.:-]` enthalten.
- Maximallänge: 128 Zeichen.
- Ungültige Header führen zu `400 bad_request`.

## Snapshot-Projektion für `GET /analyze/results/{result_id}`

### Query-Parameter

- `view=latest` (Default):
  - wählt für den Job den finalen Snapshot (`result_kind=final`), falls vorhanden
  - sonst den letzten vorhandenen Snapshot (typisch letzter `partial`)
- `view=requested`:
  - liefert exakt den angefragten Snapshot (`{result_id}`)

### Response (additiv)

Neue additive Felder:

- `requested_result_id`
- `requested_result_kind`
- `projection_mode` (`latest` oder `requested`)

Bestehende Felder bleiben erhalten (`result_id`, `job_id`, `result_kind`, `result`).

## CORS

Die CORS-Allow-Headers wurden um Tenant-Header erweitert:

- `X-Org-Id`
- `X-Tenant-Id`

Damit Browser-Clients den Tenant-Kontext auch bei Cross-Origin-Requests sauber
übergeben können.

## Regressionen

- `tests/test_async_jobs_runtime_skeleton.py`
  - tenant-guard auf Job-/Result-Endpunkten
  - Snapshot-Projektion (`view=latest` vs. `view=requested`)
- `tests/test_async_result_permalink_tenant_guard_docs.py`
  - Pflichtmarker dieser Doku
