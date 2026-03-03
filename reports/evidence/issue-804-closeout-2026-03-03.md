# Issue #804 Closeout Evidence (2026-03-03)

## 1) RDS instance available
```bash
aws rds describe-db-instances --region eu-central-1 --query "DBInstances[?DBInstanceIdentifier=='swisstopo-dev-postgres'].[DBInstanceIdentifier,DBInstanceStatus,Endpoint.Address,Endpoint.Port]" --output table
```
-----------------------------------------------------------------------------------------------------------------------
|                                                 DescribeDBInstances                                                 |
+------------------------+------------+----------------------------------------------------------------------+--------+
|  swisstopo-dev-postgres|  available |  swisstopo-dev-postgres.cvmswyum0dv5.eu-central-1.rds.amazonaws.com  |  5432  |
+------------------------+------------+----------------------------------------------------------------------+--------+

## 2) ECS service steady-state (DB-connected runtime active)
```bash
aws ecs describe-services --cluster swisstopo-dev --services swisstopo-dev-api --region eu-central-1 --query "services[0].{desired:desiredCount,running:runningCount,status:status,taskDefinition:taskDefinition}" --output json
```
{
    "desired": 1,
    "running": 1,
    "status": "ACTIVE",
    "taskDefinition": "arn:aws:ecs:eu-central-1:523234426229:task-definition/swisstopo-dev-api:172"
}

## 3) DB secret wiring in ECS task definition
```bash
aws ecs describe-task-definition --task-definition swisstopo-dev-api --region eu-central-1 --query "taskDefinition.containerDefinitions[0].{db_env:[environment[?starts_with(name, 'DB_')].{name:name,value:value}][],db_secret:secrets[?name=='DB_PASSWORD']|[0]}" --output json
```
{
    "db_env": [
        {
            "name": "DB_PORT",
            "value": "5432"
        },
        {
            "name": "DB_NAME",
            "value": "swisstopo"
        },
        {
            "name": "DB_HOST",
            "value": "swisstopo-dev-postgres.cvmswyum0dv5.eu-central-1.rds.amazonaws.com"
        },
        {
            "name": "DB_USERNAME",
            "value": "swisstopo"
        }
    ],
    "db_secret": {
        "name": "DB_PASSWORD",
        "valueFrom": "arn:aws:secretsmanager:eu-central-1:523234426229:secret:rds!db-0908ae83-3297-4241-80ea-74612982710f-0Mpayw:password::"
    }
}

## 4) Runtime history endpoint hits DB successfully
```bash
curl -ksS https://api.dev.georanking.ch/analyze/history
```
{
  "ok": true,
  "sample_count": 4,
  "first_result_id": "f91f6eca-affd-45da-b046-22951e5b9608"
}
