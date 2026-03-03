# Dev Network NAT Rollout Runbook

**Issue:** [#885](https://github.com/nimeob/geo-ranking-ch/issues/885)
**Parent:** [#882](https://github.com/nimeob/geo-ranking-ch/issues/882)
**Stand:** 2026-03-03

---

## Ziel

Sicherer Operator-Flow für NAT-Egress-Rollout in `dev`:

- Import bereits vorhandener Ressourcen (falls vorhanden)
- Terraform Plan/Apply mit klaren Abbruchkriterien
- Post-Checks für Routing/Egress
- Rollback-Hinweise

> Dieses Runbook führt **keinen** Apply automatisch aus. Es beschreibt den manuellen Operator-Prozess.

---

## Preflight

```bash
export AWS_REGION="eu-central-1"
export TF_DIR="infra/terraform"

aws sts get-caller-identity
terraform -chdir="${TF_DIR}" init
terraform -chdir="${TF_DIR}" validate
```

Vorbereitung `terraform.dev.tfvars`:

```hcl
environment             = "dev"
manage_dev_network      = true
manage_dev_ingress      = true
manage_dev_nat_gateway  = true
```

---

## Import-Pfad (wenn Ressourcen bereits existieren)

Nur ausführen, wenn NAT/EIP/RouteTable schon manuell existieren.

```bash
# IDs aus AWS ermitteln
aws ec2 describe-nat-gateways --region "${AWS_REGION}"
aws ec2 describe-addresses --region "${AWS_REGION}"
aws ec2 describe-route-tables --region "${AWS_REGION}"

# Beispiel-Imports (IDs anpassen)
terraform -chdir="${TF_DIR}" import aws_eip.dev_nat[0] eipalloc-xxxxxxxx
terraform -chdir="${TF_DIR}" import aws_nat_gateway.dev[0] nat-xxxxxxxx
terraform -chdir="${TF_DIR}" import aws_route_table.dev_private[0] rtb-xxxxxxxx
terraform -chdir="${TF_DIR}" import aws_route_table_association.dev_private[0] rtbassoc-xxxxxxxx
terraform -chdir="${TF_DIR}" import aws_route_table_association.dev_private[1] rtbassoc-yyyyyyyy
```

---

## Plan

```bash
terraform -chdir="${TF_DIR}" plan \
  -var-file="terraform.dev.tfvars" \
  -out="dev-nat.tfplan"
```

### Abbruchkriterien

Apply **nicht** ausführen, wenn:

- unerwartete Deletes/Replace bei bestehenden Kernressourcen erscheinen
- Route-Änderungen nicht nur private Subnets betreffen
- SG-/VPC-Änderungen außerhalb des NAT-Scope auftauchen

---

## Apply

```bash
terraform -chdir="${TF_DIR}" apply "dev-nat.tfplan"
```

Danach warten bis NAT verfügbar:

```bash
aws ec2 describe-nat-gateways \
  --region "${AWS_REGION}" \
  --filter Name=state,Values=available
```

---

## Post-Checks

### Routing

```bash
aws ec2 describe-route-tables \
  --region "${AWS_REGION}" \
  --filters Name=tag:Name,Values='swisstopo-dev-private-rt' \
  --query 'RouteTables[].Routes'
# Erwartung: 0.0.0.0/0 via nat-*
```

### Subnet-Assoziationen

```bash
aws ec2 describe-route-tables \
  --region "${AWS_REGION}" \
  --filters Name=tag:Name,Values='swisstopo-dev-private-rt' \
  --query 'RouteTables[].Associations[].SubnetId'
# Erwartung: private dev subnets sind assoziiert
```

### Terraform Outputs

```bash
terraform -chdir="${TF_DIR}" output dev_nat_gateway_id
terraform -chdir="${TF_DIR}" output dev_private_route_table_id
```

---

## Rollback / Safety

- Kein Force-Apply ohne frischen Plan.
- Bei Fehlkonfiguration zuerst RouteTable-Assoziationen prüfen, danach NAT.
- Destroy in Produktionsnähe vermeiden; in dev nur mit dokumentierter Freigabe.

Gezielter Rückbau nur mit bestätigtem Plan:

```bash
terraform -chdir="${TF_DIR}" plan -destroy -var-file="terraform.dev.tfvars"
```

---

## Evidence-Vorlage

Nach Operator-Lauf Evidence in `reports/evidence/` ablegen mit:

- verwendeter Plan-Datei / Plan-Zusammenfassung
- NAT ID, EIP Allocation ID, private RT ID
- Routing-/Association-Checks
- Abweichungen / manuelle Schritte
