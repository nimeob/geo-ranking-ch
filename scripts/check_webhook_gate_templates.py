#!/usr/bin/env python3
"""Fail-closed guard checks for BL-16 webhook-gate template artifacts."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_FILES = {
    "nginx": Path("infra/webhook_gate/nginx.aws-alarm.conf.template"),
    "compose": Path("infra/webhook_gate/docker-compose.webhook-gate.template.yml"),
}

REQUIRED_NGINX_MARKERS = [
    "location /aws-alarm",
    "deny all;",
    "proxy_pass http://__UPSTREAM_HOST__:__UPSTREAM_PORT__;",
    "if ($http_x_alarm_token != \"__ALARM_TOKEN__\")",
]

REQUIRED_COMPOSE_MARKERS = [
    "openclaw:",
    "webhook-gate:",
    "expose:",
    '__OPENCLAW_IMAGE__',
    '__OPENCLAW_PORT__',
]

REQUIRED_PLACEHOLDERS = [
    "__ALLOWLIST_RULES__",
    "__ALARM_TOKEN__",
    "__UPSTREAM_HOST__",
    "__UPSTREAM_PORT__",
    "__TLS_CERT_PATH__",
    "__TLS_KEY_PATH__",
    "__OPENCLAW_IMAGE__",
    "__OPENCLAW_PORT__",
]

FORBIDDEN_DEFAULTS = [
    "DEIN_LANGES_SECRET",
    "18.194.123.45",
    "3.120.67.89",
]


class ValidationError(Exception):
    pass


def _missing_markers(content: str, markers: list[str], prefix: str) -> list[str]:
    missing = []
    for marker in markers:
        if marker not in content:
            missing.append(f"{prefix}: marker fehlt: {marker}")
    return missing


def _placeholder_errors(nginx_content: str, compose_content: str) -> list[str]:
    bundle = f"{nginx_content}\n{compose_content}"
    errors = []
    for placeholder in REQUIRED_PLACEHOLDERS:
        if placeholder not in bundle:
            errors.append(f"placeholder fehlt: {placeholder}")
    return errors


def validate_templates_from_text(nginx_content: str, compose_content: str, render_example: bool = False) -> list[str]:
    errors: list[str] = []

    errors.extend(_missing_markers(nginx_content, REQUIRED_NGINX_MARKERS, "nginx"))
    errors.extend(_missing_markers(compose_content, REQUIRED_COMPOSE_MARKERS, "compose"))
    errors.extend(_placeholder_errors(nginx_content, compose_content))

    for bad in FORBIDDEN_DEFAULTS:
        if bad in nginx_content or bad in compose_content:
            errors.append(f"verbotener Default-Wert gefunden: {bad}")

    if "ports:" in compose_content.split("webhook-gate:", maxsplit=1)[0]:
        errors.append("compose: openclaw darf keinen öffentlichen ports-Block vor webhook-gate haben")

    if render_example:
        replacements = {
            "__ALLOWLIST_RULES__": "allow 10.0.0.1;\n      allow 10.0.0.2;",
            "__ALARM_TOKEN__": "example-token-please-override",
            "__UPSTREAM_HOST__": "openclaw",
            "__UPSTREAM_PORT__": "8080",
            "__TLS_CERT_PATH__": "/etc/nginx/certs/fullchain.pem",
            "__TLS_KEY_PATH__": "/etc/nginx/certs/privkey.pem",
            "__OPENCLAW_IMAGE__": "ghcr.io/hostinger/hvps-openclaw:latest",
            "__OPENCLAW_PORT__": "8080",
        }
        rendered = f"{nginx_content}\n{compose_content}"
        for key, value in replacements.items():
            rendered = rendered.replace(key, value)

        leftovers = sorted(set(re.findall(r"__[A-Z0-9_]+__", rendered)))
        if leftovers:
            errors.append(f"render-example hinterlässt Platzhalter: {', '.join(leftovers)}")

    return errors


def validate_templates(repo_root: Path, render_example: bool = False) -> list[str]:
    errors: list[str] = []
    content: dict[str, str] = {}

    for key, rel_path in REQUIRED_FILES.items():
        file_path = repo_root / rel_path
        if not file_path.is_file():
            errors.append(f"Datei fehlt: {rel_path}")
            continue
        content[key] = file_path.read_text(encoding="utf-8")

    if errors:
        return errors

    return validate_templates_from_text(
        nginx_content=content["nginx"],
        compose_content=content["compose"],
        render_example=render_example,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate BL-16 webhook-gate template artifacts")
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Path to repository root (default: current dir)")
    parser.add_argument(
        "--render-example",
        action="store_true",
        help="Render placeholders with sample values and fail if placeholders remain",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    errors = validate_templates(repo_root=repo_root, render_example=args.render_example)

    if errors:
        print("webhook gate template check: FAIL", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        return 1

    print("webhook gate template check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
