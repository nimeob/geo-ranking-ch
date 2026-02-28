# Webservice-Test: Espenmoosstrasse 18, 9008 St. Gallen

- **Issue:** #267 (BL-YY.4)
- **Datum (UTC):** 2026-02-27
- **Umgebung:** lokal (`127.0.0.1:18080`)
- **Service-Start:** `PORT=18080 PYTHONPATH=. python3 -m src.api.web_service` (Legacy-Wrapper: `python3 -m src.web_service`)

## Ziel
Reproduzierbarer Testlauf für die Adresse `Espenmoosstrasse 18, 9008 St. Gallen` inkl. dokumentiertem Request, HTTP-Status und Output-Artefakten.

## Durchgeführter Test

### 1) Health-Check
```bash
curl -sS http://127.0.0.1:18080/health
```

Ergebnis: `{"ok": true, ...}`

### 2) Analyze-Request
```bash
REQ_ID="manual-espenmoos-$(date -u +%Y%m%dT%H%M%SZ)"
curl -sS \
  -D /tmp/espenmoos_headers.txt \
  -o /tmp/espenmoos_body.json \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: ${REQ_ID}" \
  -X POST http://127.0.0.1:18080/analyze \
  -d '{"query":"Espenmoosstrasse 18, 9008 St. Gallen","intelligence_mode":"basic","timeout_seconds":25}'
```

HTTP-Status: `HTTP/1.0 200 OK`

## Output-Artefakte
- Header-Rohdaten: [`reports/manual/espenmoos_headers.txt`](../../reports/manual/espenmoos_headers.txt)
- Vollständiger JSON-Output: [`reports/manual/espenmoos_response.json`](../../reports/manual/espenmoos_response.json)
- Kompaktzusammenfassung: [`reports/manual/espenmoos_summary.json`](../../reports/manual/espenmoos_summary.json)

## Ergebnis-Zusammenfassung (aus `espenmoos_summary.json`)
- `ok: true`
- `matched_address: "Espenmoosstrasse 18 9008 St. Gallen"`
- Confidence: `90/100` (`level: high`)
- Ambiguität: `level: high`, `score_gap_to_next: 0.0`
- `suitability_light`: `score=82`, `traffic_light=green`, `classification=geeignet`
- Pflichtquellenstatus (`source_health`):
  - `geoadmin_search: ok`
  - `geoadmin_gwr: ok`
  - `gwr_codes: ok`

## Kurzfazit
- Der Webservice-Call war technisch erfolgreich (`200 OK`) und lieferte ein vollständiges, strukturiertes Ergebnisobjekt.
- Die Confidence ist hoch, gleichzeitig signalisiert die Ambiguitätsmetrik (`score_gap_to_next = 0.0`) einen engen Kandidatenabstand; das passt zur Executive-Summary (`review`).
- Für den Basic-Modus sind optionale Quellen erwartungsgemäß teils deaktiviert (z. B. `osm_poi_overpass`, `google_news_rss`).
