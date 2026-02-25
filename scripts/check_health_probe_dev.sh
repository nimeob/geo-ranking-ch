#!/usr/bin/env bash
# check_health_probe_dev.sh
# Read-only Status-Check für die HTTP Uptime Probe (swisstopo-dev).
#
# Exit Codes:
#   0  — Probe voll operativ, Alarm im OK-Zustand
#   10 — Probe läuft, aber mit Warnungen (Alarm INSUFFICIENT_DATA, fehlende Metrikpunkte)
#   20 — Kritische Teile fehlen oder Alarm im ALARM-Zustand

set -euo pipefail

AWS_REGION="${AWS_REGION:-eu-central-1}"
ECS_SERVICE="${ECS_SERVICE:-swisstopo-dev-api}"
METRIC_NS="${METRIC_NS:-swisstopo/dev-api}"
LAMBDA_NAME="swisstopo-dev-health-probe"
RULE_NAME="swisstopo-dev-health-probe-schedule"
ALARM_NAME="swisstopo-dev-api-health-probe-fail"

WARNINGS=0
ERRORS=0

warn()  { echo "⚠️  WARN: $*"; WARNINGS=$((WARNINGS + 1)); }
error() { echo "❌ FAIL: $*"; ERRORS=$((ERRORS + 1)); }
ok()    { echo "✅ OK:   $*"; }

echo "== Health Probe Status Check (dev) =="
echo "Region: ${AWS_REGION}  |  Lambda: ${LAMBDA_NAME}"
echo

# 1. Lambda-Status
echo "── Lambda ──────────────────────────────────────────"
LAMBDA_STATE=$(aws lambda get-function-configuration \
  --region "$AWS_REGION" \
  --function-name "$LAMBDA_NAME" \
  --query 'State' \
  --output text 2>/dev/null || echo "NOT_FOUND")

if [[ "$LAMBDA_STATE" == "Active" ]]; then
  ok "Lambda '${LAMBDA_NAME}' Status = Active"
elif [[ "$LAMBDA_STATE" == "NOT_FOUND" ]]; then
  error "Lambda '${LAMBDA_NAME}' nicht gefunden — Setup ausführen"
else
  warn "Lambda Status = ${LAMBDA_STATE}"
fi

# 2. EventBridge Rule
echo
echo "── EventBridge Rule ────────────────────────────────"
RULE_STATE=$(aws events describe-rule \
  --region "$AWS_REGION" \
  --name "$RULE_NAME" \
  --query 'State' \
  --output text 2>/dev/null || echo "NOT_FOUND")

if [[ "$RULE_STATE" == "ENABLED" ]]; then
  ok "EventBridge Rule '${RULE_NAME}' = ENABLED"
elif [[ "$RULE_STATE" == "NOT_FOUND" ]]; then
  error "EventBridge Rule '${RULE_NAME}' nicht gefunden"
else
  warn "EventBridge Rule State = ${RULE_STATE}"
fi

# 3. Letzter Lambda-Invoke (via CloudWatch Logs)
echo
echo "── Letzter Lambda-Aufruf ───────────────────────────"
LAST_INVOKE=$(aws cloudwatch get-metric-statistics \
  --region "$AWS_REGION" \
  --namespace "AWS/Lambda" \
  --metric-name "Invocations" \
  --dimensions Name=FunctionName,Value="$LAMBDA_NAME" \
  --start-time "$(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-30M +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --period 1800 \
  --statistics Sum \
  --query 'Datapoints[0].Sum' \
  --output text 2>/dev/null || echo "None")

if [[ "$LAST_INVOKE" != "None" && "$LAST_INVOKE" != "0.0" ]]; then
  ok "Lambda Invocations in letzten 30 Min = ${LAST_INVOKE}"
else
  warn "Keine Lambda-Invocations in letzten 30 Min (noch nicht getriggert oder Regel deaktiviert)"
fi

# 4. HealthProbeSuccess Metrik (letzte 30 Min)
echo
echo "── HealthProbeSuccess Metrik ───────────────────────"
METRIC_VAL=$(aws cloudwatch get-metric-statistics \
  --region "$AWS_REGION" \
  --namespace "$METRIC_NS" \
  --metric-name "HealthProbeSuccess" \
  --dimensions Name=Service,Value="$ECS_SERVICE" Name=Environment,Value=dev \
  --start-time "$(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-30M +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --period 1800 \
  --statistics Minimum \
  --query 'sort_by(Datapoints, &Timestamp)[-1].Minimum' \
  --output text 2>/dev/null || echo "None")

if [[ "$METRIC_VAL" == "1.0" ]]; then
  ok "HealthProbeSuccess = 1 (Probe läuft, Endpoint healthy)"
elif [[ "$METRIC_VAL" == "0.0" ]]; then
  error "HealthProbeSuccess = 0 — /health nicht erreichbar!"
elif [[ "$METRIC_VAL" == "None" ]]; then
  warn "Kein Metrikdatenpunkt in letzten 30 Min (noch kein vollständiger Zyklus?)"
fi

# 5. Alarm-Status
echo
echo "── CloudWatch Alarm ────────────────────────────────"
ALARM_STATE=$(aws cloudwatch describe-alarms \
  --region "$AWS_REGION" \
  --alarm-names "$ALARM_NAME" \
  --query 'MetricAlarms[0].StateValue' \
  --output text 2>/dev/null || echo "NOT_FOUND")

if [[ "$ALARM_STATE" == "OK" ]]; then
  ok "Alarm '${ALARM_NAME}' = OK"
elif [[ "$ALARM_STATE" == "ALARM" ]]; then
  error "Alarm '${ALARM_NAME}' = ALARM — Probe fehlgeschlagen!"
elif [[ "$ALARM_STATE" == "INSUFFICIENT_DATA" ]]; then
  warn "Alarm '${ALARM_NAME}' = INSUFFICIENT_DATA (noch kein Datenpunkt)"
elif [[ "$ALARM_STATE" == "NOT_FOUND" ]]; then
  error "Alarm '${ALARM_NAME}' nicht gefunden"
fi

# ── Zusammenfassung ──────────────────────────────────────────────────────────
echo
echo "────────────────────────────────────────────────────"
if [[ $ERRORS -gt 0 ]]; then
  echo "Ergebnis: ❌ KRITISCH ($ERRORS Fehler, $WARNINGS Warnungen)"
  exit 20
elif [[ $WARNINGS -gt 0 ]]; then
  echo "Ergebnis: ⚠️  WARNUNG ($WARNINGS Warnungen)"
  exit 10
else
  echo "Ergebnis: ✅ Alles operativ"
  exit 0
fi
