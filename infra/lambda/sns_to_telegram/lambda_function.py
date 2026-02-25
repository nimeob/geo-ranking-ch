"""
sns_to_telegram — Lambda-Handler
Trigger: SNS (CloudWatch Alarm Notification)
Zweck:   Forwardiert CloudWatch-Alarme kompakt als Telegram-Nachricht.

Umgebungsvariablen (Lambda):
  TELEGRAM_CHAT_ID       Ziel-Chat-ID (kein Secret, Zahl)
  TELEGRAM_BOT_TOKEN_SSM SSM-Parameter-Name für den Bot-Token (SecureString)
  AWS_REGION             gesetzt von der Lambda-Runtime automatisch

Secret-Verwaltung:
  Bot-Token liegt als SSM SecureString unter:
    /swisstopo/dev/telegram-bot-token
  Er wird per Boto3 zur Laufzeit gelesen – NICHT als Klartext in Terraform
  oder im Repo gespeichert.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Konfiguration -----------------------------------------------------------
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
SSM_PARAM_NAME = os.environ.get(
    "TELEGRAM_BOT_TOKEN_SSM", "/swisstopo/dev/telegram-bot-token"
)
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

_ssm_client: Any = None
_cached_token: str | None = None


def _get_bot_token() -> str:
    """Holt den Bot-Token einmalig aus SSM Parameter Store (gecached per Warm-Start)."""
    global _ssm_client, _cached_token
    if _cached_token:
        return _cached_token
    if _ssm_client is None:
        _ssm_client = boto3.client("ssm", region_name=os.environ.get("AWS_REGION", "eu-central-1"))
    response = _ssm_client.get_parameter(Name=SSM_PARAM_NAME, WithDecryption=True)
    _cached_token = response["Parameter"]["Value"]
    return _cached_token  # type: ignore[return-value]


def _safe(d: dict, *keys: str, default: str = "–") -> str:
    """Liest geschachtelte Dict-Keys robust; gibt Default zurück wenn fehlt."""
    val = d
    for k in keys:
        if not isinstance(val, dict):
            return default
        val = val.get(k, default)
    return str(val) if val is not None else default


def _format_alarm_message(alarm: dict) -> str:
    """Kompaktes Telegram-Nachrichtenformat für einen CloudWatch-Alarm."""
    state = _safe(alarm, "NewStateValue")
    name = _safe(alarm, "AlarmName")
    reason = _safe(alarm, "NewStateReason")
    region = _safe(alarm, "Region")
    account = _safe(alarm, "AWSAccountId")
    timestamp = _safe(alarm, "StateChangeTime")

    # Emoji je nach State
    icon = {"ALARM": "🚨", "OK": "✅", "INSUFFICIENT_DATA": "⚠️"}.get(state, "❓")

    return (
        f"{icon} *CloudWatch Alarm* — {state}\n"
        f"*Name:* `{name}`\n"
        f"*Grund:* {reason}\n"
        f"*Region:* {region}  |  *Account:* `{account}`\n"
        f"*Zeit:* {timestamp}"
    )


def _send_telegram(token: str, chat_id: str, text: str) -> None:
    """Sendet eine Nachricht via Telegram Bot API (MarkdownV2 escaped, Fallback Plain)."""
    payload = json.dumps(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
    ).encode("utf-8")
    url = TELEGRAM_API.format(token=token)
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            logger.info("Telegram API response: %s", body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        logger.error("Telegram API HTTP error %s: %s", exc.code, body)
        raise


def lambda_handler(event: dict, context: Any) -> dict:
    """Entry-Point. Verarbeitet SNS-Records (ein oder mehrere pro Invokation)."""
    if not CHAT_ID:
        logger.error("TELEGRAM_CHAT_ID nicht gesetzt — Abbruch.")
        return {"status": "error", "reason": "missing TELEGRAM_CHAT_ID"}

    token = _get_bot_token()
    processed = 0
    errors = 0

    for record in event.get("Records", []):
        try:
            sns_msg = record.get("Sns", {})
            raw_message = sns_msg.get("Message", "{}")
            # CloudWatch sendet JSON als String im SNS-Message-Feld
            try:
                alarm = json.loads(raw_message)
            except json.JSONDecodeError:
                alarm = {}

            text = _format_alarm_message(alarm) if alarm else f"⚠️ SNS-Nachricht (kein Alarm-JSON):\n{raw_message[:800]}"
            _send_telegram(token, CHAT_ID, text)
            processed += 1
            logger.info("Alarm-Nachricht gesendet: AlarmName=%s", alarm.get("AlarmName", "?"))
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Fehler beim Verarbeiten von Record: %s", exc)
            errors += 1

    return {"processed": processed, "errors": errors}
