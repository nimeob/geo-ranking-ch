from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path("scripts/reconcile_dev_alb_listener_rules.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("reconcile_dev_alb_listener_rules", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _FakeAws:
    def __init__(self, *, rules_by_listener: dict[str, list[dict]], listeners: list[dict] | None = None) -> None:
        self._lb_arn = "arn:aws:elasticloadbalancing:eu-central-1:123456789012:loadbalancer/app/dev/abc"
        self._listeners = listeners or [
            {"Port": 80, "ListenerArn": "listener-80"},
            {"Port": 443, "ListenerArn": "listener-443"},
        ]
        self._rules_by_listener = rules_by_listener
        self.delete_calls: list[list[str]] = []

    def json(self, args: list[str], *, region: str):  # noqa: ARG002
        if args[:3] == ["elbv2", "describe-load-balancers", "--names"]:
            return {"LoadBalancers": [{"LoadBalancerArn": self._lb_arn}]}
        if args[:3] == ["elbv2", "describe-listeners", "--load-balancer-arn"]:
            return {"Listeners": self._listeners}
        if args[:3] == ["elbv2", "describe-rules", "--listener-arn"]:
            listener_arn = args[3]
            return {"Rules": self._rules_by_listener.get(listener_arn, [])}
        raise AssertionError(f"unexpected json call: {args}")

    def call(self, args: list[str], *, region: str):  # noqa: ARG002
        self.delete_calls.append(args)


_UI_FORWARD_RULE = {
    "RuleArn": "rule-ui-forward",
    "Priority": "20",
    "IsDefault": False,
    "Conditions": [
        {
            "Field": "host-header",
            "HostHeaderConfig": {"Values": ["www.dev.georanking.ch", "www.dev.geo-ranking.ch"]},
        }
    ],
    "Actions": [
        {
            "Type": "forward",
            "TargetGroupArn": "arn:aws:elasticloadbalancing:eu-central-1:123:targetgroup/swisstopo-dev-vpc-ui-tg/abc",
        }
    ],
}


def _stale_rule(*, arn: str, priority: str, path: str):
    return {
        "RuleArn": arn,
        "Priority": priority,
        "IsDefault": False,
        "Conditions": [
            {
                "Field": "host-header",
                "HostHeaderConfig": {"Values": ["www.dev.georanking.ch", "www.dev.geo-ranking.ch"]},
            },
            {
                "Field": "path-pattern",
                "PathPatternConfig": {"Values": [path]},
            },
        ],
        "Actions": [{"Type": "redirect", "RedirectConfig": {"Path": "/auth/login", "StatusCode": "HTTP_302"}}],
    }


def test_reconcile_passes_when_ui_forward_exists_and_no_stale_login_redirects():
    module = _load_module()
    aws = _FakeAws(
        rules_by_listener={
            "listener-80": [_UI_FORWARD_RULE],
            "listener-443": [_UI_FORWARD_RULE],
        }
    )

    config = module.Config(
        lb_name="swisstopo-dev-vpc-alb",
        region="eu-central-1",
        required_ports=(80, 443),
        ui_hosts=("www.dev.georanking.ch", "www.dev.geo-ranking.ch"),
        ui_target_group_substring="swisstopo-dev-vpc-ui-tg",
        apply=False,
        output_json="",
    )

    code, payload = module.reconcile(config, aws=aws)

    assert code == 0
    assert payload["overall"]["status"] == "pass"
    assert payload["overall"]["reason"] == "no_drift_detected"
    assert payload["summary"]["stale_rule_count"] == 0
    assert aws.delete_calls == []


def test_reconcile_fails_when_stale_login_redirect_rules_exist_in_check_mode():
    module = _load_module()
    aws = _FakeAws(
        rules_by_listener={
            "listener-80": [_UI_FORWARD_RULE],
            "listener-443": [_UI_FORWARD_RULE, _stale_rule(arn="rule-stale-15", priority="15", path="/login")],
        }
    )

    config = module.Config(
        lb_name="swisstopo-dev-vpc-alb",
        region="eu-central-1",
        required_ports=(80, 443),
        ui_hosts=("www.dev.georanking.ch", "www.dev.geo-ranking.ch"),
        ui_target_group_substring="swisstopo-dev-vpc-ui-tg",
        apply=False,
        output_json="",
    )

    code, payload = module.reconcile(config, aws=aws)

    assert code == 1
    assert payload["overall"]["reason"] == "stale_login_redirect_rules_detected"
    assert payload["summary"]["stale_rule_count"] == 1
    assert payload["stale_rules"][0]["priority"] == "15"
    assert aws.delete_calls == []


def test_reconcile_apply_deletes_stale_login_redirect_rules():
    module = _load_module()
    aws = _FakeAws(
        rules_by_listener={
            "listener-80": [_UI_FORWARD_RULE, _stale_rule(arn="rule-stale-16", priority="16", path="/signin")],
            "listener-443": [_UI_FORWARD_RULE],
        }
    )

    config = module.Config(
        lb_name="swisstopo-dev-vpc-alb",
        region="eu-central-1",
        required_ports=(80, 443),
        ui_hosts=("www.dev.georanking.ch", "www.dev.geo-ranking.ch"),
        ui_target_group_substring="swisstopo-dev-vpc-ui-tg",
        apply=True,
        output_json="",
    )

    code, payload = module.reconcile(config, aws=aws)

    assert code == 0
    assert payload["overall"]["reason"] == "stale_login_redirect_rules_deleted"
    assert payload["summary"]["deleted_rule_count"] == 1
    assert aws.delete_calls == [["elbv2", "delete-rule", "--rule-arn", "rule-stale-16"]]


def test_reconcile_fails_when_ui_forward_rule_missing():
    module = _load_module()
    aws = _FakeAws(
        rules_by_listener={
            "listener-80": [],
            "listener-443": [_UI_FORWARD_RULE],
        }
    )

    config = module.Config(
        lb_name="swisstopo-dev-vpc-alb",
        region="eu-central-1",
        required_ports=(80, 443),
        ui_hosts=("www.dev.georanking.ch", "www.dev.geo-ranking.ch"),
        ui_target_group_substring="swisstopo-dev-vpc-ui-tg",
        apply=True,
        output_json="",
    )

    code, payload = module.reconcile(config, aws=aws)

    assert code == 1
    assert payload["overall"]["reason"] == "missing_ui_host_forward_rule"
    assert payload["summary"]["error_count"] >= 1
    assert aws.delete_calls == []
