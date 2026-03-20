#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Protocol


class AwsClient(Protocol):
    def json(self, args: list[str], *, region: str) -> dict[str, Any]: ...

    def call(self, args: list[str], *, region: str) -> None: ...


class AwsCliError(RuntimeError):
    def __init__(self, *, command: list[str], returncode: int, stderr: str) -> None:
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"aws command failed ({returncode}): {' '.join(command)} :: {stderr.strip()}")


class AwsCli:
    def json(self, args: list[str], *, region: str) -> dict[str, Any]:
        command = ["aws", *args, "--region", region, "--output", "json"]
        try:
            completed = subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise AwsCliError(command=command, returncode=exc.returncode, stderr=exc.stderr or "") from exc
        return json.loads(completed.stdout or "{}")

    def call(self, args: list[str], *, region: str) -> None:
        command = ["aws", *args, "--region", region]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise AwsCliError(command=command, returncode=exc.returncode, stderr=exc.stderr or "") from exc


@dataclass(frozen=True)
class Config:
    lb_name: str
    region: str
    required_ports: tuple[int, ...]
    ui_hosts: tuple[str, ...]
    ui_target_group_substring: str
    apply: bool
    output_json: str


def _extract_condition_values(condition: dict[str, Any], *, field: str) -> list[str]:
    if condition.get("Field") != field:
        return []
    config_key = "HostHeaderConfig" if field == "host-header" else "PathPatternConfig"
    configured = condition.get(config_key) or {}
    values = configured.get("Values")
    if isinstance(values, list):
        return [str(item).strip().lower() for item in values if str(item).strip()]
    values = condition.get("Values")
    if isinstance(values, list):
        return [str(item).strip().lower() for item in values if str(item).strip()]
    return []


def _normalize_path_pattern(value: str) -> str:
    return value.strip().lower().replace(" ", "")


def _is_login_or_signin_pattern(value: str) -> bool:
    normalized = _normalize_path_pattern(value)
    return normalized in {
        "/login",
        "/login*",
        "/signin",
        "/signin*",
        "/sign-in",
        "/sign-in*",
    }


def _rule_redirects_to_auth_login(rule: dict[str, Any]) -> bool:
    for action in rule.get("Actions") or []:
        if (action.get("Type") or "").lower() != "redirect":
            continue
        redirect = action.get("RedirectConfig") or {}
        path = str(redirect.get("Path") or "").strip().lower()
        if path == "/auth/login" or path == "/auth/login*":
            return True
    return False


def _rule_forwards_to_ui_target_group(rule: dict[str, Any], *, ui_tg_substring: str) -> bool:
    expected = ui_tg_substring.lower()
    for action in rule.get("Actions") or []:
        if (action.get("Type") or "").lower() != "forward":
            continue
        target_arns: list[str] = []
        direct = action.get("TargetGroupArn")
        if isinstance(direct, str) and direct:
            target_arns.append(direct)
        forward_cfg = action.get("ForwardConfig") or {}
        for tg in forward_cfg.get("TargetGroups") or []:
            arn = tg.get("TargetGroupArn")
            if isinstance(arn, str) and arn:
                target_arns.append(arn)
        if any(expected in arn.lower() for arn in target_arns):
            return True
    return False


def _collect_rules(aws: AwsClient, *, listener_arn: str, region: str) -> list[dict[str, Any]]:
    response = aws.json(["elbv2", "describe-rules", "--listener-arn", listener_arn], region=region)
    return list(response.get("Rules") or [])


