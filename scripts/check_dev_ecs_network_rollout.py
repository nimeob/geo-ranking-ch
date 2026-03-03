#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _run_aws_describe_service(region: str, cluster: str, service: str) -> dict[str, Any]:
    cmd = [
        "aws",
        "ecs",
        "describe-services",
        "--region",
        region,
        "--cluster",
        cluster,
        "--services",
        service,
        "--output",
        "json",
    ]
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode != 0:
        detail = (cp.stderr or cp.stdout or "unknown aws error").strip()
        raise RuntimeError(f"AWS describe-services failed: {detail}")
    return json.loads(cp.stdout)


def evaluate_rollout(
    service_obj: dict[str, Any],
    *,
    expected_subnets: list[str],
    expected_assign_public_ip: str,
    expected_target_group_substring: str,
) -> dict[str, Any]:
    network_cfg = (service_obj.get("networkConfiguration") or {}).get("awsvpcConfiguration") or {}
    actual_subnets = sorted(network_cfg.get("subnets") or [])
    expected_subnets_sorted = sorted(expected_subnets)

    assign_public_ip = str(network_cfg.get("assignPublicIp") or "").upper()
    expected_assign_public_ip_norm = expected_assign_public_ip.upper()

    load_balancers = service_obj.get("loadBalancers") or []
    target_group_arns = [lb.get("targetGroupArn") for lb in load_balancers if lb.get("targetGroupArn")]

    deployments = service_obj.get("deployments") or []
    rollout_completed = any(
        (dep.get("status") == "PRIMARY") and (dep.get("rolloutState") == "COMPLETED") for dep in deployments
    )

    checks = {
        "subnets_match_expected": actual_subnets == expected_subnets_sorted,
        "assign_public_ip_matches": assign_public_ip == expected_assign_public_ip_norm,
        "primary_rollout_completed": rollout_completed,
        "single_target_group_attached": len(target_group_arns) == 1,
        "expected_target_group_attached": any(expected_target_group_substring in arn for arn in target_group_arns),
    }

    ok = all(checks.values())

    return {
        "ok": ok,
        "checked_at": _utc_now(),
        "service": {
            "serviceArn": service_obj.get("serviceArn"),
            "taskDefinition": service_obj.get("taskDefinition"),
            "desiredCount": service_obj.get("desiredCount"),
            "runningCount": service_obj.get("runningCount"),
        },
        "expected": {
            "subnets": expected_subnets_sorted,
            "assignPublicIp": expected_assign_public_ip_norm,
            "targetGroupArnContains": expected_target_group_substring,
        },
        "actual": {
            "subnets": actual_subnets,
            "assignPublicIp": assign_public_ip,
            "targetGroupArns": target_group_arns,
            "deployments": [
                {
                    "id": dep.get("id"),
                    "status": dep.get("status"),
                    "rolloutState": dep.get("rolloutState"),
                    "rolloutStateReason": dep.get("rolloutStateReason"),
                    "runningCount": dep.get("runningCount"),
                    "pendingCount": dep.get("pendingCount"),
                }
                for dep in deployments
            ],
        },
        "checks": checks,
    }


def _parse_expected_subnets(values: list[str]) -> list[str]:
    out: list[str] = []
    for item in values:
        out.extend(part.strip() for part in item.split(",") if part.strip())
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate dev ECS private-subnet rollout state.")
    parser.add_argument("--region", default="eu-central-1")
    parser.add_argument("--cluster", default="swisstopo-dev")
    parser.add_argument("--service", default="swisstopo-dev-api")
    parser.add_argument(
        "--expected-subnet",
        action="append",
        default=["subnet-0cd8553a1fedbf183", "subnet-04d5ddec3c5b06d7a"],
        help="Expected subnet id(s), repeatable or comma-separated.",
    )
    parser.add_argument("--expected-assign-public-ip", default="DISABLED")
    parser.add_argument(
        "--expected-target-group-substring",
        default="targetgroup/swisstopo-dev-vpc-api-tg/",
        help="Substring that must appear in the attached target group ARN.",
    )
    parser.add_argument("--service-json", default="", help="Optional path to describe-services JSON.")
    parser.add_argument("--output-json", required=True)

    args = parser.parse_args(argv)

    expected_subnets = _parse_expected_subnets(args.expected_subnet)
    if not expected_subnets:
        print("expected-subnet must not be empty", file=sys.stderr)
        return 2

    try:
        if args.service_json:
            payload = json.loads(Path(args.service_json).read_text(encoding="utf-8"))
        else:
            payload = _run_aws_describe_service(args.region, args.cluster, args.service)
    except Exception as exc:  # noqa: BLE001
        print(f"failed to load service payload: {exc}", file=sys.stderr)
        return 1

    services = payload.get("services") or []
    if not services:
        print("no ECS service in payload", file=sys.stderr)
        return 1

    result = evaluate_rollout(
        services[0],
        expected_subnets=expected_subnets,
        expected_assign_public_ip=args.expected_assign_public_ip,
        expected_target_group_substring=args.expected_target_group_substring,
    )

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote rollout check: {out_path}")

    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
