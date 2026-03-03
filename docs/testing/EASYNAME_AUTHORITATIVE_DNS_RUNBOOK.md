# Easyname authoritative DNS publish verification (Issue #904)

## Zweck

Runbook für den Nachweis, dass DNS-Änderungen für `georanking.ch` auf den **autoritativen** Easyname-Nameservern (`ns1.easyname.eu`, `ns2.easyname.eu`) tatsächlich publiziert sind.

Hintergrund: In #904 wurde beobachtet, dass Easyname-API-Write-Calls zwar `success` liefern können, aber ohne autoritative Publikation wirkungslos bleiben.

## Verbindlicher Publish-Path

1. DNS-Änderung über den **autoritativen Operator-Path** durchführen (Easyname Control Panel / bestätigter Provider-Path).
2. Danach immer gegen beide autoritativen NS verifizieren.
3. Erst bei konsistenten Antworten (beide NS gleich) gilt das Cutover als veröffentlicht.

## Verifikation ausführen

```bash
node scripts/check_easyname_authoritative_dns.js \
  --host api.dev.georanking.ch \
  --zone georanking.ch \
  --expect-cname swisstopo-dev-vpc-alb-989918850.eu-central-1.elb.amazonaws.com \
  > reports/evidence/issue-904-authoritative-dns-check-$(date -u +%Y%m%dT%H%M%SZ).json
```

### Erfolgskriterium

Der Command muss mit Exit-Code `0` enden und im JSON enthalten sein:

- `consistency.same_cname_on_all_authoritative_ns: true`
- `consistency.expected_cname_matches: true` (wenn `--expect-cname` gesetzt ist)

## Post-Cutover-Smoke

Nach erfolgreicher autoritativer DNS-Verifikation:

```bash
curl -fsS https://api.dev.georanking.ch/health
```

Optional ergänzend (OIDC-Flow):

- `POST /analyze`
- `GET /analyze/history`

## Artefakte

- Script: `scripts/check_easyname_authoritative_dns.js`
- Evidence JSON: `reports/evidence/issue-904-authoritative-dns-check-*.json`
- Referenz-Cutover-Smoke: `reports/evidence/issue-897-dns-cutover-verify-20260303T132759Z.{json,md}`
