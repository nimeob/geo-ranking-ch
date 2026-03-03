# Dev Frontdoor Outage Root-Cause (Issue #908)

## Scope
Forensische Ist-Aufnahme für den DNS-Cutover-Ausfall aus #907 (HTTPS Timeout / HTTP 503) auf dem neuen ALB `swisstopo-dev-vpc-alb`.

## Reproduzierbare Evidence

```bash
python3 scripts/check_dev_frontdoor_outage.py \
  --lb-name swisstopo-dev-vpc-alb \
  --region eu-central-1 \
  --output-json reports/evidence/issue-908-frontdoor-outage-audit-2026-03-03.json
```

Artefakt:
- `reports/evidence/issue-908-frontdoor-outage-audit-2026-03-03.json`

Der Audit enthält jetzt:
- ALB Listener/Rules/Target-Health
- zugehörige Security Groups
- zugehörige Subnetze + Network ACLs (Ingress/Egress-Heuristik)
- externe Host-Probes (DNS-basiert)
- ALB-direkte Probes mit Host-Header (routing-intern, DNS-unabhängig)

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

5. **SG/NACL-Sicht für Ingress/Backend-Pfade dokumentiert**
   - SG-Layer: TCP/443-Ingress-Check enthalten
   - NACL-Layer: zugehörige ACL-Entries pro ALB-Subnetz im Report enthalten
   - Ergebnis ist im Artefakt unter `analysis.derived.network_acls` nachvollziehbar

## Probe-Evidenz

Aus dem JSON-Report:
- Extern (DNS):
  - `https://api.dev.georanking.ch/health` → Timeout
  - `https://api.dev.geo-ranking.ch/health` → Timeout
  - `https://www.dev.georanking.ch/` → Timeout
  - `https://www.dev.geo-ranking.ch/` → Timeout
  - HTTP auf allen vier Hosts → `503`
- ALB-direkt (Host-Header auf ALB-DNS):
  - zeigt denselben fehlenden Frontdoor-Pfad unabhängig vom DNS-Cutover

## Minimaler Fix-Plan für #912

1. HTTPS-Listener `:443` auf `swisstopo-dev-vpc-alb` anlegen und ACM-Zertifikat mit SANs für alle 4 Hostnamen binden.
2. Host-Header-Rules für API/UI auf beiden Domains anlegen (`api.*` → API-TG, `www.*` → UI-TG).
3. Laufende ECS-Targets an API/UI-TGs registrieren (inkl. stabiler Service-Attachments) und Health-Checks verifizieren.
4. Nach dem Fix extern + ALB-direkt erneut prüfen (gleiches Script), um DNS und Frontdoor getrennt zu validieren.

## Ergebnis
Issue #908 liefert reproduzierbare Root-Cause-Evidence + konkreten, direkt umsetzbaren Fix-Plan für das nächste Leaf-Work-Package #912.
