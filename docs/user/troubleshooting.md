# Troubleshooting

Dieser Guide hilft bei den häufigsten Fehlerbildern rund um den Webservice.

## Schnelle Diagnose in 3 Schritten

1. **Erreichbarkeit prüfen**

```bash
curl -i -sS "http://localhost:8080/health"
```

2. **API minimal testen**

```bash
curl -i -sS -X POST "http://localhost:8080/analyze" \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: ts-quickcheck-001" \
  -d '{"query":"St. Gallen"}'
```

3. **Request-ID für Logs notieren**
   - Response-Header: `X-Request-Id`
   - Response-JSON: `request_id`

---

## 401 `unauthorized`

**Symptom**
- `POST /analyze` liefert `401` mit `error=unauthorized`.

**Typische Ursache**
- `API_AUTH_TOKEN` ist auf dem Service gesetzt, aber im Request fehlt der Header `Authorization: Bearer <token>` oder der Token ist falsch.

**Checks**

```bash
# ohne Token (erwartet 401, wenn Auth aktiv)
curl -i -sS -X POST "http://localhost:8080/analyze" \
  -H "Content-Type: application/json" \
  -d '{"query":"St. Gallen"}'

# mit Token
curl -i -sS -X POST "http://localhost:8080/analyze" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <API_AUTH_TOKEN>" \
  -d '{"query":"St. Gallen"}'
```

**Fix**
- Sicherstellen, dass Client und Service denselben Tokenwert verwenden.
- Auf Whitespace im Token achten (z. B. beim Setzen über ENV-Dateien).

---

## 400 `bad_request`

**Symptom**
- `POST /analyze` liefert `400` mit `error=bad_request`.

**Häufige Ursachen & Gegenmaßnahmen**

1. `query` fehlt oder ist leer/whitespace-only.
   - Fix: `query` als nicht-leeren String senden.
2. `intelligence_mode` ist ungültig.
   - Erlaubt: `basic`, `extended`, `risk` (Trim + case-insensitive).
3. `timeout_seconds` ist ungültig.
   - Muss eine **endliche Zahl > 0** sein (`nan`, `inf`, `0`, negative Werte sind ungültig).

**Repro/Check**

```bash
# ungültiger mode -> 400
curl -i -sS -X POST "http://localhost:8080/analyze" \
  -H "Content-Type: application/json" \
  -d '{"query":"St. Gallen","intelligence_mode":"fast"}'
```

---

## 504 `timeout`

**Symptom**
- `POST /analyze` liefert `504` mit `error=timeout`.

**Typische Ursache**
- Upstream/Analyse läuft länger als erlaubt.

**Checks**
- Request mit realistischem `timeout_seconds` erneut testen.
- Last/Netzwerk prüfen (lokal vs. dev vergleichen).

**Fix**
- `timeout_seconds` moderat erhöhen (innerhalb `ANALYZE_MAX_TIMEOUT_SECONDS`).
- Bei wiederholten Timeouts Query vereinfachen und Logs mit `request_id` prüfen.

---

## 404 `not_found` oder „falscher Endpoint"

**Symptom**
- `404 not_found` bei einem erwarteten API-Call.

**Typische Ursache**
- Falscher Pfad oder Base-URL verwechselt (`/health` statt `/analyze`).

**Checks**

```bash
curl -i -sS "http://localhost:8080/health"
curl -i -sS "http://localhost:8080/version"
```

Der Service toleriert zwar z. B. trailing/double slashes, aber der Endpunkt muss fachlich korrekt sein.

---

## Request-ID fehlt oder passt nicht

**Symptom**
- Erwartete Request-ID taucht nicht in der Antwort auf.

**Typische Ursache**
- Gesendete Header-ID ist ungültig (z. B. Whitespace, Non-ASCII, `,`/`;`, >128 Zeichen).

**Wichtig**
- Ungültige IDs werden verworfen.
- Dann wird die nächste gültige Header-Quelle verwendet oder eine ID automatisch erzeugt.

**Fix**
- Knappe ASCII-ID ohne Leerzeichen verwenden, z. B. `req-20260226-001`.

---

## Smoke/Stability-Checks für reproduzierbare Diagnose

Für reproduzierbare Fehleranalyse:

```bash
# lokale + optionale dev E2E-Tests
./scripts/run_webservice_e2e.sh

# dedizierter Remote-Smoke gegen /analyze
DEV_BASE_URL="https://<endpoint>" ./scripts/run_remote_api_smoketest.sh

# kurzer Stabilitätslauf mit NDJSON-Report
DEV_BASE_URL="https://<endpoint>" ./scripts/run_remote_api_stability_check.sh
```

Wenn ein Lauf fehlschlägt:
- Exit-Code notieren
- erzeugtes Artefakt (`SMOKE_OUTPUT_JSON` / `STABILITY_REPORT_PATH`) sichern
- `request_id` aus dem Fehlerfall in die Diagnose übernehmen

---

## Wann eskalieren?

Eskalieren (Issue/PR-Kommentar), wenn:
- derselbe reproduzierbare Fehler nach den Checks weiter besteht,
- `500 internal` wiederholt auftritt,
- oder 401/504 nur in einer Umgebung (dev/prod) reproduzierbar ist.

Am besten direkt mitliefern:
- exakter `curl`-Befehl,
- HTTP-Status + Fehler-JSON,
- `request_id`,
- betroffene Umgebung (lokal/dev).

---

Weiterführend:
- [Getting Started](./getting-started.md)
- [API Usage Guide](./api-usage.md)
- [Operations Quick Guide](./operations-runbooks.md)
- [Operations (Infra/Team)](../OPERATIONS.md)
