# Dev Dashboard (5xx + p95)

Dieses Dokument definiert ein minimales Dev-Dashboard für schnelle Triage.

## Zielbild

- **Kernmetrik 1:** `5xx-Rate` (CloudWatch Metric Math)
- **Kernmetrik 2:** `p95-Latenz` (ALB `TargetResponseTime`, Stat `p95`)
- **Einheitliche Zeitfenster:** `15m` und `1h`
- **Oncall-Startwerte:** Warn/Kritisch für beide Metriken

## Dashboard-Definition (Export)

Die Dashboard-JSON liegt im Repo unter:

- [`docs/observability/dev-dashboard-cloudwatch.json`](dev-dashboard-cloudwatch.json)

> Die Datei nutzt Platzhalter für ALB/TargetGroup-Dimensionen (`${LOAD_BALANCER_DIMENSION}`, `${TARGET_GROUP_DIMENSION}`), damit sie reproduzierbar zwischen Accounts/Environments einsetzbar ist.

## Eindeutige Query-Definitionen

### 1) 5xx-Rate (%)

Metriken im Namespace `swisstopo/dev-api`:

- `Http5xxCount` (ID `m5`)
- `HttpRequestCount` (ID `mt`)

Metric-Math-Ausdruck:

```text
IF(mt>=20,(m5/mt)*100,0)
```

Interpretation: erst ab 20 Requests/5m eine Rate berechnen, sonst 0 (Rauschen vermeiden).

### 2) p95-Latenz

CloudWatch-Query:

- Namespace: `AWS/ApplicationELB`
- Metric: `TargetResponseTime`
- Dimensions: `LoadBalancer=<...>`, `TargetGroup=<...>`
- Stat: `p95`
- Period: `60s`

## Zeitfenster / Filter

Für beide Charts dieselben Presets verwenden:

- **Kurzfenster:** `15m` (`-PT15M`)
- **Triage-Fenster:** `1h` (`-PT1H`)

## Oncall-/Triage-Startwerte

- **5xx-Rate:**
  - Warnung ab `>= 2%`
  - Kritisch ab `>= 5%`
- **p95-Latenz:**
  - Warnung ab `>= 1.2s`
  - Kritisch ab `>= 2.5s`

## Abrufbar machen (AWS CLI)

```bash
export AWS_REGION=eu-central-1
export DASHBOARD_NAME=swisstopo-dev-api-overview
export LB_NAME=swisstopo-dev-vpc-alb
export TG_NAME=swisstopo-dev-vpc-api-tg

LB_DIM=$(aws elbv2 describe-load-balancers \
  --region "$AWS_REGION" \
  --names "$LB_NAME" \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text | cut -d: -f6)

TG_DIM=$(aws elbv2 describe-target-groups \
  --region "$AWS_REGION" \
  --names "$TG_NAME" \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text | cut -d: -f6)

sed \
  -e "s|\${LOAD_BALANCER_DIMENSION}|$LB_DIM|g" \
  -e "s|\${TARGET_GROUP_DIMENSION}|$TG_DIM|g" \
  docs/observability/dev-dashboard-cloudwatch.json > /tmp/dev-dashboard-resolved.json

aws cloudwatch put-dashboard \
  --region "$AWS_REGION" \
  --dashboard-name "$DASHBOARD_NAME" \
  --dashboard-body "$(cat /tmp/dev-dashboard-resolved.json)"

aws cloudwatch get-dashboard \
  --region "$AWS_REGION" \
  --dashboard-name "$DASHBOARD_NAME" \
  --query 'DashboardName' --output text
```

Console-Link (Beispiel):

```text
https://eu-central-1.console.aws.amazon.com/cloudwatch/home?region=eu-central-1#dashboards:name=swisstopo-dev-api-overview
```
