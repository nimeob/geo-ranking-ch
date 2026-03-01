# Minimum-Compliance-Set — Export-Logging-Standard v1

_Status: freigegeben (Repo-Baseline)_  
_Gültig ab: 2026-03-01_  
_Bezug: Issue #525_

## Zweck

Dieser Standard definiert den **verbindlichen Mindest-Logeintrag** für Exporte,
damit Exportvorgänge nachvollziehbar, auditierbar und maschinell auswertbar sind.

## Verbindliche Pflichtfelder (wer/wann/kanal)

Jeder Export-Logeintrag muss mindestens folgende Felder enthalten:

| Feld | Pflicht | Beschreibung |
|---|---|---|
| `actor` | ja | Wer hat den Export ausgelöst (User/Worker/Automation) |
| `exported_at_utc` | ja | Wann wurde exportiert (UTC ISO-8601, z. B. `2026-03-01T08:20:00Z`) |
| `channel` | ja | Über welchen Kanal/Transport wurde exportiert (z. B. `file:csv`) |
| `artifact_path` | ja | Zielartefakt bzw. Exportpfad |
| `export_kind` | ja | Fachlicher Exporttyp |
| `row_count` | ja | Anzahl exportierter Datensätze |
| `error_count` | ja | Anzahl fehlerhafter Datensätze |
| `status` | ja | `ok` / `partial` / `error` |

## Referenz-Schema (JSONL v1)

```json
{
  "version": 1,
  "event": "compliance.export.logged",
  "control": "bl342-export-logging-v1",
  "actor": "worker-a",
  "channel": "file:csv",
  "exported_at_utc": "2026-03-01T08:20:00Z",
  "artifact_path": "reports/exports/sample.csv",
  "export_kind": "address-intel-batch-csv",
  "row_count": 128,
  "error_count": 2,
  "status": "partial",
  "details": {
    "scope": "batch-export"
  }
}
```

## Ablage und Auswertung

- Default-Logpfad: `artifacts/compliance/export/export_log_v1.jsonl`
- Override via ENV: `COMPLIANCE_EXPORT_LOG_PATH`
- Actor-Override via ENV: `COMPLIANCE_EXPORT_ACTOR`

Beispielauswertung (wer/wann/kanal):

```bash
jq -r '.actor + "\t" + .exported_at_utc + "\t" + .channel' artifacts/compliance/export/export_log_v1.jsonl
```

## Implementierungsbezug

- Runtime-Helper: `src/compliance/export_logging.py`
- Batch-Export-Integration: `src/api/address_intel.py` (`--out-jsonl`, `--out-csv`, `--out-error-csv`)
- Regressionstests:
  - `tests/test_compliance_export_logging.py`
  - `tests/test_address_intel_export_logging.py`
