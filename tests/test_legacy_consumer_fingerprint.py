from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.legacy_consumer_fingerprint import (
    build_fingerprint_report,
    extract_records_from_lookup_page,
    load_ndjson_records,
    normalize_lookup_event,
    render_report_lines,
)


class TestLegacyConsumerFingerprintModule(unittest.TestCase):
    def test_normalize_lookup_event_keeps_expected_fields(self) -> None:
        payload = {
            "EventTime": "2026-02-26T20:00:00Z",
            "EventName": "GetCallerIdentity",
            "EventSource": "sts.amazonaws.com",
            "Username": "swisstopo-api-deploy",
            "CloudTrailEvent": json.dumps(
                {
                    "eventTime": "2026-02-26T20:00:00Z",
                    "eventName": "GetCallerIdentity",
                    "eventSource": "sts.amazonaws.com",
                    "sourceIPAddress": "76.13.144.185",
                    "userAgent": "aws-cli/2.33.29",
                    "recipientAccountId": "523234426229",
                    "awsRegion": "eu-central-1",
                    "userIdentity": {
                        "userName": "swisstopo-api-deploy",
                        "accountId": "523234426229",
                    },
                }
            ),
        }

        record = normalize_lookup_event(payload)

        self.assertEqual(record["event_source"], "sts.amazonaws.com")
        self.assertEqual(record["source_ip"], "76.13.144.185")
        self.assertEqual(record["user_agent"], "aws-cli/2.33.29")
        self.assertEqual(record["recipient_account"], "523234426229")
        self.assertEqual(record["region"], "eu-central-1")

    def test_extract_records_from_lookup_page_handles_token(self) -> None:
        page = {
            "Events": [
                {
                    "EventTime": "2026-02-26T20:00:00Z",
                    "EventName": "GetCallerIdentity",
                    "EventSource": "sts.amazonaws.com",
                    "CloudTrailEvent": "{}",
                }
            ],
            "NextToken": "abc-123",
        }

        records, token = extract_records_from_lookup_page(page)
        self.assertEqual(token, "abc-123")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["event_name"], "GetCallerIdentity")

    def test_load_ndjson_records_skips_invalid_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text('{"a":1}\nnot-json\n[1,2]\n{"b":2}\n', encoding="utf-8")
            records, invalid = load_ndjson_records(path)

        self.assertEqual(len(records), 2)
        self.assertEqual(invalid, 2)

    def test_build_report_is_deterministic_for_ties(self) -> None:
        records = [
            {
                "event_time": "2026-02-26T20:00:01Z",
                "event_name": "A",
                "event_source": "service.example",
                "source_ip": "9.9.9.9",
                "user_agent": "ua-z",
                "recipient_account": "acc-2",
                "username": "u",
                "region": "eu-central-1",
            },
            {
                "event_time": "2026-02-26T20:00:02Z",
                "event_name": "B",
                "event_source": "service.example",
                "source_ip": "1.1.1.1",
                "user_agent": "ua-a",
                "recipient_account": "acc-1",
                "username": "u",
                "region": "eu-central-1",
            },
        ]

        report = build_fingerprint_report(
            records,
            start_time="2026-02-26T14:00:00Z",
            end_time="2026-02-26T20:00:00Z",
            lookback_hours=6,
            legacy_user="swisstopo-api-deploy",
            region="eu-central-1",
            max_results=50,
            max_pages=20,
            pages_read=1,
            include_lookup_events=True,
            include_region=False,
            include_account=False,
        )

        self.assertEqual(report["status"], "found_events")
        # Tie on count=1 must be sorted lexicographically by fingerprint key.
        self.assertEqual(report["top_fingerprints"][0]["source_ip"], "1.1.1.1")
        self.assertEqual(report["top_fingerprints"][1]["source_ip"], "9.9.9.9")

    def test_report_can_include_region_and_account_dimensions(self) -> None:
        records = [
            {
                "event_time": "2026-02-26T20:00:00Z",
                "event_name": "GetCallerIdentity",
                "event_source": "sts.amazonaws.com",
                "source_ip": "76.13.144.185",
                "user_agent": "aws-cli/2.33.29",
                "recipient_account": "523234426229",
                "username": "swisstopo-api-deploy",
                "region": "eu-central-1",
            }
        ]

        report = build_fingerprint_report(
            records,
            start_time="2026-02-26T14:00:00Z",
            end_time="2026-02-26T20:00:00Z",
            lookback_hours=6,
            legacy_user="swisstopo-api-deploy",
            region="eu-central-1",
            max_results=50,
            max_pages=20,
            pages_read=1,
            include_lookup_events=True,
            include_region=True,
            include_account=True,
        )

        self.assertEqual(
            report["config"]["fingerprint_dimensions"],
            ["source_ip", "user_agent", "region", "recipient_account"],
        )
        self.assertEqual(report["top_fingerprints"][0]["region"], "eu-central-1")
        self.assertEqual(report["top_fingerprints"][0]["recipient_account"], "523234426229")

        lines = render_report_lines(report)
        self.assertTrue(any("Top Fingerprints (source_ip + user_agent + region + recipient_account):" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
