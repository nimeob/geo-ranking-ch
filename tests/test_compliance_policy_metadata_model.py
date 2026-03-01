import unittest

from src.compliance.policy_metadata import PolicyMetadataV1, validate_policy_metadata


class TestCompliancePolicyMetadataModel(unittest.TestCase):
    def test_from_dict_accepts_valid_payload_and_normalizes(self):
        payload = {
            "policy_id": "POL-RETDEL-001",
            "version": "v1.0",
            "begruendung": "Regulatorische Mindestanforderungen konsolidiert",
            "wirksam_ab": "2026-03-01",
            "impact_referenz": "https://github.com/nimeob/geo-ranking-ch/issues/519",
        }

        model = PolicyMetadataV1.from_dict(payload)

        self.assertEqual(model.policy_id, "POL-RETDEL-001")
        self.assertEqual(model.version, "v1.0")
        self.assertEqual(model.wirksam_ab.isoformat(), "2026-03-01")
        self.assertEqual(
            model.to_dict(),
            {
                "policy_id": "POL-RETDEL-001",
                "version": "v1.0",
                "begruendung": "Regulatorische Mindestanforderungen konsolidiert",
                "wirksam_ab": "2026-03-01",
                "impact_referenz": "https://github.com/nimeob/geo-ranking-ch/issues/519",
            },
        )

    def test_validate_policy_metadata_rejects_missing_required_field(self):
        payload = {
            "policy_id": "POL-RETDEL-001",
            "version": "v1.0",
            "begruendung": "ok",
            "wirksam_ab": "2026-03-01",
        }

        with self.assertRaisesRegex(ValueError, "missing required field: impact_referenz"):
            validate_policy_metadata(payload)

    def test_validate_policy_metadata_rejects_invalid_version(self):
        payload = {
            "policy_id": "POL-RETDEL-001",
            "version": "1.0",
            "begruendung": "ok",
            "wirksam_ab": "2026-03-01",
            "impact_referenz": "#519",
        }

        with self.assertRaisesRegex(ValueError, "version must match"):
            validate_policy_metadata(payload)

    def test_validate_policy_metadata_rejects_invalid_wirksam_ab_format(self):
        payload = {
            "policy_id": "POL-RETDEL-001",
            "version": "v1.0",
            "begruendung": "ok",
            "wirksam_ab": "01-03-2026",
            "impact_referenz": "issue:519",
        }

        with self.assertRaisesRegex(ValueError, "wirksam_ab must be an ISO date"):
            validate_policy_metadata(payload)

    def test_validate_policy_metadata_rejects_empty_impact_reference(self):
        payload = {
            "policy_id": "POL-RETDEL-001",
            "version": "v1.0",
            "begruendung": "ok",
            "wirksam_ab": "2026-03-01",
            "impact_referenz": " ",
        }

        with self.assertRaisesRegex(ValueError, "impact_referenz must be a non-empty string"):
            validate_policy_metadata(payload)


if __name__ == "__main__":
    unittest.main()
