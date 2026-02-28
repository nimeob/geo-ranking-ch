# BL-31 Routing/TLS Smoke-Catch-up (Issue #336)

## Ziel
Reproduzierbarer Smoke-Ablauf für die aktuell offenen BL-31-Routing/TLS-Änderungen mit drei Pflichtchecks:

1. API-Health (`/health`)
2. UI-Reachability (`/healthz`)
3. CORS-Baseline (Preflight auf `POST /analyze`)

Der Ablauf ist bewusst zweistufig aufgebaut:
- **Baseline-Modus (`BL31_STRICT_CORS=0`)**: CORS-Gap wird als `warn` sichtbar, blockiert den Lauf aber nicht.
- **Strict-Modus (`BL31_STRICT_CORS=1`)**: CORS muss korrekt sein, sonst Hard-Fail.

---

## Voraussetzungen
- Python 3
- `curl`
- Repo-Root als aktuelles Verzeichnis

---

## 1) API und UI lokal starten

### Terminal A (API)

```bash
HOST=127.0.0.1 PORT=18080 python3 -m src.web_service
```

### Terminal B (UI)

```bash
HOST=127.0.0.1 PORT=18081 UI_API_BASE_URL="http://127.0.0.1:18080" python3 -m src.ui_service
```

---

## 2) Smoke im Baseline-Modus laufen lassen

```bash
BL31_API_BASE_URL="http://127.0.0.1:18080" \
BL31_APP_BASE_URL="http://127.0.0.1:18081" \
BL31_CORS_ORIGIN="http://127.0.0.1:18081" \
BL31_STRICT_CORS="0" \
BL31_OUTPUT_JSON="artifacts/bl31-routing-tls-smoke-baseline.json" \
./scripts/run_bl31_routing_tls_smoke.sh
```

### Erwartete Ausgabe (solange #329 offen ist)

- API-Health: `pass`
- APP-Reachability: `pass`
- CORS-Baseline: typischerweise `warn` mit `reason=missing_allow_origin`
- OVERALL: `pass`

Beispiel:

```text
[BL-31] API health (.../health): pass (...)
[BL-31] APP reachability (.../healthz): pass (...)
[BL-31] CORS baseline (.../analyze, origin=...): warn (..., reason=missing_allow_origin, ...)
[BL-31] OVERALL: pass (ok)
```

---

## 3) Smoke im Strict-Modus (Abnahmemodus)

```bash
BL31_API_BASE_URL="http://127.0.0.1:18080" \
BL31_APP_BASE_URL="http://127.0.0.1:18081" \
BL31_CORS_ORIGIN="http://127.0.0.1:18081" \
BL31_STRICT_CORS="1" \
./scripts/run_bl31_routing_tls_smoke.sh
```

### Erwartete Ausgabe vor #329
- CORS-Baseline nicht `pass` → `OVERALL: fail (cors_baseline_failed)` und Exit-Code `1`.

### Erwartete Ausgabe nach #329
- Alle drei Checks `pass` und Exit-Code `0`.

---

## Artefaktstruktur (`BL31_OUTPUT_JSON`)
Das Script kann einen strukturierten Nachweis schreiben, z. B.:

- `overall.status` / `overall.reason`
- `checks.api_health.*`
- `checks.app_reachability.*`
- `checks.cors_baseline.*`

Damit ist der Lauf in CI oder manuellen Reviews nachvollziehbar.

---

## Follow-up-Risiken / Abhängigkeiten

### Abhängigkeit zu #329 (BL-31.3 Routing + TLS)
- Der CORS-Teil ist aktuell als **Baseline-Warnung** erwartbar, solange host-basiertes Routing/CORS-Policy für `app` → `api` noch nicht final umgesetzt ist.
- Abnahmekriterium für #329: Strict-Modus (`BL31_STRICT_CORS=1`) muss stabil grün laufen.

### Abhängigkeit zu #330 (BL-31.4 Deploy-/Rollback-Runbooks)
- Für reproduzierbare Umgebungs-Smokes (dev/stage/prod) fehlen noch service-spezifische Standardwerte/Schritte für `app`- und `api`-Domains inklusive Rollback-Reihenfolge.
- #330 soll die verbindliche Ausführungsreihenfolge und Endpoint-Matrix dokumentieren, sodass dieser Smoke-Runbook ohne Interpretationsspielraum in Deploy/Rollback genutzt werden kann.
