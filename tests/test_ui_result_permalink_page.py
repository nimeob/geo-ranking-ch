from __future__ import annotations

from src.ui.service import _build_result_permalink_html, _normalize_result_id


def test_normalize_result_id_rejects_empty_or_slashes() -> None:
    assert _normalize_result_id("") == ""
    assert _normalize_result_id("  ") == ""
    assert _normalize_result_id("res/123") == ""


def test_normalize_result_id_accepts_reasonable_ids() -> None:
    assert _normalize_result_id("res-123") == "res-123"
    assert _normalize_result_id("Res_123") == "Res_123"


def test_build_result_permalink_html_uses_relative_api_when_base_is_empty() -> None:
    html = _build_result_permalink_html(app_version="test", api_base_url="", result_id="res-123")
    assert "res-123" in html
    assert 'const RESULTS_ENDPOINT_BASE = "/analyze/results";' in html
    assert "Overview" in html
    assert "Sources / Evidence" in html
    assert "Generated / Derived" in html
    assert "Raw JSON" in html


def test_build_result_permalink_html_injects_api_base_url() -> None:
    html = _build_result_permalink_html(
        app_version="test",
        api_base_url="https://api.example.test/",
        result_id="res-123",
    )
    assert 'const RESULTS_ENDPOINT_BASE = "https://api.example.test/analyze/results";' in html
