"""Tests für geo_utils.py mit Mocking für externe API-Aufrufe."""

import pytest
from unittest.mock import patch, MagicMock
from src.geo_utils import (
    elevation_at,
    wgs84_to_lv95,
    lv95_to_wgs84,
    geocode_ch,
    location_info,
    building_info,
    haversine_km,
    _get,
)

# --- Fixtures für Mocking ---
@pytest.fixture
def mock_get_success():
    """Mock für erfolgreiche API-Antworten."""
    with patch("src.geo_utils._get") as mock:
        mock.return_value = {"height": 1234.5}
        yield mock

@pytest.fixture
def mock_get_wgs84_to_lv95():
    """Mock für WGS84 → LV95 Umrechnung."""
    with patch("src.geo_utils._get") as mock:
        mock.return_value = {"easting": 2600000.0, "northing": 1200000.0}
        yield mock

@pytest.fixture
def mock_get_lv95_to_wgs84():
    """Mock für LV95 → WGS84 Umrechnung."""
    with patch("src.geo_utils._get") as mock:
        mock.return_value = {"northing": 46.8, "easting": 8.3}
        yield mock

@pytest.fixture
def mock_get_geocode():
    """Mock für Geocoding-API."""
    with patch("src.geo_utils._get") as mock:
        mock.return_value = {
            "results": [
                {
                    "attrs": {
                        "label": "Teststrasse 1, 8000 Zürich",
                        "x": 2680000.0,
                        "y": 1240000.0,
                        "postalcode": "8000",
                        "city": "Zürich",
                        "origin": "address",
                        "featureId": "12345",
                    }
                }
            ]
        }
        yield mock

@pytest.fixture
def mock_get_location_info():
    """Mock für Standort-Info-API."""
    with patch("src.geo_utils._get") as mock:
        mock.side_effect = [
            {"easting": 2680000.0, "northing": 1240000.0},  # wgs84_to_lv95
            {
                "results": [
                    {
                        "layerBodId": "ch.swisstopo.swissboundaries3d-gemeinde-flaeche.fill",
                        "attributes": {
                            "gemname": "Zürich",
                            "kanton": "ZH",
                            "gde_nr": "261",
                            "is_current_jahr": True,
                        },
                    },
                    {
                        "layerBodId": "ch.swisstopo.swissboundaries3d-kanton-flaeche.fill",
                        "attributes": {"name": "Zürich", "ak": "ZH"},
                    },
                ]
            },
            {"height": 450.0},  # elevation_at
        ]
        yield mock

@pytest.fixture
def mock_get_building_info():
    """Mock für Gebäude-Info-API."""
    with patch("src.geo_utils._get") as mock:
        mock.side_effect = [
            {  # geocode_ch
                "results": [
                    {
                        "attrs": {
                            "label": "Teststrasse 1, 8000 Zürich",
                            "x": 2680000.0,
                            "y": 1240000.0,
                            "postalcode": "8000",
                            "city": "Zürich",
                            "origin": "address",
                            "featureId": "12345",
                        }
                    }
                ]
            },
            {  # Adressregister
                "feature": {
                    "attributes": {
                        "bdg_egid": "CH123456789",
                        "adr_egaid": "CH987654321",
                        "str_esid": "12345",
                        "bdg_category": "1010",
                        "adr_official": "Teststrasse 1",
                        "adr_modified": "2020-01-01",
                    }
                }
            },
            {  # GWR
                "feature": {
                    "attributes": {
                        "egrid": "CH1234567890",
                        "lparz": "12345",
                        "lgbkr": "ZH",
                        "gbez": "Testgebäude",
                        "gebnr": "1",
                        "gbauj": 2000,
                        "garea": 1000.0,
                        "gastw": 5,
                        "ganzwhg": 10,
                        "gstat": 1004,
                        "gkat": 1010,
                        "gwaerzh1": 7410,
                        "genh1": 7520,
                        "gwaerdath1": "2020-01-01",
                        "gwaerzw1": 7610,
                        "genw1": 7510,
                        "ewid": ["1", "2"],
                        "wstwk": [3102, 3102],
                        "wstat": [3004, 3004],
                        "warea": [100.0, 120.0],
                        "wazim": [3, 4],
                        "wbauj": [2000, 2005],
                    }
                }
            },
        ]
        yield mock

# --- Tests für Koordinaten-Umrechnung ---
def test_wgs84_to_lv95(mock_get_wgs84_to_lv95):
    """Test für WGS84 → LV95 Umrechnung."""
    result = wgs84_to_lv95(46.8, 8.3)
    assert result == (2600000.0, 1200000.0)
    mock_get_wgs84_to_lv95.assert_called_once()

def test_lv95_to_wgs84(mock_get_lv95_to_wgs84):
    """Test für LV95 → WGS84 Umrechnung."""
    result = lv95_to_wgs84(2600000.0, 1200000.0)
    assert result == (46.8, 8.3)
    mock_get_lv95_to_wgs84.assert_called_once()

# --- Tests für Höhe ---
def test_elevation_at_success(mock_get_success):
    """Test für erfolgreiche Höhenabfrage."""
    result = elevation_at(46.8, 8.3)
    assert result == 1234.5
    mock_get_success.assert_called_once()

def test_elevation_at_failure():
    """Test für fehlgeschlagene Höhenabfrage (außerhalb CH)."""
    with patch("src.geo_utils._get") as mock:
        mock.side_effect = Exception("API Error")
        result = elevation_at(0.0, 0.0)
        assert result is None

# --- Tests für Geocoding ---
def test_geocode_ch(mock_get_geocode):
    """Test für Geocoding."""
    results = geocode_ch("Teststrasse 1, Zürich")
    assert len(results) == 1
    assert results[0]["label"] == "Teststrasse 1, 8000 Zürich"
    assert results[0]["city"] == "Zürich"
    assert results[0]["zip_code"] == "8000"
    mock_get_geocode.assert_called_once()

# --- Tests für Standort-Info ---
def test_location_info(mock_get_location_info):
    """Test für Standort-Info."""
    result = location_info(46.8, 8.3)
    assert result["gemeinde"] == "Zürich"
    assert result["kanton"] == "Zürich"
    assert result["kanton_kz"] == "ZH"
    assert result["gde_nr"] == "261"
    assert result["elevation_m"] == 450.0

# --- Tests für Gebäude-Info ---
def test_building_info(mock_get_building_info):
    """Test für Gebäude-Info."""
    result = building_info("Teststrasse 1, 8000 Zürich")
    assert result is not None
    assert result["address"] == "Teststrasse 1, 8000 Zürich"
    assert result["egid"] == "CH123456789"
    assert result["egrid"] == "CH1234567890"
    assert result["gebaeudename"] == "Testgebäude"
    assert result["baujahr"] == 2000
    assert len(result["wohnungen"]) == 2

# --- Tests für Haversine ---
def test_haversine_km():
    """Test für Haversine-Formel."""
    # Zürich (47.3769, 8.5417) → Bern (46.9481, 7.4474) ≈ 120 km
    distance = haversine_km(47.3769, 8.5417, 46.9481, 7.4474)
    assert 115 < distance < 125  # Toleranz für grobe Schätzung