def reconcile(config: Config, *, aws: AwsClient | None = None) -> tuple[int, dict[str, Any]]:
    aws_client = aws or AwsCli()

    lb = aws_client.json(
        ["elbv2", "describe-load-balancers", "--names", config.lb_name],
        region=config.region,
    )
    load_balancers = lb.get("LoadBalancers") or []
    if not load_balancers:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "overall": {"status": "fail", "reason": "load_balancer_not_found"},
            "config": {
                "lb_name": config.lb_name,
                "region": config.region,
            },
            "findings": [{"reason": "load_balancer_not_found", "lb_name": config.lb_name}],
            "actions": [],
        }
        return 1, payload

    lb_arn = str(load_balancers[0].get("LoadBalancerArn"))
    listeners_resp = aws_client.json(
        ["elbv2", "describe-listeners", "--load-balancer-arn", lb_arn],
        region=config.region,
    )
    listeners = list(listeners_resp.get("Listeners") or [])

    listeners_by_port: dict[int, list[dict[str, Any]]] = {}
    for listener in listeners:
        port = int(listener.get("Port") or 0)
        listeners_by_port.setdefault(port, []).append(listener)

    ui_hosts = {host.strip().lower() for host in config.ui_hosts if host.strip()}

    findings: list[dict[str, Any]] = []
    stale_rule_candidates: list[dict[str, Any]] = []

    for required_port in config.required_ports:
        selected = listeners_by_port.get(required_port) or []
        if not selected:
            findings.append(
                {
                    "severity": "error",
                    "reason": "missing_listener_port",
                    "port": required_port,
                }
            )
            continue

        for listener in selected:
            listener_arn = str(listener.get("ListenerArn") or "")
            rules = _collect_rules(aws_client, listener_arn=listener_arn, region=config.region)
            listener_finding: dict[str, Any] = {
                "listener_arn": listener_arn,
                "port": required_port,
                "ui_forward_rules": [],
                "stale_login_redirect_rules": [],
            }

            for rule in rules:
                if rule.get("IsDefault"):
                    continue

                rule_arn = str(rule.get("RuleArn") or "")
                priority = str(rule.get("Priority") or "")
                host_values: set[str] = set()
                path_values: set[str] = set()

                for condition in rule.get("Conditions") or []:
                    host_values.update(_extract_condition_values(condition, field="host-header"))
                    path_values.update(_extract_condition_values(condition, field="path-pattern"))

                host_intersection = sorted(ui_hosts.intersection(host_values))
                if host_intersection and _rule_forwards_to_ui_target_group(
                    rule,
                    ui_tg_substring=config.ui_target_group_substring,
                ):
                    listener_finding["ui_forward_rules"].append(
                        {
                            "rule_arn": rule_arn,
                            "priority": priority,
                            "hosts": sorted(host_values),
                        }
                    )

                has_login_path = any(_is_login_or_signin_pattern(value) for value in path_values)
                if host_intersection and has_login_path and _rule_redirects_to_auth_login(rule):
                    stale = {
                        "rule_arn": rule_arn,
                        "priority": priority,
                        "hosts": sorted(host_values),
                        "paths": sorted(path_values),
                    }
                    listener_finding["stale_login_redirect_rules"].append(stale)
                    stale_rule_candidates.append(
                        {
                            "listener_arn": listener_arn,
                            "port": required_port,
                            **stale,
                        }
                    )

            if not listener_finding["ui_forward_rules"]:
                findings.append(
                    {
                        "severity": "error",
                        "reason": "missing_ui_host_forward_rule",
                        "port": required_port,
                        "listener_arn": listener_arn,
                        "ui_hosts": sorted(ui_hosts),
                        "ui_target_group_substring": config.ui_target_group_substring,
                    }
                )

            findings.append(listener_finding)

    blocking_errors = [f for f in findings if f.get("severity") == "error"]

    actions: list[dict[str, Any]] = []
    if not blocking_errors and stale_rule_candidates and config.apply:
        for rule in stale_rule_candidates:
            aws_client.call(["elbv2", "delete-rule", "--rule-arn", rule["rule_arn"]], region=config.region)
            actions.append(
                {
                    "type": "delete_rule",
                    "rule_arn": rule["rule_arn"],
                    "priority": rule["priority"],
                    "listener_arn": rule["listener_arn"],
                    "port": rule["port"],
                }
            )

    if blocking_errors:
        overall_status = "fail"
        overall_reason = blocking_errors[0]["reason"]
    elif stale_rule_candidates and not config.apply:
        overall_status = "fail"
        overall_reason = "stale_login_redirect_rules_detected"
    elif stale_rule_candidates and config.apply:
        overall_status = "pass"
        overall_reason = "stale_login_redirect_rules_deleted"
    else:
        overall_status = "pass"
        overall_reason = "no_drift_detected"

    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "overall": {
            "status": overall_status,
            "reason": overall_reason,
        },
        "config": {
            "lb_name": config.lb_name,
            "region": config.region,
            "required_ports": list(config.required_ports),
            "ui_hosts": sorted(ui_hosts),
            "ui_target_group_substring": config.ui_target_group_substring,
            "apply": config.apply,
        },
        "summary": {
            "stale_rule_count": len(stale_rule_candidates),
            "deleted_rule_count": len(actions),
            "error_count": len(blocking_errors),
        },
        "stale_rules": stale_rule_candidates,
        "findings": findings,
        "actions": actions,
    }

    return (0 if overall_status == "pass" else 1), payload


