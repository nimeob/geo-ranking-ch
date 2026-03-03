# Issue #897 DNS Cutover Verification

- Timestamp (UTC): `20260303T132759Z`
- Host `api.dev.georanking.ch` resolves to: `35.156.158.122, 63.182.86.48`
- ALB `swisstopo-dev-vpc-alb` (`swisstopo-dev-vpc-alb-989918850.eu-central-1.elb.amazonaws.com`) resolves to: `35.156.158.122, 63.182.86.48`
- DNS cutover proof (IP intersection non-empty): `True` (`35.156.158.122, 63.182.86.48`)
- Smoke `/health`: HTTP `200`
- Smoke `POST /analyze` (OIDC token): HTTP `200`
- Smoke `GET /analyze/history` (OIDC token): HTTP `200`, total `0`
- Egress indicator `geoadmin_search.successes`: `1`
- Rollback references: #895 closeout notes + prior #897 status note

JSON artifact: `issue-897-dns-cutover-verify-20260303T132759Z.json`
