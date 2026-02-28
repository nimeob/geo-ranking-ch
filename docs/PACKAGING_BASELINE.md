# Packaging Baseline (BL-20.7.a)

Ziel dieses Dokuments ist eine **reproduzierbare Build/Run-Basis** für das aktuelle API-only MVP.

## 1) Voraussetzungen

- Python **3.12**
- Docker (optional, für containerisierte Ausführung)
- Git-Checkout auf einem aktuellen Branch (empfohlen: `main`)

## 2) Build/Run-Matrix (reproduzierbar)

| Modus | Build/Setup | Run | Minimaler Verify-Check |
|---|---|---|---|
| Lokal (venv) | `python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt` | `python -m src.api.web_service` | `curl -fsS http://127.0.0.1:8080/health` |
| Docker lokal | `docker build -t geo-ranking-ch:dev .` | `docker run --rm -p 8080:8080 geo-ranking-ch:dev` | `curl -fsS http://127.0.0.1:8080/health` |
| Test-Baseline | `source .venv/bin/activate` | `pytest tests/test_web_e2e.py -q` | Exit-Code `0` |

> Kompatibilität: `python -m src.web_service` bleibt als Legacy-Wrapper nutzbar; kanonisch ist `python -m src.api.web_service`.

## 3) Konfigurationsmatrix (Packaging/Runtime)

Die Matrix konsolidiert die relevanten Parameter für Build-/Run-Modi und macht Pflicht/Optional, Defaults und Beispielwerte auf einen Blick sichtbar.

| Parameter | Kontext | Pflicht | Default | Beispiel | Referenz |
|---|---|---|---|---|---|
| `HOST` | Service-Run (lokal/container) | nein | `0.0.0.0` | `127.0.0.1` | [`docs/user/configuration-env.md`](./user/configuration-env.md) |
| `PORT` | Service-Run (primärer Listen-Port) | nein | – | `8080` | [`docs/user/configuration-env.md`](./user/configuration-env.md) |
| `WEB_PORT` | Service-Run (Fallback-Port) | nein | `8080` | `8081` | [`docs/user/configuration-env.md`](./user/configuration-env.md) |
| `API_AUTH_TOKEN` | Service-Run (`POST /analyze` Auth) | nein | leer | `dev-secret` | [`docs/user/configuration-env.md`](./user/configuration-env.md) |
| `ANALYZE_DEFAULT_TIMEOUT_SECONDS` | Service-Run (Timeout-Default) | nein | `15` | `10` | [`docs/user/configuration-env.md`](./user/configuration-env.md) |
| `ANALYZE_MAX_TIMEOUT_SECONDS` | Service-Run (Timeout-Cap) | nein | `45` | `30` | [`docs/user/configuration-env.md`](./user/configuration-env.md) |
| `DEV_BASE_URL` | Remote-Smoke/Stability | **ja** | – | `https://api.example.ch` | [`docs/user/configuration-env.md`](./user/configuration-env.md) |
| `DEV_API_AUTH_TOKEN` | Remote-Smoke/Stability Auth | nein | leer | `prod-token-redacted` | [`docs/user/configuration-env.md`](./user/configuration-env.md) |
| `SMOKE_MODE` | Remote-Smoke (`basic\|extended\|risk`) | nein | `basic` | `extended` | [`docs/user/configuration-env.md`](./user/configuration-env.md) |
| `SMOKE_TIMEOUT_SECONDS` | Remote-Smoke Request-Timeout | nein | `20` | `25` | [`docs/user/configuration-env.md`](./user/configuration-env.md) |
| `STABILITY_RUNS` | Stabilitätslauf Iterationen | nein | `6` | `10` | [`docs/user/configuration-env.md`](./user/configuration-env.md) |
| `STABILITY_REPORT_PATH` | Stabilitätslauf Evidenzpfad | nein | `artifacts/bl18.1-remote-stability.ndjson` | `artifacts/stability-nightly.ndjson` | [`docs/user/configuration-env.md`](./user/configuration-env.md) |

**Hinweis zur Detailtiefe:** Validierungsregeln (z. B. ASCII-/Whitespace-Guards, erlaubte Modi, Zahlenbereiche) bleiben im User-Guide die führende Referenz. Diese Matrix ist der Packaging-spezifische Kompakt-Überblick.

## 4) Reproduzierbarer Local-Run (Schrittfolge)

```bash
git checkout main
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m src.api.web_service
```

Parallel (zweite Shell):

```bash
curl -fsS http://127.0.0.1:8080/health
```

Erwartung: JSON mit `{"ok": true, ...}` und HTTP `200`.

## 5) Reproduzierbarer Docker-Run

```bash
docker build -t geo-ranking-ch:dev .
docker run --rm -p 8080:8080 geo-ranking-ch:dev
```

Parallel:

```bash
curl -fsS http://127.0.0.1:8080/health
```

### Basis-Release-Checkliste (API-only Packaging)

Diese Checkliste ist der minimale Gate für einen releasefähigen API-only Stand. Sie ergänzt die allgemeine Release-Sequenz in [`docs/OPERATIONS.md`](./OPERATIONS.md#release-checkliste).

| Check | Kommando / Nachweis | Erwartung |
|---|---|---|
| Build (lokal) | `python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt` | Dependencies lösen ohne Fehler |
| Run (lokal) | `python -m src.api.web_service` | Service startet ohne Traceback |
| Smoke | `curl -fsS http://127.0.0.1:8080/health` | HTTP `200`, `{"ok": true}` |
| Test-Gate | `pytest tests/test_web_e2e.py -q` | Exit-Code `0` |
| Doku-Check | `./scripts/check_docs_quality_gate.sh` | Exit-Code `0` |
| Artefakt-Nachweis | Test-/Run-Ausgaben in `artifacts/` oder PR-Beschreibung verlinken | Prüfbare Evidenz vorhanden |

### Follow-ups / offene Abhängigkeiten

- ✅ Konfigurationsmatrix-Vertiefung (Pflicht/Optional, Defaults, Beispiele) ist mit **Issue #55** in Abschnitt „Konfigurationsmatrix (Packaging/Runtime)" umgesetzt.
- Diese Checkliste bleibt absichtlich API-only; GUI-spezifische Release-Gates folgen mit BL-20.6.

## 6) Scope-Grenze dieser Baseline

- Fokus: **Build/Run-Reproduzierbarkeit** für API-only MVP
- Nicht enthalten: Distribution/Registry-Release-Prozess, semantische Versionierung, Artefakt-Signing
- Diese Follow-ups sind in BL-20.7.a-Child-Issues getrennt nachgezogen

## 7) Verweise

- User-Betriebsdoku: [`docs/user/operations-runbooks.md`](./user/operations-runbooks.md)
- Konfigurations-Referenz: [`docs/user/configuration-env.md`](./user/configuration-env.md)
- Parent-Backlog: [`docs/BACKLOG.md`](./BACKLOG.md)