def _load_config(argv: Iterable[str] | None = None) -> Config:
    parser = argparse.ArgumentParser(
        description=(
            "Check/reconcile DEV ALB listener intent: UI hosts must forward to UI target group "
            "and must not contain stale /login|/signin -> /auth/login redirect rules."
        )
    )
    parser.add_argument("--lb-name", default="swisstopo-dev-vpc-alb")
    parser.add_argument("--region", default="eu-central-1")
    parser.add_argument("--required-port", type=int, action="append", default=[])
    parser.add_argument(
        "--ui-host",
        action="append",
        default=[],
        help="UI host header value expected to forward to UI target group (repeatable)",
    )
    parser.add_argument(
        "--ui-target-group-substring",
        default="swisstopo-dev-vpc-ui-tg",
        help="Substring that must be present in target group ARN for UI host forward rules",
    )
    parser.add_argument("--apply", action="store_true", help="Delete stale login/signin redirect rules")
    parser.add_argument("--output-json", default="")

    args = parser.parse_args(list(argv) if argv is not None else None)

    required_ports = tuple(args.required_port or [80, 443])
    if any(port <= 0 for port in required_ports):
        raise ValueError("required-port must be > 0")

    ui_hosts = tuple(
        dict.fromkeys(
            [
                host.strip().lower()
                for host in (args.ui_host or ["www.dev.georanking.ch", "www.dev.geo-ranking.ch"])
                if host.strip()
            ]
        )
    )
    if not ui_hosts:
        raise ValueError("at least one --ui-host is required")

    if not args.ui_target_group_substring.strip():
        raise ValueError("ui-target-group-substring must not be empty")

    return Config(
        lb_name=args.lb_name.strip(),
        region=args.region.strip(),
        required_ports=required_ports,
        ui_hosts=ui_hosts,
        ui_target_group_substring=args.ui_target_group_substring.strip(),
        apply=bool(args.apply),
        output_json=args.output_json.strip(),
    )


def _write_json(path: str, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _is_access_denied(stderr: str) -> bool:
    text = (stderr or "").lower()
    return (
        "accessdenied" in text
        or "not authorized" in text
        or "is not authorized" in text
        or "unauthorizedoperation" in text
    )


def main(argv: Iterable[str] | None = None) -> int:
    try:
        config = _load_config(argv)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    try:
        exit_code, payload = reconcile(config)
    except AwsCliError as exc:
        access_denied = _is_access_denied(exc.stderr)
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "overall": {
                "status": "warn" if access_denied else "fail",
                "reason": "aws_access_denied" if access_denied else "aws_cli_error",
            },
            "config": {
                "lb_name": config.lb_name,
                "region": config.region,
                "required_ports": list(config.required_ports),
                "ui_hosts": sorted(config.ui_hosts),
                "ui_target_group_substring": config.ui_target_group_substring,
                "apply": config.apply,
            },
            "summary": {
                "stale_rule_count": 0,
                "deleted_rule_count": 0,
                "error_count": 1,
            },
            "findings": [
                {
                    "severity": "warning" if access_denied else "error",
                    "reason": "aws_access_denied" if access_denied else "aws_cli_error",
                    "command": exc.command,
                    "returncode": exc.returncode,
                    "stderr": exc.stderr,
                }
            ],
            "actions": [],
        }
        exit_code = 3 if access_denied else 1

    print(json.dumps(payload, ensure_ascii=False))

    if config.output_json:
        _write_json(config.output_json, payload)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
