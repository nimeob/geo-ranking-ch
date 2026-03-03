# Dev Frontdoor Outage Root-Cause (Issue #911)

## Scope
Forensische Ist-Aufnahme für den DNS-Cutover-Ausfall aus #907 (HTTPS Timeout / HTTP 503) auf dem neuen ALB `swisstopo-dev-vpc-alb`.

## Reproduzierbare Evidence

```bash
python3 scripts/check_dev_frontdoor_outage.py \
  --lb-name swisstopo-dev-vpc-alb \
  --region eu-central-1 \
  --output-json reports/evidence/issue-911-frontdoor-outage-audit-2026-03-03.json
```

Artefakt:
- `reports/evidence/issue-911-frontdoor-outage-audit-2026-03-03.json`

## Befund (konkrete AWS-Ressourcen)

1. **Kein HTTPS-Listener (443) auf dem ALB**
   - Betroffene Resource: `arn:aws:elasticloadbalancing:eu-central-1:523234426229:listener/app/swisstopo-dev-vpc-alb/170e7b30dbb9cd7f/b7ffe241130b0613`
   - Ist-Zustand: nur Port `80` vorhanden
   - Auswirkung: externe HTTPS-Aufrufe laufen in Timeout

2. **Kein Host-basiertes Routing für die 4 erwarteten Hosts**
   - Fehlende Host-Rules:
     - `api.dev.georanking.ch`
     - `api.dev.geo-ranking.ch`
     - `www.dev.georanking.ch`
     - `www.dev.geo-ranking.ch`
   - Auswirkung: kein deterministisches API/UI-Routing je Hostname

3. **Keine gesunden Targets im einzigen Target Group Attachment**
   - Betroffene Resource: `swisstopo-dev-vpc-api-tg` (`.../targetgroup/swisstopo-dev-vpc-api-tg/0cd1b00f557f3a4b`)
   - Ist-Zustand: `0` registrierte/gesunde Targets
   - Auswirkung: HTTP-Pfad liefert extern `503`

4. **Nur ein Target Group vorhanden**
   - Ist-Zustand: nur API-TG, kein separater UI-TG im ALB
   - Auswirkung: UI-Hostpfad ist strukturell unvollständig

## Externe Probe-Evidenz

Aus dem JSON-Report:
- HTTPS:
  - `https://api.dev.georanking.ch/health` → Timeout
  - `https://api.dev.geo-ranking.ch/health` → Timeout
  - `https://www.dev.georanking.ch/` → Timeout
  - `https://www.dev.geo-ranking.ch/` → Timeout
- HTTP:
  - alle vier Hosts → `503`

## Minimaler Fix-Plan für #912

1. HTTPS-Listener `:443` auf `swisstopo-dev-vpc-alb` anlegen und ACM-Zertifikat mit SANs für alle 4 Hostnamen binden.
2. Host-Header-Rules für API/UI auf beiden Domains anlegen (`api.*` → API-TG, `www.*` → UI-TG).
3. Laufende ECS-Targets an API/UI-TGs registrieren (inkl. stabiler Service-Attachments) und Health-Checks verifizieren.

## Ergebnis
Issue #911 liefert reproduzierbare Root-Cause-Evidence + konkreten, direkt umsetzbaren Fix-Plan für das nächste Leaf-Work-Package #912.
