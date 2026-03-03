# Issue #896 — ECS private-subnet switch + SG/DB wiring (dev)

- Issue: https://github.com/nimeob/geo-ranking-ch/issues/896
- Timestamp (UTC): 2026-03-03T12:04:27Z
- Region/Cluster/Service: `eu-central-1` / `swisstopo-dev` / `swisstopo-dev-api`

## Summary

Worker A reran the WP2 rollout and moved `swisstopo-dev-api` to the dev private subnets with `assignPublicIp=DISABLED`.

During rollout, ECS initially remained unstable because the service was still attached to both target groups (legacy default-VPC TG + dev-VPC TG). This produced registration/health issues while moving tasks between VPCs. The service was then converged to the dev-VPC target group only, followed by a clean forced deployment.

## Actions executed

1. ECS network config updated:
   - subnets: `subnet-0cd8553a1fedbf183`, `subnet-04d5ddec3c5b06d7a`
   - security group: `sg-02d1c720c9b0adc7b`
   - `assignPublicIp=DISABLED`
2. Service load-balancer attachment normalized to dev-VPC TG only:
   - `arn:aws:elasticloadbalancing:eu-central-1:523234426229:targetgroup/swisstopo-dev-vpc-api-tg/0cd1b00f557f3a4b`
3. Forced new deployment and waited for stable state.
4. Runtime probes + logs sampled.

## Definition of Done mapping

- [x] ECS service uses private subnets (`subnet-0cd8553a1fedbf183`, `subnet-04d5ddec3c5b06d7a`)
- [x] `assignPublicIp=DISABLED`
- [x] Service stable (`rolloutState=COMPLETED`)
- [x] DB connectivity for new task is plausible/no startup timeout signal in log tail (`contains_db_timeout_or_operational_error=false`)

## Runtime evidence

Primary artifact:
- `reports/evidence/issue-896-ecs-private-subnet-rollout-2026-03-03.json`

Rollout checker artifact:
- `reports/evidence/issue-896-ecs-network-check-2026-03-03.json`

Key observed values:
- Deployment: `PRIMARY`, `rolloutState=COMPLETED`, `failedTasks=0`
- Running task subnet: `subnet-04d5ddec3c5b06d7a`
- Running task private IP: `10.80.11.190`
- Health probe: `GET https://api.dev.georanking.ch/health` → `200`
- Auth probe: `POST /analyze` without bearer token → `401` (expected under OIDC guard)

## Local validation added (code + tests)

Added script:
- `scripts/check_dev_ecs_network_rollout.py`

Added tests:
- `tests/test_check_dev_ecs_network_rollout.py`

Executed test command:
- `pytest -q tests/test_check_dev_ecs_network_rollout.py`
- Result: `2 passed`
