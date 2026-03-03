#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import ssl
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

DEFAULT_EXPECTED_HOSTS = [
    "api.dev.georanking.ch",
    "api.dev.geo-ranking.ch",
    "www.dev.georanking.ch",
    "www.dev.geo-ranking.ch",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _run_aws_json(args: list[str], region: str | None = None) -> dict[str, Any]:
    cmd = ["aws"]
    if region:
        cmd.extend(["--region", region])
    cmd.extend(args)
    cmd.extend(["--output", "json"])
    cp = subprocess.run(cmd, capture_output=True, text=True)
    if cp.returncode != 0:
        stderr = (cp.stderr or "").strip()
        stdout = (cp.stdout or "").strip()
        detail = stderr or stdout or "unknown aws cli error"
        raise RuntimeError(f"AWS CLI failed ({' '.join(cmd)}): {detail}")
    try:
        return json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"AWS CLI produced invalid JSON for {' '.join(cmd)}") from exc


def collect_live_snapshot(lb_name: str, region: str | None = None) -> dict[str, Any]:
    lb_resp = _run_aws_json(["elbv2", "describe-load-balancers", "--names", lb_name], region=region)
    lbs = lb_resp.get("LoadBalancers") or []
    if not lbs:
        raise RuntimeError(f"Load balancer not found: {lb_name}")
    lb = lbs[0]
    lb_arn = lb["LoadBalancerArn"]

    listeners_resp = _run_aws_json(["elbv2", "describe-listeners", "--load-balancer-arn", lb_arn], region=region)
    listeners = listeners_resp.get("Listeners") or []

    rules_by_listener: dict[str, list[dict[str, Any]]] = {}
    for listener in listeners:
        listener_arn = listener["ListenerArn"]
        rules_resp = _run_aws_json(["elbv2", "describe-rules", "--listener-arn", listener_arn], region=region)
        rules_by_listener[listener_arn] = rules_resp.get("Rules") or []

    tgs_resp = _run_aws_json(["elbv2", "describe-target-groups", "--load-balancer-arn", lb_arn], region=region)
    target_groups = tgs_resp.get("TargetGroups") or []

    target_health: dict[str, list[dict[str, Any]]] = {}
    for tg in target_groups:
        tg_arn = tg["TargetGroupArn"]
        th_resp = _run_aws_json(["elbv2", "describe-target-health", "--target-group-arn", tg_arn], region=region)
        target_health[tg_arn] = th_resp.get("TargetHealthDescriptions") or []

    sg_ids = lb.get("SecurityGroups") or []
    security_groups: list[dict[str, Any]] = []
    if sg_ids:
        sg_resp = _run_aws_json(["ec2", "describe-security-groups", "--group-ids", *sg_ids], region=region)
        security_groups = sg_resp.get("SecurityGroups") or []

    subnet_ids = [
        az.get("SubnetId")
        for az in (lb.get("AvailabilityZones") or [])
        if isinstance(az, dict) and az.get("SubnetId")
    ]

    subnets: list[dict[str, Any]] = []
    network_acls: list[dict[str, Any]] = []
    if subnet_ids:
        subnet_resp = _run_aws_json(["ec2", "describe-subnets", "--subnet-ids", *subnet_ids], region=region)
        subnets = subnet_resp.get("Subnets") or []

        nacl_filter = f"Name=association.subnet-id,Values={','.join(subnet_ids)}"
        nacl_resp = _run_aws_json(["ec2", "describe-network-acls", "--filters", nacl_filter], region=region)
        network_acls = nacl_resp.get("NetworkAcls") or []

    return {
        "load_balancer": lb,
        "listeners": listeners,
        "rules_by_listener": rules_by_listener,
        "target_groups": target_groups,
        "target_health": target_health,
        "security_groups": security_groups,
        "subnets": subnets,
        "network_acls": network_acls,
    }


