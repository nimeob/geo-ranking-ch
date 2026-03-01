# Compliance Ops Monitoring — Runbook V1

**Issue:** #531 — Monitoring aktivieren (Löschjobs/Hold-Bestand/Fehlerquote)  
**Erstellt:** 2026-03-01  
**Owner:** IT Operations  
**Status:** Aktiv

---

## Überblick

Dieses Runbook beschreibt die Monitoring-KPIs und Alerting-Regeln für den
laufenden Compliance-Betrieb. Drei Bereiche werden überwacht:

| Bereich | KPI | Quelle |
|---|---|---|
| Löschjobs | `deletion_overdue_count` | `COMPLIANCE_DELETION_LOG` JSONL |
| Hold-Bestand | `hold_active_count`, `hold_overdue_review_count` | `COMPLIANCE_HOLD_LOG` JSONL |
| Fehlerquote | Export-Fehlerrate (%) | `COMPLIANCE_EXPORT_LOG_PATH` JSONL |

---

## Monitoring-Skript

```bash
# Lokal / CI ausführen
python scripts/check_compliance_ops_monitoring.py
```

Konfiguration via Umgebungsvariablen:

| Variable | Bedeutung | Standard |
|---|---|---|
| `COMPLIANCE_DELETION_LOG` | Pfad zum Löschrekord-JSONL-Snapshot | _(kein — Skip)_ |
| `COMPLIANCE_HOLD_LOG` | Pfad zum Hold-Rekord-JSONL-Snapshot | _(kein — Skip)_ |
| `COMPLIANCE_EXPORT_LOG_PATH` | Pfad zum Export-Log-JSONL | `artifacts/compliance/export/export_log_v1.jsonl` |
| `COMPLIANCE_MONITOR_HOURS` | Zeitfenster für Fehlerquote (Stunden) | `24` |
| `COMPLIANCE_WARN_OVERDUE` | Mindest-Anzahl Overdue-Items für WARN | `1` |
| `COMPLIANCE_FAIL_EXPORT_PCT` | Export-Fehlerrate (%) → FAIL | `25.0` |
| `COMPLIANCE_WARN_EXPORT_PCT` | Export-Fehlerrate (%) → WARN | `10.0` |

### Exit-Codes

| Code | Bedeutung |
|---|---|
| `0` | OK — alle Checks bestanden |
| `10` | WARN — mind. eine Warnung |
| `20` | FAIL — mind. ein kritischer Check |

---

## KPI-Definitionen & Schwellenwerte

### 1. Löschjobs

**Definition:** Anzahl Lösch-Records mit Status `notified` und überschrittenem
`execute_after`-Zeitstempel.

| Schwelle | Aktion |
|---|---|
| `deletion_overdue_count ≥ 1` | **FAIL** — sofort eskalieren, manuellen Löschprozess prüfen |
| `deletion_pending_count > 100` | WARN empfohlen — Rückstau-Indikator |

**Reaktion bei FAIL:**
1. JSONL-Snapshot laden: `artifacts/compliance/deletions/deletion_records_snapshot.jsonl`
2. Überfällige Record-IDs identifizieren (`status=notified`, `execute_after` abgelaufen)
3. Manuell prüfen: Hält ein Hold die Ausführung auf?
4. Wenn kein Hold: `DeletionScheduler.tick()` manuell triggern oder On-Call benachrichtigen
5. Nach Behebung: Snapshot neu erzeugen und Monitoring erneut ausführen

### 2. Hold-Bestand

**Definition:** Aktive Holds (`status=active`) mit überschrittenem `review_due_at`.

| Schwelle | Aktion |
|---|---|
| `hold_overdue_review_count ≥ 1` | **FAIL** — Compliance Lead benachrichtigen |
| `hold_active_count > 50` | WARN empfohlen — ungewöhnlich hoher Bestand |

