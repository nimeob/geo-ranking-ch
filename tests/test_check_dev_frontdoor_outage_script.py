import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_dev_frontdoor_outage.py"


class TestCheckDevFrontdoorOutageScript(unittest.TestCase):
    def _run_with_snapshot(self, snapshot: dict) -> tuple[subprocess.CompletedProcess[str], dict]:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            snapshot_path = tmp / "snapshot.json"
            output_path = tmp / "out.json"
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
            cp = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--snapshot-file",
                    str(snapshot_path),
                    "--output-json",
                    str(output_path),
                    "--skip-probes",
                ],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            return cp, payload

    def test_detects_missing_https_and_unhealthy_targets(self):
        snapshot = {
            "load_balancer": {
                "LoadBalancerArn": "arn:alb:test",
                "SecurityGroups": ["sg-1"],
            },
            "listeners": [
                {
                    "Port": 80,
                    "ListenerArn": "arn:listener:http",
                    "Protocol": "HTTP",
                }
            ],
            "rules_by_listener": {
                "arn:listener:http": [
                    {
                        "Priority": "default",
                        "Conditions": [],
                        "Actions": [],
                    }
                ]
            },
            "target_groups": [
                {
                    "TargetGroupArn": "arn:tg:api",
                    "TargetGroupName": "api",
                    "Port": 8080,
                    "Protocol": "HTTP",
                    "HealthCheckPath": "/health",
                }
            ],
            "target_health": {
                "arn:tg:api": [],
            },
            "security_groups": [
                {
                    "GroupId": "sg-1",
                    "IpPermissions": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 80,
                            "ToPort": 80,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        },
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 443,
                            "ToPort": 443,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        },
                    ],
                }
            ],
        }

        cp, payload = self._run_with_snapshot(snapshot)
        self.assertEqual(cp.returncode, 1, msg=cp.stdout + cp.stderr)
        self.assertEqual(payload["analysis"]["overall"], "fail")
        ids = {item["id"] for item in payload["analysis"]["findings"]}
        self.assertIn("missing_https_listener", ids)
        self.assertIn("no_healthy_targets", ids)
        self.assertIn("host_routing_incomplete", ids)

    def test_passes_when_https_host_rules_and_healthy_targets_exist(self):
        snapshot = {
            "load_balancer": {
                "LoadBalancerArn": "arn:alb:test",
                "SecurityGroups": ["sg-1"],
            },
            "listeners": [
                {
                    "Port": 80,
                    "ListenerArn": "arn:listener:http",
                    "Protocol": "HTTP",
                },
                {
                    "Port": 443,
                    "ListenerArn": "arn:listener:https",
                    "Protocol": "HTTPS",
                },
            ],
            "rules_by_listener": {
                "arn:listener:http": [
                    {
                        "Priority": "10",
                        "Conditions": [
                            {
                                "Field": "host-header",
                                "HostHeaderConfig": {
                                    "Values": [
                                        "api.dev.georanking.ch",
                                        "api.dev.geo-ranking.ch",
                                        "www.dev.georanking.ch",
                                        "www.dev.geo-ranking.ch",
                                    ]
                                },
                            }
                        ],
                        "Actions": [],
                    }
                ],
                "arn:listener:https": [
                    {
                        "Priority": "10",
                        "Conditions": [
                            {
                                "Field": "host-header",
                                "HostHeaderConfig": {
                                    "Values": [
                                        "api.dev.georanking.ch",
                                        "api.dev.geo-ranking.ch",
                                        "www.dev.georanking.ch",
                                        "www.dev.geo-ranking.ch",
                                    ]
                                },
                            }
                        ],
                        "Actions": [],
                    }
                ],
            },
            "target_groups": [
                {
                    "TargetGroupArn": "arn:tg:api",
                    "TargetGroupName": "api",
                    "Port": 8080,
                    "Protocol": "HTTP",
                    "HealthCheckPath": "/health",
                },
                {
                    "TargetGroupArn": "arn:tg:ui",
                    "TargetGroupName": "ui",
                    "Port": 8081,
                    "Protocol": "HTTP",
                    "HealthCheckPath": "/healthz",
                },
            ],
            "target_health": {
                "arn:tg:api": [
                    {"TargetHealth": {"State": "healthy"}},
                ],
                "arn:tg:ui": [
                    {"TargetHealth": {"State": "healthy"}},
                ],
            },
            "security_groups": [
                {
                    "GroupId": "sg-1",
                    "IpPermissions": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 80,
                            "ToPort": 80,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        },
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 443,
                            "ToPort": 443,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        },
                    ],
                }
            ],
        }

        cp, payload = self._run_with_snapshot(snapshot)
        self.assertEqual(cp.returncode, 0, msg=cp.stdout + cp.stderr)
        self.assertEqual(payload["analysis"]["overall"], "pass")
        self.assertEqual(payload["analysis"]["findings"], [])


if __name__ == "__main__":
    unittest.main()
