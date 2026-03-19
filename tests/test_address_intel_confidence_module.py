import unittest

from src.api import address_intel
from src.api.address_intel_confidence import (
    assess_ambiguity as assess_ambiguity_impl,
    compute_confidence as compute_confidence_impl,
)


class TestAddressIntelConfidenceModule(unittest.TestCase):
    def test_assess_ambiguity_wrapper_matches_extracted_impl(self):
        selected = address_intel.CandidateEval(
            feature_id="a",
            label="A",
            detail="",
            origin="address",
            rank=1,
            lat=None,
            lon=None,
            pre_score=40,
            total_score=62,
            pre_reasons=["Strasse exakt im Treffertext"],
            detail_reasons=["GWR-Strasse bestätigt"],
            gwr_attrs={"plz_plz6": 8001, "dplzname": "Zürich", "gdekt": "ZH"},
            address_attrs={},
        )
        close = address_intel.CandidateEval(
            feature_id="b",
            label="B",
            detail="",
            origin="address",
            rank=2,
            lat=None,
            lon=None,
            pre_score=59,
            total_score=59,
            gwr_attrs={},
            address_attrs={},
        )

        wrapped = address_intel.assess_ambiguity(selected, [selected, close])
        extracted = assess_ambiguity_impl(selected, [selected, close])
        self.assertEqual(wrapped, extracted)

    def test_compute_confidence_wrapper_matches_extracted_impl(self):
        sources = address_intel.SourceRegistry()
        sources.note_success("geoadmin_search", "https://example")
        sources.note_success("geoadmin_gwr", "https://example")
        sources.note_success("geoadmin_address", "https://example")

        selected = address_intel.CandidateEval(
            feature_id="111_0",
            label="Test 1",
            detail="",
            origin="address",
            rank=1,
            lat=47.0,
            lon=8.0,
            pre_score=50,
            total_score=95,
            address_attrs={"adr_official": True},
            gwr_attrs={
                "egid": 1,
                "egrid": "CH1",
                "esid": 22,
                "gstat": 1004,
                "gbauj": 1999,
                "garea": 100,
                "gastw": 4,
                "ganzwhg": 8,
                "plz_plz6": 9000,
                "dplzname": "St. Gallen",
                "ggdename": "St. Gallen",
                "gdekt": "SG",
            },
        )

        kwargs = dict(
            selected=selected,
            candidates=[selected],
            sources=sources,
            heating_layer={"genh1_de": "Fernwärme"},
            plz_layer={"plz": 9000, "langtext": "St. Gallen"},
            admin_boundary={"gemname": "St. Gallen", "kanton": "SG"},
            osm={"address": {"postcode": "9000", "city": "St. Gallen"}},
        )

        wrapped = address_intel.compute_confidence(**kwargs)
        extracted = compute_confidence_impl(
            **kwargs,
            normalize_text_fn=address_intel.normalize_text,
            clamp_fn=address_intel.clamp,
            required_sources=address_intel._REQUIRED_SOURCES,
        )
        self.assertEqual(wrapped, extracted)


if __name__ == "__main__":
    unittest.main()
