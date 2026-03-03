# Issue #922 — Dev frontdoor UI host routing fix

Timestamp (UTC): 2026-03-03

## Context

`#913` was blocked because UI domains returned `404` from API handler (`{"ok": false, "error": "not_found"}`) while API health was already green.

## Applied changes

1. **Created UI target group in dev VPC**
   - Name: `swisstopo-dev-vpc-ui-tg`
   - VPC: `vpc-013b6dfa58c5a2009`
   - Type/Port: `ip` / `8080`
   - Health check: `GET /healthz` (`200-399`)

2. **Added explicit host-header rules on dev VPC ALB**
   - ALB: `swisstopo-dev-vpc-alb`
   - Listener rules (ports `80` + `443`):
     - `api.dev.georanking.ch`, `api.dev.geo-ranking.ch` → `swisstopo-dev-vpc-api-tg`
     - `www.dev.georanking.ch`, `www.dev.geo-ranking.ch` → `swisstopo-dev-vpc-ui-tg`

3. **Moved `swisstopo-dev-ui` service onto dev-VPC/private wiring**
   - ECS service now registers against `swisstopo-dev-vpc-ui-tg`
   - Network config:
     - subnets: `subnet-0cd8553a1fedbf183`, `subnet-04d5ddec3c5b06d7a`
     - security group: `sg-02d1c720c9b0adc7b`
     - `assignPublicIp=DISABLED`
   - Deployment completed (`services-stable`)

## Validation

External 4-host smoke (post-fix):

- `https://api.dev.georanking.ch/health` → `200`
- `https://api.dev.geo-ranking.ch/health` → `200`
- `https://www.dev.georanking.ch/` → `200`
- `https://www.dev.geo-ranking.ch/` → `200`

Additional runtime audit:

- `scripts/check_dev_frontdoor_outage.py` postcheck is `analysis.overall=pass`, no findings.

## Evidence artifacts

- `reports/evidence/issue-922-frontdoor-routing-precheck-20260303T122759Z.json`
- `reports/evidence/issue-922-frontdoor-routing-postcheck-20260303T123442Z.json`
- `reports/evidence/issue-922-frontdoor-ui-routing-fix-2026-03-03.json`