**Reaktion bei FAIL:**
1. Überfällige Hold-IDs aus JSONL identifizieren
2. Compliance Lead kontaktieren (zuständige Rolle: `Compliance Lead` / `Legal Counsel`)
3. Vier-Augen-Review durchführen: Hold verlängern oder `release()` aufrufen
4. Snapshot aktualisieren

### 3. Fehlerquote (Export-Log)

**Definition:** Anteil von Export-Einträgen mit `status=error` an allen
Einträgen im konfigurierten Zeitfenster (Standard: 24h).

| Schwelle | Aktion |
|---|---|
| `error_rate ≥ 25%` | **FAIL** — API/Service-Incident wahrscheinlich |
| `error_rate ≥ 10%` | **WARN** — erhöhte Fehlerrate, Ursache untersuchen |
| `error_rate < 10%` | OK |

**Reaktion bei FAIL/WARN:**
1. Export-Log öffnen: `artifacts/compliance/export/export_log_v1.jsonl`
2. Fehlgeschlagene Einträge nach `channel` und `export_kind` gruppieren
3. Wenn Kanal-spezifisch: downstream-System prüfen
4. Wenn global: API-Service-Health prüfen (`check_monitoring_baseline_dev.sh`)
5. Bei Incident: On-Call benachrichtigen (SNS-Topic: `swisstopo-dev-alerts`)

---

## Snapshot-Format

### Löschrekord-Snapshot (JSONL)

Jede Zeile = ein `DeletionRecord` serialisiert als JSON-Objekt:

```json
{
  "record_id": "uuid",
  "document_id": "doc-001",
  "requested_by_role": "Compliance Lead",
  "delete_reason": "DSGVO Art. 17",
  "execute_after": "2026-03-15T00:00:00+00:00",
  "notice_period_days": 7,
  "status": "notified",
  "created_at": "2026-03-01T10:00:00+00:00",
  "notified_at": "2026-03-08T10:00:00+00:00",
  "executed_at": null,
  "canceled_at": null,
  "cancel_reason": null
}
```

### Hold-Rekord-Snapshot (JSONL)

```json
{
  "hold_id": "uuid",
  "document_id": "doc-001",
  "hold_reason": "Laufende Untersuchung",
  "requested_by_role": "Legal Counsel",
  "approved_by_role": "Compliance Lead",
  "counter_approved_by_role": "Security Lead",
  "review_due_at": "2026-03-31T00:00:00+00:00",
  "status": "active",
  "created_at": "2026-03-01T12:00:00+00:00",
  "released_at": null,
  "release_reason": null
}
```

### Export-Log-Format

Gemäß `docs/compliance/EXPORT_LOGGING_STANDARD_V1.md` (JSONL, Pflichtfelder:
`actor`, `exported_at_utc`, `channel`, `status`).

---

## Automatisierung / CI-Integration

```yaml
# Beispiel: GitHub Actions Job (weekly)
- name: Compliance Ops Monitoring
  run: |
    python scripts/check_compliance_ops_monitoring.py
  env:
    COMPLIANCE_DELETION_LOG: artifacts/compliance/deletions/deletion_records_snapshot.jsonl
    COMPLIANCE_HOLD_LOG: artifacts/compliance/holds/hold_records_snapshot.jsonl
```

---

## Verwandte Dokumente

- [`docs/compliance/HOLD_GOVERNANCE_V1.md`](HOLD_GOVERNANCE_V1.md)
- [`docs/compliance/EXPORT_LOGGING_STANDARD_V1.md`](EXPORT_LOGGING_STANDARD_V1.md)
- [`docs/compliance/ACCEPTANCE_TEST_CATALOG_V1.md`](ACCEPTANCE_TEST_CATALOG_V1.md)
- [`docs/OPERATIONS.md`](../OPERATIONS.md)
- [`scripts/check_monitoring_baseline_dev.sh`](../../scripts/check_monitoring_baseline_dev.sh)
