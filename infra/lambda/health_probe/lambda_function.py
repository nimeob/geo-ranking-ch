"""HTTP Uptime Probe Lambda — swisstopo dev

Läuft auf EventBridge-Schedule (alle 5 Min).
Löst dynamisch die öffentliche IP des laufenden ECS-Tasks auf (kein ALB/Domain
nötig), prüft GET /health und publiziert eine CloudWatch-Metrik.

Metrik: swisstopo/dev-api  /  HealthProbeSuccess  (1 = ok, 0 = fail)
→ CloudWatch Alarm → SNS → Telegram

Umgebungsvariablen (werden im Setup-Script gesetzt):
  ECS_CLUSTER   swisstopo-dev
  ECS_SERVICE   swisstopo-dev-api
  HEALTH_PORT   8080
  HEALTH_PATH   /health
  METRIC_NS     swisstopo/dev-api
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

import boto3

log = logging.getLogger()
log.setLevel(logging.INFO)

ECS_CLUSTER = os.environ.get("ECS_CLUSTER", "swisstopo-dev")
ECS_SERVICE = os.environ.get("ECS_SERVICE", "swisstopo-dev-api")
HEALTH_PORT = int(os.environ.get("HEALTH_PORT", "8080"))
HEALTH_PATH = os.environ.get("HEALTH_PATH", "/health")
METRIC_NS = os.environ.get("METRIC_NS", "swisstopo/dev-api")
REGION = os.environ.get("AWS_REGION", "eu-central-1")

ecs = boto3.client("ecs", region_name=REGION)
ec2 = boto3.client("ec2", region_name=REGION)
cw = boto3.client("cloudwatch", region_name=REGION)


def _get_task_public_ip() -> str | None:
    """Liefert die öffentliche IPv4 des ersten laufenden Tasks, oder None."""
    resp = ecs.list_tasks(cluster=ECS_CLUSTER, serviceName=ECS_SERVICE, desiredStatus="RUNNING")
    task_arns = resp.get("taskArns", [])
    if not task_arns:
        log.warning("Kein laufender Task gefunden in %s/%s", ECS_CLUSTER, ECS_SERVICE)
        return None

    tasks = ecs.describe_tasks(cluster=ECS_CLUSTER, tasks=[task_arns[0]])["tasks"]
    if not tasks:
        log.warning("describe_tasks lieferte keine Daten")
        return None

    eni_id = None
    for attachment in tasks[0].get("attachments", []):
        if attachment.get("type") == "ElasticNetworkInterface":
            for detail in attachment.get("details", []):
                if detail.get("name") == "networkInterfaceId":
                    eni_id = detail["value"]
                    break

    if not eni_id:
        log.warning("Kein ENI an Task gefunden")
        return None

    eni = ec2.describe_network_interfaces(NetworkInterfaceIds=[eni_id])
    interfaces = eni.get("NetworkInterfaces", [])
    if not interfaces:
        return None

    public_ip = (
        interfaces[0].get("Association", {}).get("PublicIp")
    )
    return public_ip


def _probe_health(public_ip: str) -> tuple[bool, int | None, str]:
    """Führt GET /health aus. Gibt (success, status_code, message) zurück."""
    url = f"http://{public_ip}:{HEALTH_PORT}{HEALTH_PATH}"
    try:
        req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            body = resp.read(512).decode("utf-8", errors="replace")
            ok = status == 200
            log.info("Health probe %s → HTTP %d  body=%s", url, status, body[:200])
            return ok, status, body
    except urllib.error.HTTPError as e:
        log.error("Health probe %s → HTTPError %d", url, e.code)
        return False, e.code, str(e)
    except Exception as e:  # noqa: BLE001
        log.error("Health probe %s → Exception: %s", url, e)
        return False, None, str(e)


def _put_metric(success: bool) -> None:
    cw.put_metric_data(
        Namespace=METRIC_NS,
        MetricData=[
            {
                "MetricName": "HealthProbeSuccess",
                "Value": 1.0 if success else 0.0,
                "Unit": "Count",
                "Dimensions": [
                    {"Name": "Service", "Value": ECS_SERVICE},
                    {"Name": "Environment", "Value": "dev"},
                ],
            }
        ],
    )
    log.info("Metrik HealthProbeSuccess = %d publiziert", 1 if success else 0)


def lambda_handler(event: dict, context) -> dict:  # noqa: ANN001
    log.info("Health probe gestartet. Cluster=%s Service=%s", ECS_CLUSTER, ECS_SERVICE)

    public_ip = _get_task_public_ip()
    if not public_ip:
        log.error("Keine öffentliche IP ermittelbar — Probe schlägt fehl")
        _put_metric(False)
        return {"ok": False, "reason": "no_public_ip"}

    success, status_code, message = _probe_health(public_ip)
    _put_metric(success)

    result = {
        "ok": success,
        "public_ip": public_ip,
        "status_code": status_code,
        "message": message[:200],
    }
    log.info("Probe-Ergebnis: %s", json.dumps(result))
    return result
