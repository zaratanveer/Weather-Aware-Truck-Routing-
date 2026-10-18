from unittest.mock import Mock

import pytest

from planner.logic.geo import LatLon
from planner.services import geocoding
from planner.services.geocoding import Place, search_places

PHOTON_RESPONSE = {
    "features": [
        {
            "geometry": {"coordinates": [-96.7968, 32.7763]},
            "properties": {"name": "Dallas", "city": "Dallas", "state": "Texas", "country": "United States"},
        },
        {
            "geometry": {"coordinates": [-89.65, 39.80]},
            "properties": {"name": "Springfield", "state": "Illinois", "country": "United States"},
        },
    ]
}

MAPBOX_RESPONSE = {
    "features": [
        {
            "geometry": {"coordinates": [-87.6298, 41.8781]},
            "properties": {"name": "Chicago", "full_address": "Chicago, Illinois, United States"},
        }
    ]
}


@pytest.fixture
def fake_get_json(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Replaces the real HTTP call so tests never touch the network."""
    fake = Mock()
    monkeypatch.setattr(geocoding, "get_json", fake)
    return fake


class TestSearchPlaces:
    def test_photon_results_are_parsed(self, fake_get_json: Mock, settings) -> None:
        settings.MAPBOX_TOKEN = ""
        fake_get_json.return_value = PHOTON_RESPONSE

        places = search_places("dal", limit=2)

        assert places == [
            Place("Dallas, Texas, United States", LatLon(32.7763, -96.7968)),
            Place("Springfield, Illinois, United States", LatLon(39.80, -89.65)),
        ]
        url, params, _ = fake_get_json.call_args.args
        assert url == geocoding.PHOTON_URL
        assert params["q"] == "dal"
        assert params["limit"] == 2

    def test_mapbox_is_used_when_a_token_is_set(self, fake_get_json: Mock, settings) -> None:
        settings.MAPBOX_TOKEN = "test-token"
        fake_get_json.return_value = MAPBOX_RESPONSE

        places = search_places("chic")

        assert places == [Place("Chicago, Illinois, United States", LatLon(41.8781, -87.6298))]
        url, params, _ = fake_get_json.call_args.args
        assert url == geocoding.MAPBOX_GEOCODING_URL
        assert params["access_token"] == "test-token"

    def test_no_matches_gives_empty_list(self, fake_get_json: Mock, settings) -> None:
        settings.MAPBOX_TOKEN = ""
        fake_get_json.return_value = {"features": []}

        assert search_places("zzzz") == []

