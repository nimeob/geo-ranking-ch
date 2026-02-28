#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List


VALID_MODES = {"api", "ui", "both"}


@dataclass(frozen=True)
class Config:
    mode: str
    execute: bool
    aws_region: str
    ecs_cluster: str
    api_service: str
    ui_service: str
    smoke_script: str
    out_dir: Path


def resolve_steps(mode: str) -> List[str]:
    if mode not in VALID_MODES:
        raise ValueError(f"unsupported mode: {mode}")
    if mode == "both":
        return ["api", "ui"]
    return [mode]


def _run_command(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False, env=env)


def _service_taskdef(config: Config, service: str) -> str:
    result = _run_command(
        [
            "aws",
            "ecs",
            "describe-services",
            "--region",
            config.aws_region,
            "--cluster",
            config.ecs_cluster,
            "--services",
            service,
            "--query",
            "services[0].taskDefinition",
            "--output",
            "text",
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(f"failed to describe service {service}: {result.stderr.strip()}")
    value = result.stdout.strip()
    if not value or value == "None":
        raise RuntimeError(f"service has no task definition: {service}")
    return value


def _update_service(config: Config, service: str) -> None:
    result = _run_command(
        [
            "aws",
            "ecs",
            "update-service",
            "--region",
            config.aws_region,
            "--cluster",
            config.ecs_cluster,
            "--service",
            service,
            "--force-new-deployment",
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(f"failed to update service {service}: {result.stderr.strip()}")


def _wait_services_stable(config: Config, service: str) -> None:
    result = _run_command(
        [
            "aws",
            "ecs",
            "wait",
            "services-stable",
            "--region",
            config.aws_region,
            "--cluster",
            config.ecs_cluster,
            "--services",
            service,
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(f"service did not stabilize ({service}): {result.stderr.strip()}")


def _run_smoke(config: Config, mode: str, stamp: str) -> str:
    smoke_output = config.out_dir / f"{stamp}-bl31-split-deploy-{mode}-smoke.json"
    env = os.environ.copy()
    env["BL31_STRICT_CORS"] = "1"
    env["BL31_OUTPUT_JSON"] = str(smoke_output)

    result = _run_command([config.smoke_script], env=env)
    if result.returncode != 0:
        raise RuntimeError(
            "smoke script failed: "
            f"mode={mode} rc={result.returncode} stderr={result.stderr.strip()}"
        )
    return str(smoke_output)


def _other_service(config: Config, service_key: str) -> str:
    if service_key == "api":
        return config.ui_service
    if service_key == "ui":
        return config.api_service
    raise ValueError(f"unknown service key: {service_key}")


def _service_name(config: Config, service_key: str) -> str:
    if service_key == "api":
        return config.api_service
    if service_key == "ui":
        return config.ui_service
    raise ValueError(f"unknown service key: {service_key}")


def _assert_service_local_guardrail(
    *,
    selected_key: str,
    before_api_taskdef: str,
    before_ui_taskdef: str,
    after_api_taskdef: str,
    after_ui_taskdef: str,
) -> None:
    if selected_key == "api" and after_ui_taskdef != before_ui_taskdef:
        raise RuntimeError(
            "guardrail violation: API-only step changed UI task definition "
            f"({before_ui_taskdef} -> {after_ui_taskdef})"
        )
    if selected_key == "ui" and after_api_taskdef != before_api_taskdef:
        raise RuntimeError(
            "guardrail violation: UI-only step changed API task definition "
            f"({before_api_taskdef} -> {after_api_taskdef})"
        )


DRY_RUN_TASKDEF_VALUE = "not-collected (dry-run)"
RESULT_PLANNED = "planned"
RESULT_PASS = "pass"


def _taskdef_snapshot(api_taskdef: str, ui_taskdef: str) -> dict[str, str]:
    return {"api": api_taskdef, "ui": ui_taskdef}


def _dry_run_taskdef_snapshot() -> dict[str, str]:
    return _taskdef_snapshot(DRY_RUN_TASKDEF_VALUE, DRY_RUN_TASKDEF_VALUE)


def execute_deploy(config: Config) -> dict:
    config.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    steps = resolve_steps(config.mode)

    evidence: dict = {
        "timestampUtc": stamp,
        "mode": config.mode,
        "execute": config.execute,
        "result": RESULT_PLANNED,
        "region": config.aws_region,
        "cluster": config.ecs_cluster,
        "taskDefinitionBefore": _dry_run_taskdef_snapshot(),
        "taskDefinitionAfter": _dry_run_taskdef_snapshot(),
        "smokeArtifacts": [],
        "steps": [],
    }

    if not config.execute:
        evidence["plan"] = [
            {
                "step": step,
                "service": _service_name(config, step),
                "commands": [
                    f"aws ecs update-service --cluster {config.ecs_cluster} --service {_service_name(config, step)} --force-new-deployment",
                    f"aws ecs wait services-stable --cluster {config.ecs_cluster} --services {_service_name(config, step)}",
                    f"BL31_STRICT_CORS=1 BL31_OUTPUT_JSON=<...{step}...> {config.smoke_script}",
                ],
                "guardrail": f"{_other_service(config, step)} task definition must remain unchanged",
            }
            for step in steps
        ]
        return evidence

    before_api = _service_taskdef(config, config.api_service)
    before_ui = _service_taskdef(config, config.ui_service)
    evidence["taskDefinitionBefore"] = _taskdef_snapshot(before_api, before_ui)

    for step in steps:
        selected_service = _service_name(config, step)
        _update_service(config, selected_service)
        _wait_services_stable(config, selected_service)

        smoke_output = _run_smoke(config, step, stamp)

        after_api = _service_taskdef(config, config.api_service)
        after_ui = _service_taskdef(config, config.ui_service)
        _assert_service_local_guardrail(
            selected_key=step,
            before_api_taskdef=before_api,
            before_ui_taskdef=before_ui,
            after_api_taskdef=after_api,
            after_ui_taskdef=after_ui,
        )

        evidence["smokeArtifacts"].append(smoke_output)
        evidence["steps"].append(
            {
                "step": step,
                "service": selected_service,
                "taskDefinitionBefore": _taskdef_snapshot(before_api, before_ui),
                "taskDefinitionAfter": _taskdef_snapshot(after_api, after_ui),
                "smokeArtifact": smoke_output,
                "guardrail": "ok",
            }
        )

        before_api = after_api
        before_ui = after_ui

    evidence["taskDefinitionAfter"] = _taskdef_snapshot(before_api, before_ui)
    evidence["result"] = RESULT_PASS
    return evidence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "BL-31 split deploy orchestrator (api|ui|both). "
            "Default is dry-run; pass --execute to perform AWS operations."
        )
    )
    parser.add_argument("--mode", choices=sorted(VALID_MODES), required=True)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute AWS update/wait + smoke checks. Without this flag the script runs in dry-run mode.",
    )
    parser.add_argument("--aws-region", default=os.getenv("AWS_REGION", "eu-central-1"))
    parser.add_argument("--ecs-cluster", default=os.getenv("ECS_CLUSTER", "swisstopo-dev"))
    parser.add_argument("--api-service", default=os.getenv("API_SERVICE", "swisstopo-dev-api"))
    parser.add_argument("--ui-service", default=os.getenv("UI_SERVICE", "swisstopo-dev-ui"))
    parser.add_argument(
        "--smoke-script",
        default=os.getenv("BL31_SMOKE_SCRIPT", "./scripts/run_bl31_routing_tls_smoke.sh"),
    )
    parser.add_argument(
        "--out-dir",
        default=os.getenv("BL31_SPLIT_DEPLOY_OUT_DIR", "artifacts/bl31"),
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional path for full orchestration output JSON.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    config = Config(
        mode=args.mode,
        execute=bool(args.execute),
        aws_region=args.aws_region,
        ecs_cluster=args.ecs_cluster,
        api_service=args.api_service,
        ui_service=args.ui_service,
        smoke_script=args.smoke_script,
        out_dir=Path(args.out_dir),
    )

    try:
        payload = execute_deploy(config)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    output_path = Path(args.output_json) if args.output_json else config.out_dir / (
        f"{payload['timestampUtc']}-bl31-split-deploy-{config.mode}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if config.execute:
        print(f"✅ BL-31 split deploy completed ({config.mode})")
    else:
        print(f"🧪 BL-31 split deploy dry-run plan generated ({config.mode})")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
