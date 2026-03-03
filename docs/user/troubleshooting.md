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

## GUI Auth / Session (BFF) – Fehlerbilder

Kanonischer Referenz-Flow (Login/Callback/Session/Logout):
[`docs/gui/GUI_AUTH_BFF_SESSION_FLOW.md`](../gui/GUI_AUTH_BFF_SESSION_FLOW.md)

Die folgenden Fehlerbilder sind GUI-spezifisch und ergänzen die API-Fehler oben.

### 1) Redirect-Loop zwischen `/auth/login` und `/auth/callback`

**Symptom**
- Browser springt wiederholt zwischen Login und Callback, GUI lädt nicht fertig.

**Typische Ursache**
- Fehlender/abgelaufener Session-Cookie oder `state`-Mismatch im Callback.

**Reproduzierbarer Check**

```bash
# Ohne gültigen Session-Cookie führt Callback typischerweise zu 4xx JSON-Fehler
curl -i -sS "http://127.0.0.1:8080/auth/callback?code=dummy&state=dummy"
```

**Fix**
- Login neu starten über `/auth/login?next=%2Fgui` (keinen alten Callback-Tab wiederverwenden).
- Bei wiederholtem Fehler OIDC-Redirect-URI und Clock-Skew prüfen.

### 2) Session abgelaufen -> GUI fällt auf Login zurück

**Symptom**
- Geschützte Routen (`/gui`, `/history`, `/results/<id>`) leiten unerwartet auf `/auth/login` um.

**Typische Ursache**
- Session-TTL erreicht oder Session serverseitig invalidiert.

**Reproduzierbarer Check**

```bash
# Erwartet bei fehlender/abgelaufener Session: 302 auf /auth/login?next=...
curl -i -sS "http://127.0.0.1:8080/gui" | sed -n '1,12p'
```

**Fix**
- Erneut einloggen und den Flow von der Zielroute aus neu starten.
- Bei häufigen Expiry-Ereignissen `BFF_SESSION_TTL_SECONDS` und Refresh-Pfad prüfen.

### 3) Logout ohne sichtbare Wirkung

**Symptom**
- Nach „Logout" scheint die GUI weiter eingeloggt oder springt sofort wieder zurück.

**Typische Ursache**
- Cookie wurde nicht gelöscht oder Provider-Logout-Redirect fehlt/ist inkonsistent.

**Reproduzierbarer Check**

```bash
curl -i -sS "http://127.0.0.1:8080/auth/logout" | sed -n '1,20p'
# Erwartete Indizien:
# - Set-Cookie mit Max-Age=0 (Session-Löschung)
# - Location auf /auth/login oder OIDC-Logout-Endpoint
```

**Fix**
- Prüfen, dass `Set-Cookie` wirklich `Max-Age=0` enthält.
- OIDC-Logout-Endpoint + Post-Logout-Redirect im Provider validieren.

### 4) 401/403 bei GUI-API-Aufrufen trotz vorherigem Login

**Symptom**
- GUI zeigt Auth-Fehler bei Analyze/History trotz erfolgreichem Login-Flow.

**Typische Ursache**
- Delegierter Upstream-Token abgelaufen/ungültig, Refresh fehlgeschlagen oder Session nicht mitgesendet.

**Reproduzierbarer Check**

```bash
# Ohne Session-Cookie muss der BFF-Proxy Auth-Fehler liefern
curl -i -sS "http://127.0.0.1:8080/portal/api/analyze/history?limit=5"

# Mit Browser-DevTools prüfen:
# - Request enthält Session-Cookie
# - Response enthält konsistente 401/403 statt stiller JS-Fehler
```

**Fix**
- Session neu aufbauen (frischer Login) und erneut testen.
- Bei persistierendem Fehler BFF-Token-Refresh-/Delegationspfad sowie OIDC-Issuer/JWKS-Konfiguration prüfen.

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
- [Configuration / ENV](./configuration-env.md)
- [API Usage Guide](./api-usage.md)
- [Operations Quick Guide](./operations-runbooks.md)
- [Operations (Infra/Team)](../OPERATIONS.md)
