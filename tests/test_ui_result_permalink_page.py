from __future__ import annotations

import pytest

from src.ui.service import _build_result_permalink_html, _normalize_result_id


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("res-123", "res-123"),
        ("550e8400-e29b-41d4-a716-446655440000", "550e8400-e29b-41d4-a716-446655440000"),
        (" RES_1 ", "RES_1"),
        ("a.b_c-d", "a.b_c-d"),
    ],
)
def test_normalize_result_id_accepts_safe_values(raw: str, expected: str) -> None:
    assert _normalize_result_id(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        " ",
        "/",
        "../etc/passwd",
        "a/b",
        "<script>",
        "x" * 2048,
        "has space",
    ],
)
def test_normalize_result_id_rejects_unsafe_values(raw: str) -> None:
    assert _normalize_result_id(raw) == ""


def test_build_result_permalink_html_uses_relative_api_when_base_is_empty() -> None:
    html = _build_result_permalink_html(app_version="test", api_base_url="", result_id="res-123")
    assert "RESULT_ID" in html
    assert "res-123" in html
    assert 'const RESULTS_ENDPOINT_BASE = "/analyze/results";' in html


def test_build_result_permalink_html_injects_api_base_url() -> None:
    html = _build_result_permalink_html(
        app_version="test",
        api_base_url="https://api.example.test/",
        result_id="res-123",
    )
    assert 'const RESULTS_ENDPOINT_BASE = "https://api.example.test/analyze/results";' in html


def test_build_result_permalink_html_rejects_invalid_result_id() -> None:
    with pytest.raises(ValueError):
        _build_result_permalink_html(app_version="test", api_base_url="", result_id="a/b")
