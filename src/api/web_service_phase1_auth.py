from __future__ import annotations

import hmac
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Phase1AuthUser:
    token: str
    user_id: str
    org_id: str


def normalize_phase1_auth_scalar(value: Any, *, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in normalized):
        raise ValueError(f"{field_name} must not contain control characters")
    return normalized


def load_phase1_auth_users_from_config(*, raw_file: str, raw_json: str) -> list[Phase1AuthUser]:
    if not raw_file and not raw_json:
        return []

    if raw_file:
        payload_text = Path(raw_file).read_text(encoding="utf-8")
    else:
        payload_text = raw_json

    try:
        parsed = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise ValueError("PHASE1 auth users config must be valid JSON") from exc

    if isinstance(parsed, dict) and "users" in parsed:
        users_raw = parsed.get("users")
    else:
        users_raw = parsed

    if not isinstance(users_raw, list):
        raise ValueError("PHASE1 auth users config must be a list or {users:[...]} object")

    users: list[Phase1AuthUser] = []
    for idx, row in enumerate(users_raw):
        if not isinstance(row, dict):
            raise ValueError(f"PHASE1 auth users entry #{idx+1} must be an object")
        token = normalize_phase1_auth_scalar(row.get("token"), field_name="token")
        user_id = normalize_phase1_auth_scalar(row.get("user_id"), field_name="user_id")
        org_id_raw = str(row.get("org_id") or "").strip()
        org_id = org_id_raw if org_id_raw else user_id
        org_id = normalize_phase1_auth_scalar(org_id, field_name="org_id")

        users.append(Phase1AuthUser(token=token, user_id=user_id, org_id=org_id))

    if not users:
        raise ValueError("PHASE1 auth users config must contain at least one user")

    return users


def resolve_phase1_auth_user(
    bearer_token: str,
    users: list[Phase1AuthUser],
) -> Phase1AuthUser | None:
    token = str(bearer_token or "").strip()
    if not token or not users:
        return None

    match: Phase1AuthUser | None = None
    for user in users:
        if hmac.compare_digest(token, user.token):
            match = user
    return match
