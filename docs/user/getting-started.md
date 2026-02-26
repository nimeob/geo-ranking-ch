# Getting Started

Dieser Guide bringt dich in wenigen Minuten zum ersten erfolgreichen API-Call.

## 1) Voraussetzungen

- Python **3.12**
- Git
- (optional) `curl`

## 2) Projekt lokal starten

```bash
git clone https://github.com/nimeob/geo-ranking-ch.git
cd geo-ranking-ch

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Service starten:

```bash
python -m src.web_service
```

Standard-Port ist `8080` (ENV `PORT`, Fallback `WEB_PORT`).

## 3) Health prüfen

```bash
curl -sS http://localhost:8080/health
```

Erwartung (Beispiel):

```json
{"ok":true,"service":"geo-ranking-ch"}
```

## 4) Erster `/analyze`-Call

```bash
curl -sS -X POST "http://localhost:8080/analyze" \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: gs-001" \
  -d '{"query":"Bahnhofstrasse 1, 8001 Zürich","intelligence_mode":"extended","timeout_seconds":15}'
```

Erwartung:
- HTTP `200`
- JSON mit `ok: true`
- Feld `result` vorhanden
- `request_id` in JSON gesetzt (und i. d. R. auch im Response-Header `X-Request-Id`)

## 5) Optional: Auth aktivieren

Wenn der Service mit `API_AUTH_TOKEN` läuft, ist `POST /analyze` geschützt.

Start mit Token:

```bash
API_AUTH_TOKEN="dev-secret" python -m src.web_service
```

Request mit Bearer Token:

```bash
curl -sS -X POST "http://localhost:8080/analyze" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-secret" \
  -d '{"query":"St. Gallen"}'
```

Ohne gültigen Token kommt `401 unauthorized`.

## 6) Schnelltest-Suite

```bash
./scripts/run_webservice_e2e.sh
```

Optional gegen dev-URL:

```bash
DEV_BASE_URL="https://<dein-endpoint>" ./scripts/run_webservice_e2e.sh
```

## 7) Häufige Stolpersteine

- `400 bad_request` bei ungültigem `intelligence_mode` (nur `basic|extended|risk`)
- `400 bad_request` bei ungültigem `timeout_seconds` (`nan`, `inf`, `<=0`)
- `401 unauthorized`, wenn `API_AUTH_TOKEN` gesetzt ist, aber kein/ungültiger Bearer-Token gesendet wird
- Verwechslung der URL (`/health` vs. `/analyze`)

---

Nächste Seite: **[API Usage Guide](./api-usage.md)**
