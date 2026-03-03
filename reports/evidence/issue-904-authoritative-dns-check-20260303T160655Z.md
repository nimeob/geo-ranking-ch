# Issue #904 — Authoritative DNS Publish Verification

- Timestamp (UTC): `2026-03-03T16:06:55Z`
- Host: `api.dev.georanking.ch`
- Erwartetes Target-CNAME: `swisstopo-dev-vpc-alb-989918850.eu-central-1.elb.amazonaws.com`

## Autoritative NS-Prüfung (Easyname)

Verifiziert mit `scripts/check_easyname_authoritative_dns.js` gegen beide Easyname-Nameserver:

- `ns1.easyname.eu` (`77.244.243.4`) → CNAME stimmt auf erwartetes ALB-Target
- `ns2.easyname.eu` (`77.244.244.138`) → CNAME stimmt auf erwartetes ALB-Target
- Konsistenz: `same_cname_on_all_authoritative_ns = true`
- Erwartungs-Match: `expected_cname_matches = true`

SOA-Sicht (beide NS):

- Serial: `2026030302`
- Primary NS: `ns1.easyname.eu`

## Post-Cutover Smoke

```bash
curl -sS -o /tmp/issue904_health_body.txt -w "%{http_code}" https://api.dev.georanking.ch/health
```

Ergebnis:

- HTTP: `200`
- Body: `{"ok": true, "service": "geo-ranking-ch", ...}`

## Schlussfolgerung

Der autoritative Publish-Stand für `api.dev.georanking.ch` ist auf beiden Easyname-NS konsistent. Damit ist der Blocker aus #904 aufgelöst; #899 ist für den dokumentierten Cutover-/Closeout-Pfad entblockt.

JSON-Artefakt: `reports/evidence/issue-904-authoritative-dns-check-20260303T160655Z.json`
