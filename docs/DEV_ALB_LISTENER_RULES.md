# DEV ALB Listener Rules — Source of Truth

## Ziel

Verhindern, dass auf dem DEV-ALB (`swisstopo-dev-vpc-alb`) veraltete Redirect-Regeln für
`/login` oder `/signin` auf den UI-Hosts wieder auftauchen (Incident #1360).

## Autoritative Quelle

Die **verbindliche Runtime-Quelle** ist:

1. `scripts/reconcile_dev_alb_listener_rules.py`
2. Step **"Reconcile DEV ALB listener login-entry rules"** in `.github/workflows/deploy.yml`

Damit wird Drift pro Deploy-Lauf erkannt und (gezielt) bereinigt.

> Hinweis zu CI-Least-Privilege: Wenn die GitHub-Deploy-Role aktuell keine `elasticloadbalancing:*Rule*`-Rechte hat,
> liefert das Script `overall.reason=aws_access_denied` (Exit-Code 3). Der Workflow warnt dann explizit und läuft weiter;
> der nachfolgende Login-Smoke-Test bleibt weiterhin ein hartes Gate.

### CI-Remediation bei `aws_access_denied`

Wenn im Deploy-Lauf die Warnung `DEV ALB reconcile skipped (AWS access denied for deploy role)` auftaucht,
ist meist die AWS-IAM-Policy an der Role `swisstopo-dev-github-deploy-role` veraltet oder nicht korrekt attached.

Schneller Fix (mit Admin-Rechten in AWS-Account `523234426229`):

```bash
# 1) Policy aus Repo als neue Default-Version setzen
aws iam create-policy-version \
  --policy-arn arn:aws:iam::523234426229:policy/swisstopo-dev-github-deploy-policy \
  --policy-document file://infra/iam/deploy-policy.json \
  --set-as-default

# 2) Sicherstellen, dass die Deploy-Role die Policy wirklich attached hat
aws iam attach-role-policy \
  --role-name swisstopo-dev-github-deploy-role \
  --policy-arn arn:aws:iam::523234426229:policy/swisstopo-dev-github-deploy-policy
```

Danach sollte der Reconcile-Step wieder ohne Skip laufen (kein Exit-Code 3).
Relevant sind mindestens: `elasticloadbalancing:DescribeLoadBalancers`, `DescribeListeners`, `DescribeRules`, `DeleteRule`.

## Listener-Intent (DEV)

Für beide Listener-Ports `80` und `443` gilt:

- UI-Hosts
  - `www.dev.georanking.ch`
  - `www.dev.geo-ranking.ch`
- müssen über Host-Header-Regeln auf die UI-Target-Group weiterleiten
  (`swisstopo-dev-vpc-ui-tg`).
- Es dürfen **keine** UI-Host-Regeln existieren, die
  - `path-pattern` `/login`/`/signin` (inkl. `*`) matchen und
  - per Redirect nach `/auth/login` umleiten.

## Reconcile / Check lokal

Read-only Check (failt bei Drift):

```bash
python3 scripts/reconcile_dev_alb_listener_rules.py \
  --lb-name swisstopo-dev-vpc-alb \
  --region eu-central-1 \
  --output-json artifacts/dev-alb-listener-reconcile.json
```

Aktive Bereinigung (löscht nur erkannte stale Redirect-Regeln):

```bash
python3 scripts/reconcile_dev_alb_listener_rules.py \
  --lb-name swisstopo-dev-vpc-alb \
  --region eu-central-1 \
  --apply \
  --output-json artifacts/dev-alb-listener-reconcile.json
```

## Safety

Das Script ist absichtlich eng begrenzt:

- löscht nur nicht-default Regeln,
- nur bei UI-Hosts,
- nur bei Login/Signin-Path-Match + Redirect-Ziel `/auth/login`,
- und verweigert Mutation, wenn für einen Pflicht-Listener keine UI-Forward-Regel vorhanden ist.

So bleibt die gewünschte UI-Weiterleitung erhalten, während die alte Redirect-Drift nicht zurückkehrt.
