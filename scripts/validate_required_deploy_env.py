#!/usr/bin/env python3
"""Fail-fast preflight for required deploy environment keys.

Used by `.github/workflows/deploy.yml` before any AWS/OIDC interaction so
configuration issues are surfaced early with actionable fix hints.
"""

from dataclasses import dataclass
import os
import sys
from typing import Mapping


@dataclass(frozen=True)
class RequiredKey:
    name: str
    source: str  # "variable" | "secret"


REQUIRED_KEYS: tuple[RequiredKey, ...] = (
    RequiredKey("ECS_CLUSTER", "variable"),
    RequiredKey("ECS_API_SERVICE", "variable"),
    RequiredKey("ECS_UI_SERVICE", "variable"),
    RequiredKey("ECS_API_CONTAINER_NAME", "variable"),
    RequiredKey("ECS_UI_CONTAINER_NAME", "variable"),
    RequiredKey("ECR_API_REPOSITORY", "variable"),
    RequiredKey("ECR_UI_REPOSITORY", "variable"),
    RequiredKey("SERVICE_APP_BASE_URL", "variable"),
    RequiredKey("SERVICE_API_AUTH_TOKEN", "secret"),
)


def _is_blank(value: str | None) -> bool:
    return value is None or value.strip() == ""


def collect_missing_keys(environ: Mapping[str, str]) -> list[RequiredKey]:
    missing: list[RequiredKey] = []
    for key in REQUIRED_KEYS:
        if _is_blank(environ.get(key.name)):
            missing.append(key)

    # For API health checks we require at least one source URL.
    if _is_blank(environ.get("SERVICE_API_BASE_URL")) and _is_blank(environ.get("SERVICE_HEALTH_URL")):
        missing.append(RequiredKey("SERVICE_API_BASE_URL or SERVICE_HEALTH_URL", "variable"))

    return missing


def _settings_hint(source: str) -> str:
    panel = "Variables" if source == "variable" else "Secrets"
    return (
        "GitHub Settings → Secrets and variables → Actions → "
        f"{panel}"
    )


def run(environ: Mapping[str, str]) -> int:
    missing = collect_missing_keys(environ)
    if not missing:
        print("Deploy preflight OK: all required environment keys are set.")
        return 0

    print(
        f"::error::Deploy preflight failed: missing required environment keys ({len(missing)})."
    )
    print("::error::Missing keys:")
    for key in missing:
        print(f"::error:: - {key.name} [{key.source}]")
        print(
            "::error::   Fix hint: "
            f"Set `{key.name}` in {_settings_hint(key.source)}."
        )

    return 1


def main() -> int:
    return run(os.environ)


if __name__ == "__main__":
    raise SystemExit(main())
