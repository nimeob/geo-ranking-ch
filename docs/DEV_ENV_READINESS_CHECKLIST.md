# Dev Environment Readiness Checklist

**Issue:** [#1148](https://github.com/nimeob/geo-ranking-ch/issues/1148)
**Stand:** 2026-03-04

Kurze, reproduzierbare Onboarding-Checkliste für einen frischen Dev-Checkout.

## 1) Readiness-Checklist (Quick Gate)

Wenn alle Punkte grün sind, ist die lokale Dev-Umgebung einsatzbereit.

- [ ] Python 3.12 verfügbar (`python3.12 --version`)
- [ ] Virtuelle Umgebung erstellt und aktiviert (`.venv`)
- [ ] Dependencies installiert (`requirements.txt` + `requirements-dev.txt`)
- [ ] API-Health lokal erreichbar (`GET /healthz`)
- [ ] Basis-Testlauf grün (`pytest -q` oder fokussierter Target-Lauf)
- [ ] Pre-PR-Gate ausführbar (`make dev-check`)

## 2) Copy/Paste Verify-Kommandos

> Die folgende Sequenz ist bewusst copy/paste-fähig für frische Onboarding-Läufe.

```bash
git clone https://github.com/nimeob/geo-ranking-ch.git
cd geo-ranking-ch

python3.12 --version
python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt

# API starten (Shell A)
python -m src.api.web_service
```

In **Shell B** (mit aktivierter `.venv`):

```bash
curl -fsS http://localhost:8080/healthz
pytest -q tests/test_user_docs.py tests/test_markdown_links.py
make dev-check
```

Erwartung:
- `curl` liefert HTTP 200
- `pytest` läuft ohne Failures
- `make dev-check` endet mit Exit-Code 0

## 3) Häufige Fehlerbilder (mit Fix)

### Fehlerbild A — `python3.12: command not found`

**Symptom:** Setup scheitert beim Erstellen der venv.

**Fix:**
- Python 3.12 installieren (z. B. via Paketmanager/pyenv)
- Danach erneut prüfen:

```bash
python3.12 --version
python3.12 -m venv .venv
```

### Fehlerbild B — `ModuleNotFoundError` / fehlende Pakete beim Start

**Symptom:** `python -m src.api.web_service` bricht mit Importfehlern ab.

**Fix:** venv aktivieren und Dependencies vollständig installieren:

```bash
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### Fehlerbild C — `Address already in use` auf Port `8080`

**Symptom:** API oder UI startet nicht wegen belegtem Port.

**Fix:**
- Port-Konflikt prüfen:

```bash
lsof -i :8080
```

- Entweder störenden Prozess beenden **oder** Port überschreiben:

```bash
PORT=18080 python -m src.api.web_service
curl -fsS http://localhost:18080/healthz
```

### Fehlerbild D — `make dev-check` schlägt wegen `pre-commit` fehl

**Symptom:** Lint-Step kann `pre-commit` nicht finden.

**Fix:**

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install
make dev-check
```

## 4) Referenzen

- [`CONTRIBUTING.md`](../CONTRIBUTING.md)
- [`README.md` (Lokale Entwicklung)](../README.md#lokale-entwicklung)
- [`docs/local-dev.md`](./local-dev.md)