def _extract_host_condition_values(rule: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for cond in rule.get("Conditions") or []:
        if cond.get("Field") == "host-header":
            cfg = cond.get("HostHeaderConfig") or {}
            for value in cfg.get("Values") or []:
                if isinstance(value, str) and value.strip():
                    out.append(value.strip().lower())
    return out


def _summarize_target_health(target_health_entries: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"healthy": 0, "unhealthy": 0, "initial": 0, "unused": 0, "other": 0, "total": 0}
    for entry in target_health_entries:
        state = ((entry.get("TargetHealth") or {}).get("State") or "other").lower()
        if state in summary:
            summary[state] += 1
        else:
            summary["other"] += 1
        summary["total"] += 1
    return summary


def _extract_nacl_subnet_ids(nacl: dict[str, Any]) -> list[str]:
    subnet_ids: list[str] = []
    for assoc in nacl.get("Associations") or []:
        subnet_id = assoc.get("SubnetId")
        if isinstance(subnet_id, str) and subnet_id:
            subnet_ids.append(subnet_id)
    return subnet_ids


def _first_matching_nacl_rule(
    nacl: dict[str, Any],
    *,
    egress: bool,
    protocol: str,
    port: int,
) -> dict[str, Any] | None:
    entries = sorted(
        [entry for entry in (nacl.get("Entries") or []) if bool(entry.get("Egress")) == egress],
        key=lambda item: int(item.get("RuleNumber") or 32767),
    )

    for entry in entries:
        entry_protocol = str(entry.get("Protocol") or "")
        if entry_protocol not in ("-1", protocol):
            continue

        cidr = entry.get("CidrBlock") or entry.get("Ipv6CidrBlock") or ""
        if cidr not in ("0.0.0.0/0", "::/0"):
            continue

        if entry_protocol == "-1":
            return entry

        port_range = entry.get("PortRange") or {}
        from_port = int(port_range.get("From") or -1)
        to_port = int(port_range.get("To") or -1)
        if from_port <= port <= to_port:
            return entry

    return None


def _is_nacl_allow(
    nacl: dict[str, Any],
    *,
    egress: bool,
    protocol: str,
    port: int,
) -> bool | None:
    match = _first_matching_nacl_rule(nacl, egress=egress, protocol=protocol, port=port)
    if not match:
        return None
    return bool(match.get("RuleAction") == "allow")


def _summarize_network_acl(nacl: dict[str, Any]) -> dict[str, Any]:
    return {
        "nacl_id": nacl.get("NetworkAclId"),
        "subnet_ids": _extract_nacl_subnet_ids(nacl),
        "ingress_tcp_80": _is_nacl_allow(nacl, egress=False, protocol="6", port=80),
        "ingress_tcp_443": _is_nacl_allow(nacl, egress=False, protocol="6", port=443),
        "egress_tcp_443": _is_nacl_allow(nacl, egress=True, protocol="6", port=443),
        "egress_tcp_32768": _is_nacl_allow(nacl, egress=True, protocol="6", port=32768),
    }


def analyze_snapshot(snapshot: dict[str, Any], expected_hosts: list[str]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    listeners = snapshot.get("listeners") or []
    rules_by_listener = snapshot.get("rules_by_listener") or {}
    target_groups = snapshot.get("target_groups") or []
    target_health = snapshot.get("target_health") or {}
    security_groups = snapshot.get("security_groups") or []
    network_acls = snapshot.get("network_acls") or []

    listeners_by_port: dict[int, list[dict[str, Any]]] = {}
    for listener in listeners:
        port = int(listener.get("Port") or 0)
        listeners_by_port.setdefault(port, []).append(listener)

    if 443 not in listeners_by_port:
        findings.append(
            {
                "id": "missing_https_listener",
                "severity": "critical",
                "summary": "ALB has no HTTPS listener on port 443.",
                "evidence": {
                    "listener_ports": sorted(listeners_by_port.keys()),
                    "listener_arns": [listener.get("ListenerArn") for listener in listeners],
                },
            }
        )

    if 80 not in listeners_by_port:
        findings.append(
            {
                "id": "missing_http_listener",
                "severity": "high",
                "summary": "ALB has no HTTP listener on port 80.",
                "evidence": {"listener_ports": sorted(listeners_by_port.keys())},
            }
        )

    expected_hosts_lc = [host.lower() for host in expected_hosts]
    host_rules: dict[str, list[dict[str, Any]]] = {}
    for listener in listeners:
        listener_arn = listener.get("ListenerArn", "")
        for rule in rules_by_listener.get(listener_arn, []):
            for host_value in _extract_host_condition_values(rule):
                host_rules.setdefault(host_value, []).append(
                    {
                        "listener_arn": listener_arn,
                        "priority": rule.get("Priority"),
                        "actions": rule.get("Actions") or [],
                    }
                )

    missing_host_rules = [host for host in expected_hosts_lc if host not in host_rules]
    if missing_host_rules:
        findings.append(
            {
                "id": "host_routing_incomplete",
                "severity": "critical",
                "summary": "Expected host-header routing rules are missing.",
                "evidence": {
                    "missing_hosts": missing_host_rules,
                    "configured_host_rules": sorted(host_rules.keys()),
                },
            }
        )

    tg_summaries: dict[str, dict[str, Any]] = {}
    total_healthy_targets = 0
    for tg in target_groups:
        tg_arn = tg.get("TargetGroupArn", "")
        entries = target_health.get(tg_arn, [])
        health = _summarize_target_health(entries)
        total_healthy_targets += health["healthy"]
        tg_summaries[tg_arn] = {
            "target_group_name": tg.get("TargetGroupName"),
            "target_group_arn": tg_arn,
            "health": health,
            "health_check_path": tg.get("HealthCheckPath"),
            "port": tg.get("Port"),
            "protocol": tg.get("Protocol"),
        }

    if not target_groups:
        findings.append(
            {
                "id": "no_target_groups",
                "severity": "critical",
                "summary": "ALB has no attached target groups.",
                "evidence": {},
            }
        )
    elif total_healthy_targets == 0:
        findings.append(
            {
                "id": "no_healthy_targets",
                "severity": "critical",
                "summary": "No healthy registered targets found in ALB target groups.",
                "evidence": {
                    "target_group_health": tg_summaries,
                },
            }
        )

    if len(target_groups) < 2:
        findings.append(
            {
                "id": "single_target_group_only",
                "severity": "high",
                "summary": "ALB currently has fewer than two target groups; API/UI split routing likely incomplete.",
                "evidence": {
                    "target_group_names": [tg.get("TargetGroupName") for tg in target_groups],
                    "count": len(target_groups),
                },
            }
        )

    allows_https_ingress = False
    for sg in security_groups:
        for perm in sg.get("IpPermissions") or []:
            if (
                perm.get("IpProtocol") == "tcp"
                and int(perm.get("FromPort") or -1) <= 443 <= int(perm.get("ToPort") or -1)
            ):
                cidrs = [item.get("CidrIp") for item in (perm.get("IpRanges") or []) if item.get("CidrIp")]
                if "0.0.0.0/0" in cidrs:
                    allows_https_ingress = True
                    break
        if allows_https_ingress:
            break

    if not allows_https_ingress:
        findings.append(
            {
                "id": "https_ingress_not_open",
                "severity": "high",
                "summary": "No SG ingress rule found for TCP/443 from 0.0.0.0/0.",
                "evidence": {
                    "security_group_ids": [sg.get("GroupId") for sg in security_groups],
                },
            }
        )

    nacl_summaries = [_summarize_network_acl(nacl) for nacl in network_acls]
    if nacl_summaries:
        allows_443 = any(item.get("ingress_tcp_443") is True for item in nacl_summaries)
        if not allows_443:
            findings.append(
                {
                    "id": "nacl_ingress_443_not_allowed",
                    "severity": "high",
                    "summary": "No associated NACL allows inbound TCP/443 from public CIDR.",
                    "evidence": {
                        "network_acls": nacl_summaries,
                    },
                }
            )

        allows_ephemeral_egress = any(item.get("egress_tcp_32768") is True for item in nacl_summaries)
        if not allows_ephemeral_egress:
            findings.append(
                {
                    "id": "nacl_egress_ephemeral_not_allowed",
                    "severity": "medium",
                    "summary": "Associated NACLs do not expose explicit ephemeral egress allow rule (TCP/32768).",
                    "evidence": {
                        "network_acls": nacl_summaries,
                    },
                }
            )

    severity_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    max_severity = max((severity_rank.get(item["severity"], 0) for item in findings), default=0)
    if max_severity >= 3:
        overall = "fail"
    elif max_severity >= 2:
        overall = "warn"
    else:
        overall = "pass"

    fix_plan: list[str] = []
    finding_ids = {item["id"] for item in findings}
    if "missing_https_listener" in finding_ids:
        fix_plan.append(
            "Create HTTPS listener (443) on swisstopo-dev-vpc-alb and bind ACM certificate/SANs for api/www on both dev domains."
        )
    if "host_routing_incomplete" in finding_ids:
        fix_plan.append(
            "Add host-header listener rules for api.dev.georanking.ch, api.dev.geo-ranking.ch, www.dev.georanking.ch and www.dev.geo-ranking.ch with explicit API/UI target-group actions."
        )
    if "no_healthy_targets" in finding_ids or "single_target_group_only" in finding_ids:
        fix_plan.append(
            "Attach running ECS task IP targets to API/UI target groups, verify health checks, and ensure ECS services stay registered after deployment."
        )
    if "nacl_ingress_443_not_allowed" in finding_ids or "nacl_egress_ephemeral_not_allowed" in finding_ids:
        fix_plan.append(
            "Validate associated subnet NACLs for ALB-facing subnets and ensure required ingress/egress rules for HTTPS + return traffic are present."
        )

    return {
        "overall": overall,
        "findings": findings,
        "fix_plan": fix_plan,
        "derived": {
            "listener_ports": sorted(listeners_by_port.keys()),
            "host_rules": sorted(host_rules.keys()),
            "target_group_count": len(target_groups),
            "target_group_health": tg_summaries,
            "network_acls": nacl_summaries,
        },
    }


def _probe_once(
    url: str,
    timeout_seconds: float,
    *,
    host_header: str | None = None,
    insecure_tls: bool = False,
) -> dict[str, Any]:
    req = request.Request(url=url, method="GET")
    if host_header:
        req.add_header("Host", host_header)

    context = None
    if insecure_tls and url.startswith("https://"):
        context = ssl._create_unverified_context()  # noqa: SLF001

    try:
        with request.urlopen(req, timeout=timeout_seconds, context=context) as resp:
            return {
                "url": url,
                "status": int(resp.status),
                "ok": 200 <= int(resp.status) < 400,
                "error": None,
                "host_header": host_header,
            }
    except error.HTTPError as exc:
        return {
            "url": url,
            "status": int(exc.code),
            "ok": False,
            "error": f"http_error:{exc.code}",
            "host_header": host_header,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "url": url,
            "status": None,
            "ok": False,
            "error": f"request_failed:{exc}",
            "host_header": host_header,
        }


def collect_external_probes(expected_hosts: list[str], timeout_seconds: float) -> list[dict[str, Any]]:
    probes: list[dict[str, Any]] = []
    for host in expected_hosts:
        path = "/health" if host.startswith("api.") else "/"
        probes.append(_probe_once(f"https://{host}{path}", timeout_seconds))
        probes.append(_probe_once(f"http://{host}{path}", timeout_seconds))
    return probes


def collect_direct_alb_probes(
    lb_dns_name: str,
    expected_hosts: list[str],
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    probes: list[dict[str, Any]] = []
    if not lb_dns_name:
        return probes

    for host in expected_hosts:
        path = "/health" if host.startswith("api.") else "/"
        probes.append(
            _probe_once(
                f"http://{lb_dns_name}{path}",
                timeout_seconds,
                host_header=host,
                insecure_tls=False,
            )
        )
        probes.append(
            _probe_once(
                f"https://{lb_dns_name}{path}",
                timeout_seconds,
                host_header=host,
                insecure_tls=True,
            )
        )
    return probes


def _parse_expected_hosts(args: argparse.Namespace) -> list[str]:
    values: list[str] = []
    for item in args.expected_host:
        values.extend(part.strip() for part in item.split(",") if part.strip())
    if values:
        return values
    return list(DEFAULT_EXPECTED_HOSTS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Collect ALB runtime evidence for dev frontdoor outages and derive a minimal fix plan."
        )
    )
    parser.add_argument("--lb-name", default="swisstopo-dev-vpc-alb", help="ALB name in AWS")
    parser.add_argument("--region", default="eu-central-1", help="AWS region")
    parser.add_argument(
        "--expected-host",
        action="append",
        default=[],
        help="Expected hostnames (repeatable or comma-separated).",
    )
    parser.add_argument("--timeout-seconds", type=float, default=6.0)
    parser.add_argument("--output-json", required=True)
    parser.add_argument(
        "--snapshot-file",
        default="",
        help="Optional existing snapshot JSON (skips live AWS collection).",
    )
    parser.add_argument(
        "--skip-probes",
        action="store_true",
        help="Skip external and ALB-direct HTTP/HTTPS probes.",
    )

    args = parser.parse_args(argv)
    if args.timeout_seconds <= 0:
        print("timeout-seconds must be > 0", file=sys.stderr)
        return 2

    expected_hosts = _parse_expected_hosts(args)

    try:
        if args.snapshot_file:
            snapshot_path = Path(args.snapshot_file)
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            snapshot_source = f"file:{snapshot_path}"
        else:
            snapshot = collect_live_snapshot(lb_name=args.lb_name, region=args.region)
            snapshot_source = "aws-live"
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to collect snapshot: {exc}", file=sys.stderr)
        return 1

    analysis = analyze_snapshot(snapshot=snapshot, expected_hosts=expected_hosts)
    if args.skip_probes:
        probes = []
        direct_alb_probes = []
    else:
        probes = collect_external_probes(expected_hosts, timeout_seconds=args.timeout_seconds)
        lb_dns_name = ((snapshot.get("load_balancer") or {}).get("DNSName") or "").strip()
        direct_alb_probes = collect_direct_alb_probes(
            lb_dns_name=lb_dns_name,
            expected_hosts=expected_hosts,
            timeout_seconds=args.timeout_seconds,
        )

    payload = {
        "generated_at": _utc_now(),
        "inputs": {
            "lb_name": args.lb_name,
            "region": args.region,
            "expected_hosts": expected_hosts,
            "snapshot_source": snapshot_source,
        },
        "external_probes": probes,
        "direct_alb_probes": direct_alb_probes,
        "analysis": analysis,
        "snapshot": snapshot,
    }

    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print(f"Wrote outage analysis: {output_path}")
    return 1 if analysis.get("overall") == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
