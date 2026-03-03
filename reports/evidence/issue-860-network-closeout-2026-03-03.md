# Issue #860 Closeout Evidence — Dev Network Terraform

Datum: 2026-03-03
Issue: https://github.com/nimeob/geo-ranking-ch/issues/860

## Änderungen

- `infra/terraform/outputs.tf`
  - neue Dev-Network-Outputs ergänzt:
    - `dev_vpc_id`
    - `dev_public_subnet_ids`
    - `dev_private_subnet_ids`
    - `dev_alb_security_group_id`
    - `dev_alb_dns_name`
    - `dev_alb_zone_id`
    - `dev_alb_http_url`
    - `dev_db_security_group_id`
    - `dev_ecs_service_security_group_id`
- `tests/test_dev_network_outputs_tf.py`
  - Regressionstest für Dev-Network-Output-Marker in `outputs.tf`

## Verifikation (lokal)

```bash
pytest -q tests/test_dev_network_outputs_tf.py
# 1 passed

terraform -chdir=infra/terraform validate
# Success! The configuration is valid.

terraform -chdir=infra/terraform plan \
  -var-file=terraform.dev.tfvars.example \
  -var='manage_dev_network=true' \
  -var='manage_dev_ingress=true' \
  -lock=false -refresh=false
# Plan: 12 to add, 0 to change, 0 to destroy.
# Output-Preview enthält dev_vpc_id/dev_public_subnet_ids/dev_private_subnet_ids/... 
```

## Read-only AWS Inventar-Nachweis (bereits provisionierte Dev-Network-Basis)

```bash
aws ec2 describe-vpcs --region eu-central-1 \
  --filters Name=tag:Name,Values='swisstopo-dev-vpc'
# vpc-013b6dfa58c5a2009 (10.80.0.0/16, available)

aws ec2 describe-subnets --region eu-central-1 \
  --filters Name=tag:Name,Values='swisstopo-dev-public-*','swisstopo-dev-private-*'
# public: subnet-0e872f671de1cd4ec (10.80.0.0/24), subnet-0e059126fa780f4c7 (10.80.1.0/24)
# private: subnet-0cd8553a1fedbf183 (10.80.10.0/24), subnet-04d5ddec3c5b06d7a (10.80.11.0/24)

aws ec2 describe-route-tables --region eu-central-1 \
  --filters Name=vpc-id,Values=vpc-013b6dfa58c5a2009
# public RT vorhanden: rtb-0347b0c65f8622118 mit 0.0.0.0/0 via IGW

aws ec2 describe-security-groups --region eu-central-1 \
  --filters Name=vpc-id,Values=vpc-013b6dfa58c5a2009 Name=group-name,Values='swisstopo-dev-*'
# db sg vorhanden: sg-08e775d778b9c551f (Ingress tcp/5432 aus 172.31.0.0/16)
```

## Follow-up

Striktes NAT-Egress-Ziel für private ECS-Subnets als eigener Folge-Task erfasst:
- https://github.com/nimeob/geo-ranking-ch/issues/882
