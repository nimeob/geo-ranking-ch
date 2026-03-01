> **Diese Datei wurde konsolidiert.** Aktuelle kanonische Version: [RUNBOOKS.md](RUNBOOKS.md)

---

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
HOST=127.0.0.1 PORT=18080 CORS_ALLOW_ORIGINS="http://127.0.0.1:18081" python3 -m src.api.web_service
```

### Terminal B (UI)

```bash
HOST=127.0.0.1 PORT=18081 UI_API_BASE_URL="http://127.0.0.1:18080" python3 -m src.ui.service
```

> Legacy-Kompatibilität: `src.web_service` und `src.ui_service` bleiben als Wrapper weiterhin nutzbar.

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

### Erwartete Ausgabe (nach #329, mit gesetzter API-Allowlist)

Voraussetzung: API läuft mit `CORS_ALLOW_ORIGINS="http://127.0.0.1:18081"` (oder passender UI-Origin).

- API-Health: `pass`
- APP-Reachability: `pass`
- CORS-Baseline: `pass`
- OVERALL: `pass`

Beispiel:

```text
[BL-31] API health (.../health): pass (...)
[BL-31] APP reachability (.../healthz): pass (...)
[BL-31] CORS baseline (.../analyze, origin=...): pass (..., reason=ok, ...)
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

### Erwartete Ausgabe im Strict-Modus
- Mit passender API-Allowlist (`CORS_ALLOW_ORIGINS=<UI-Origin>`) sind alle drei Checks `pass` und Exit-Code `0`.
- Ohne passende Allowlist ist ein Hard-Fail erwartbar: `OVERALL: fail (cors_baseline_failed)` mit Exit-Code `1`.

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
- Host-basiertes Routing (`app`/`api`) und CORS-Allowlist für `POST/OPTIONS /analyze` sind umgesetzt.
- Abnahme erfolgt über Strict-Modus (`BL31_STRICT_CORS=1`) mit passender `CORS_ALLOW_ORIGINS`-Konfiguration auf der API.

### Abhängigkeit zu #330 (BL-31.4 Deploy-/Rollback-Runbooks)
- Für reproduzierbare Umgebungs-Smokes (dev/stage/prod) fehlen noch service-spezifische Standardwerte/Schritte für `app`- und `api`-Domains inklusive Rollback-Reihenfolge.
- #330 soll die verbindliche Ausführungsreihenfolge und Endpoint-Matrix dokumentieren, sodass dieser Smoke-Runbook ohne Interpretationsspielraum in Deploy/Rollback genutzt werden kann.
