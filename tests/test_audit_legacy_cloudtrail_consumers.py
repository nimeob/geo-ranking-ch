from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "audit_legacy_cloudtrail_consumers.sh"


class TestAuditLegacyCloudTrailConsumersScript(unittest.TestCase):
    def _run_with_mocked_aws(
        self,
        payload: dict,
        *,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bin_dir = tmp_path / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)

            response_file = tmp_path / "aws-response.json"
            response_file.write_text(json.dumps(payload), encoding="utf-8")

            mock_aws = bin_dir / "aws"
            mock_aws.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "cat \"${MOCK_AWS_RESPONSE_FILE:?}\"\n",
                encoding="utf-8",
            )
            mock_aws.chmod(mock_aws.stat().st_mode | stat.S_IXUSR)

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env['PATH']}"
            env["MOCK_AWS_RESPONSE_FILE"] = str(response_file)
            if env_overrides:
                env.update(env_overrides)

            return subprocess.run(
                ["bash", str(SCRIPT)],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_rejects_invalid_lookback_hours(self) -> None:
        env = os.environ.copy()
        env["LOOKBACK_HOURS"] = "0"

        result = subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 20)
        self.assertIn("LOOKBACK_HOURS", result.stderr)

    def test_returns_zero_when_no_events_found(self) -> None:
        result = self._run_with_mocked_aws({"Events": []})

        self.assertEqual(result.returncode, 0)
        self.assertIn("Keine Legacy-CloudTrail-Events", result.stdout)

    def test_returns_ten_and_prints_fingerprint_when_events_exist(self) -> None:
        cloudtrail_event = {
            "eventTime": "2026-02-26T20:00:00Z",
            "eventName": "GetCallerIdentity",
            "eventSource": "sts.amazonaws.com",
            "sourceIPAddress": "76.13.144.185",
            "userAgent": "aws-cli/2.33.29",
            "recipientAccountId": "523234426229",
            "userIdentity": {
                "userName": "swisstopo-api-deploy",
                "accountId": "523234426229",
            },
        }
        payload = {
            "Events": [
                {
                    "EventTime": "2026-02-26T20:00:00Z",
                    "EventName": "GetCallerIdentity",
                    "EventSource": "sts.amazonaws.com",
                    "Username": "swisstopo-api-deploy",
                    "CloudTrailEvent": json.dumps(cloudtrail_event),
                }
            ]
        }

        result = self._run_with_mocked_aws(payload)

        self.assertEqual(result.returncode, 10)
        self.assertIn("Top Fingerprints", result.stdout)
        self.assertIn("source_ip=76.13.144.185", result.stdout)

    def test_lookup_events_are_filtered_by_default_but_includable(self) -> None:
        lookup_detail = {
            "eventTime": "2026-02-26T20:00:00Z",
            "eventName": "LookupEvents",
            "eventSource": "cloudtrail.amazonaws.com",
            "sourceIPAddress": "76.13.144.185",
            "userAgent": "aws-cli/2.33.29",
            "recipientAccountId": "523234426229",
            "userIdentity": {
                "userName": "swisstopo-api-deploy",
                "accountId": "523234426229",
            },
        }
        payload = {
            "Events": [
                {
                    "EventTime": "2026-02-26T20:00:00Z",
                    "EventName": "LookupEvents",
                    "EventSource": "cloudtrail.amazonaws.com",
                    "Username": "swisstopo-api-deploy",
                    "CloudTrailEvent": json.dumps(lookup_detail),
                }
            ]
        }

        filtered = self._run_with_mocked_aws(payload)
        included = self._run_with_mocked_aws(payload, env_overrides={"INCLUDE_LOOKUP_EVENTS": "1"})

        self.assertEqual(filtered.returncode, 0)
        self.assertIn("Keine Legacy-CloudTrail-Events", filtered.stdout)

        self.assertEqual(included.returncode, 10)
        self.assertIn("LookupEvents in Auswertung: inkludiert", included.stdout)
        self.assertIn("cloudtrail.amazonaws.com", included.stdout)


if __name__ == "__main__":
    unittest.main()
