# BL-16.wp1 — AWS-Webhook-Gate Runbook (Hostinger) · Issue #549

> **Archiviert / nicht mehr Zielbild (seit 2026-03-01):** Externer Inbound auf OpenClaw wird aus Security-Gründen nicht betrieben. Dieses Dokument bleibt nur als historischer Referenzstand.

Parent-Issue: [#1](https://github.com/nimeob/geo-ranking-ch/issues/1)  
Follow-up (externes Rollout): [#550](https://github.com/nimeob/geo-ranking-ch/issues/550)

## Ziel

Dieses Runbook liefert den **repo-lokalen** Standard für einen vorgeschalteten NGINX-Webhook-Gate vor OpenClaw.
Damit kann ein AWS-Alarm-POST auf einen gehärteten Endpunkt (`/aws-alarm`) zugestellt werden, ohne OpenClaw direkt öffentlich zu exponieren.

**Scope-Klarstellung:** Der Webhook-Gate ist eine optionale Zusatzkomponente (Alarm-Inbound zu OpenClaw), **kein** Pflichtbaustein für die Kernverfügbarkeit des Projekts.

## Artefakte im Repo

- NGINX-Template: `infra/webhook_gate/nginx.aws-alarm.conf.template`
- Compose-Template: `infra/webhook_gate/docker-compose.webhook-gate.template.yml`
- Verify-Script: `scripts/check_webhook_gate_templates.py`

## Sicherheitsprinzipien

1. OpenClaw bleibt intern (`expose`, keine direkten öffentlichen Ports).
2. Öffentlich erreichbar ist nur der Webhook-Gate auf `443`.
3. Zugriff auf `/aws-alarm` wird über
   - IP-Allowlist und
   - `X-Alarm-Token`
   eingeschränkt.
4. Keine Secrets im Repo, in Commits oder Logs.

## Schritt 1 — Templates kopieren

Beispiel für einen Hostinger-Deploy-Ordner:

```bash
mkdir -p /opt/openclaw-webhook-gate
cp infra/webhook_gate/nginx.aws-alarm.conf.template /opt/openclaw-webhook-gate/nginx.aws-alarm.conf
cp infra/webhook_gate/docker-compose.webhook-gate.template.yml /opt/openclaw-webhook-gate/docker-compose.yml
```

## Schritt 2 — Platzhalter ersetzen

Ersetze in `nginx.aws-alarm.conf` die Platzhalter:

- `__ALLOWLIST_RULES__` (z. B. `allow 18.194.123.45;` je Zeile)
- `__ALARM_TOKEN__` (langes zufälliges Secret)
- `__UPSTREAM_HOST__` (typisch: `openclaw`)
- `__UPSTREAM_PORT__` (typisch: `8080`)
- `__TLS_CERT_PATH__`, `__TLS_KEY_PATH__` (Container-Pfade)

Ersetze in `docker-compose.yml` mindestens:

- `__OPENCLAW_IMAGE__`
- `__OPENCLAW_PORT__`

## Schritt 3 — Repo-lokale Verifikation ausführen

```bash
python3 scripts/check_webhook_gate_templates.py --repo-root . --render-example
```

Der Check schlägt fail-closed fehl, wenn Pflicht-Platzhalter oder Guardrails fehlen.

## Schritt 4 — Deploy/Reload am Zielhost

```bash
docker compose -f /opt/openclaw-webhook-gate/docker-compose.yml up -d
```

## Schritt 5 — Smoke-Tests

1. Valid token + allowlisted Source → `2xx`
2. Falscher Token → `403`
3. Nicht allowlisted Source → geblockt
4. CloudWatch-Alarmfluss `OK -> ALARM -> OK` verifizieren

## Hinweise zu Scope-Grenzen

Dieses Dokument deckt die **vorbereitenden, repo-lokalen Deliverables** ab.  
Das produktive externe Rollout (Hostinger-Zugang, echte Egress-IP(s), E2E-Evidenz) wird separat in [#550](https://github.com/nimeob/geo-ranking-ch/issues/550) abgeschlossen.
