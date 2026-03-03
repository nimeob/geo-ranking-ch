# Issue #886 Runtime Validation Evidence

- Timestamp (UTC): `20260303T132531Z`
- ECS `swisstopo-dev-api`: `assignPublicIp=DISABLED`, subnets `subnet-04d5ddec3c5b06d7a, subnet-0cd8553a1fedbf183`
- NAT available: `nat-01c348d29cf09e2f1`
- Private route table `rtb-0a1fdbf9c13782310` has default route via NAT
- Egress proof: `POST /analyze` HTTP `200` with `geoadmin_search.successes=1`
- Inbound hardening: world-open ingress rules on app port 8080 = `0`

JSON artifact: `issue-886-runtime-validation-20260303T132531Z.json`
