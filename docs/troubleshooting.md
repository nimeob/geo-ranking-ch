# Dev Troubleshooting — Top 10 Fehlerbilder

Diese Seite sammelt **verifizierte** Dev-Fehlerbilder aus dem aktuellen Projekt-Setup.
Template pro Eintrag: **Symptom → Probable Cause → Check → Fix**.

> Standard-Entry-Point für lokale Smokes: `make dev-smoke`

## 1) `make dev-smoke` bricht sofort mit `required command not found` ab

**Symptom**
- `make dev-smoke` endet direkt mit `ERROR: required command not found: python3` oder `curl`.

**Probable Cause**
- Lokale Dev-Abhängigkeiten fehlen im PATH.

**Check**
```bash
command -v python3
command -v curl
```

**Fix**
- Fehlendes Tool installieren und Shell/Terminal neu öffnen.
- Danach erneut ausführen: `make dev-smoke`.

---

## 2) `make dev-smoke` meldet `missing or non-executable smoke script`

**Symptom**
- Fehler: `ERROR: missing or non-executable smoke script: ./scripts/check_bl334_split_smokes.sh`

**Probable Cause**
- Script fehlt im Checkout oder Execute-Bit ging verloren.

**Check**
```bash
ls -l ./scripts/check_bl334_split_smokes.sh
```

**Fix**
```bash
git checkout -- ./scripts/check_bl334_split_smokes.sh
chmod +x ./scripts/check_bl334_split_smokes.sh
```

---

## 3) API startet lokal nicht (`/health` bleibt nicht erreichbar)

**Symptom**
- Smoke läuft in Timeout (`timeout waiting for http://127.0.0.1:<port>/health`).

**Probable Cause**
- API-Prozess crasht beim Start (z. B. defekte lokale Änderungen oder Python-Umgebung).

**Check**
```bash
# letzten API-Log aus dem letzten Smoke öffnen
ls -t artifacts/bl334/*-api-smoke.log | head -n 1 | xargs -r sed -n '1,120p'
```

**Fix**
- Traceback im Log beheben.
- Danach Smoke erneut starten: `make dev-smoke`.

---

## 4) UI startet lokal nicht (`/healthz` bleibt nicht erreichbar)

**Symptom**
- Smoke läuft in Timeout auf `http://127.0.0.1:<port>/healthz`.

**Probable Cause**
- UI-Prozess crasht beim Start oder kann API-Basis nicht nutzen.

**Check**
```bash
ls -t artifacts/bl334/*-ui-smoke.log | head -n 1 | xargs -r sed -n '1,120p'
```

**Fix**
- Fehler im UI-Log beheben.
- API separat testen: `python -m src.api.web_service` und `curl -sS http://127.0.0.1:8080/health`.

---

## 5) Lokaler Start scheitert mit `Address already in use`

**Symptom**
- Beim lokalen Service-Start erscheint `OSError: [Errno 98] Address already in use`.

**Probable Cause**
- Port ist bereits durch einen anderen lokalen Prozess belegt.

**Check**
```bash
ss -ltnp | grep ':8080'
```

**Fix**
- Belegenden Prozess stoppen **oder** alternativen Port setzen:
```bash
PORT=18080 python -m src.api.web_service
curl -sS http://127.0.0.1:18080/health
```

---

## 6) `POST /analyze` liefert `401 unauthorized`

**Symptom**
- API antwortet mit `401` und `error=unauthorized`.

**Probable Cause**
- Auth-Guard aktiv, aber Bearer-Token fehlt/ist falsch.

**Check**
```bash
curl -i -sS -X POST "http://127.0.0.1:8080/analyze" \
  -H "Content-Type: application/json" \
  -d '{"query":"St. Gallen"}'
```

**Fix**
```bash
curl -i -sS -X POST "http://127.0.0.1:8080/analyze" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"query":"St. Gallen"}'
```

---

## 7) `POST /analyze` liefert `400 bad_request`

**Symptom**
- API antwortet `400` mit Validierungsfehler.

**Probable Cause**
- Ungültiger Payload (`query` leer, `intelligence_mode` ungültig, `timeout_seconds` ungültig).

**Check**
```bash
curl -i -sS -X POST "http://127.0.0.1:8080/analyze" \
  -H "Content-Type: application/json" \
  -d '{"query":"","intelligence_mode":"fast"}'
```

**Fix**
- `query` als nicht-leeren String senden.
- `intelligence_mode` auf `basic|extended|risk` begrenzen.
- `timeout_seconds` als endliche Zahl `> 0` setzen.

---

## 8) Doku-Gate schlägt fehl (`markdown links`)

**Symptom**
- `pytest tests/test_markdown_links.py` schlägt fehl.

**Probable Cause**
- Neuer Link zeigt auf nicht vorhandene Datei oder falschen relativen Pfad.

**Check**
```bash
pytest -q tests/test_markdown_links.py
```

**Fix**
- Defekten Linkpfad in der genannten Datei korrigieren.
- Danach Gate erneut ausführen.

---

## 9) User-Doku-Guard schlägt fehl

**Symptom**
- `tests/test_user_docs.py` fehlschlägt nach Doku-Änderungen.

**Probable Cause**
- Erwartete Kernhinweise/Referenzen in README/CONTRIBUTING wurden entfernt oder inkonsistent geändert.

**Check**
```bash
pytest -q tests/test_user_docs.py
```

**Fix**
- Betroffene Doku-Dateien auf die erwarteten Referenzen synchronisieren.
- Typischerweise README + CONTRIBUTING gemeinsam aktualisieren.

---

## 10) Virtuelle Umgebung inkonsistent (Imports/Module fehlen)

**Symptom**
- Tests oder Start schlagen mit `ModuleNotFoundError` oder alten Paketversionen fehl.

**Probable Cause**
- Veraltete/inkonsistente lokale `.venv`.

**Check**
```bash
python3 -V
python3 -m pip --version
pytest -q tests/test_bl334_split_smokes_script.py
```

**Fix**
```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
```

Danach Re-Check:
```bash
make dev-smoke
pytest -q
```
