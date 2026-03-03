# Issue #912 — Minimal AWS frontdoor fix (API host recovery)

Timestamp (UTC): 2026-03-03T11:38Z

## Applied changes

1. **HTTPS listener on dev-vpc ALB**
   - Resource: `swisstopo-dev-vpc-alb`
   - Change: created listener `:443` with ACM cert `arn:aws:acm:eu-central-1:523234426229:certificate/9e7d8116-c6d7-4998-84fa-d5d80cf15059`
   - Default action: forward to `swisstopo-dev-vpc-api-tg`

2. **Ingress from frontdoor ALB SG to API tasks**
   - Target SG: `sg-092e0616ffb0663c3` (`swisstopo-dev-api-sg`)
   - Added rule: `tcp/8080` from `sg-02d1c720c9b0adc7b` (`swisstopo-dev-frontdoor-sg`) via peering `pcx-0ec189e6248290214`

3. **API ECS service dual-target registration**
   - Service: `swisstopo-dev-api`
   - Change: attached second target group `swisstopo-dev-vpc-api-tg` (in addition to existing `swisstopo-dev-api-tg`) and forced new deployment
   - Result: service reached steady state (`aws ecs wait services-stable`)

## Evidence

- JSON evidence bundle: `reports/evidence/issue-912-frontdoor-fix-2026-03-03.json`
- New TG health (post-change): at least one `healthy` target in `swisstopo-dev-vpc-api-tg`

External checks:

```bash
curl -sS -L --max-time 20 -o /tmp/api-dev-georanking-health.txt -w "%{http_code}" https://api.dev.georanking.ch/health
# 200

curl -sS -L --max-time 20 -o /tmp/api-dev-geo-ranking-health.txt -w "%{http_code}" https://api.dev.geo-ranking.ch/health
# 200
```
