# Packaging Baseline (BL-20.7.a)

Ziel dieses Dokuments ist eine **reproduzierbare Build/Run-Basis** für das aktuelle API-only MVP.

## 1) Voraussetzungen

- Python **3.12**
- Docker (optional, für containerisierte Ausführung)
- Git-Checkout auf einem aktuellen Branch (empfohlen: `main`)

## 2) Build/Run-Matrix (reproduzierbar)

| Modus | Build/Setup | Run | Minimaler Verify-Check |
|---|---|---|---|
| Lokal (venv) | `python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt` | `python -m src.web_service` | `curl -fsS http://127.0.0.1:8080/health` |
| Docker lokal | `docker build -t geo-ranking-ch:dev .` | `docker run --rm -p 8080:8080 geo-ranking-ch:dev` | `curl -fsS http://127.0.0.1:8080/health` |
| Test-Baseline | `source .venv/bin/activate` | `pytest tests/test_web_e2e.py -q` | Exit-Code `0` |

## 3) Reproduzierbarer Local-Run (Schrittfolge)

```bash
git checkout main
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m src.web_service
```

Parallel (zweite Shell):

```bash
curl -fsS http://127.0.0.1:8080/health
```

Erwartung: JSON mit `{"ok": true, ...}` und HTTP `200`.

## 4) Reproduzierbarer Docker-Run

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
| Run (lokal) | `python -m src.web_service` | Service startet ohne Traceback |
| Smoke | `curl -fsS http://127.0.0.1:8080/health` | HTTP `200`, `{"ok": true}` |
| Test-Gate | `pytest tests/test_web_e2e.py -q` | Exit-Code `0` |
| Doku-Check | `./scripts/check_docs_quality_gate.sh` | Exit-Code `0` |
| Artefakt-Nachweis | Test-/Run-Ausgaben in `artifacts/` oder PR-Beschreibung verlinken | Prüfbare Evidenz vorhanden |

### Follow-ups / offene Abhängigkeiten

- Konfigurationsmatrix-Vertiefung (Pflicht/Optional, Defaults, Sensitivität) erfolgt separat in Issue **#55**.
- Diese Checkliste bleibt absichtlich API-only; GUI-spezifische Release-Gates folgen mit BL-20.6.

## 5) Scope-Grenze dieser Baseline

- Fokus: **Build/Run-Reproduzierbarkeit** für API-only MVP
- Nicht enthalten: Distribution/Registry-Release-Prozess, semantische Versionierung, Artefakt-Signing
- Diese Follow-ups sind in BL-20.7.a-Child-Issues getrennt nachgezogen

## 6) Verweise

- User-Betriebsdoku: [`docs/user/operations-runbooks.md`](./user/operations-runbooks.md)
- Konfigurations-Referenz: [`docs/user/configuration-env.md`](./user/configuration-env.md)
- Parent-Backlog: [`docs/BACKLOG.md`](./BACKLOG.md)
