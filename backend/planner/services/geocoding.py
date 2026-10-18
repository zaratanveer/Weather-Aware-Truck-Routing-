"""
Place search for the origin / destination autocomplete.

Default: Photon (photon.komoot.io), a free OpenStreetMap geocoder built for
search-as-you-type. (Nominatim's usage policy forbids autocomplete.)
If MAPBOX_TOKEN is set, Mapbox's geocoding API is used instead.
"""

from dataclasses import dataclass
from typing import Any

from django.conf import settings

from ..logic.geo import LatLon
from .http import get_json

PHOTON_URL = "https://photon.komoot.io/api/"
MAPBOX_GEOCODING_URL = "https://api.mapbox.com/search/geocode/v6/forward"


@dataclass(frozen=True)
class Place:
    label: str  # e.g. "Springfield, Illinois, United States"
    location: LatLon


def search_places(query: str, limit: int = 5) -> list[Place]:
    """Places matching `query`, best match first."""
    if settings.MAPBOX_TOKEN:
        return _search_mapbox(query, limit)
    return _search_photon(query, limit)


def _search_photon(query: str, limit: int) -> list[Place]:
    data = get_json(PHOTON_URL, {"q": query, "limit": limit, "lang": "en"}, "Place search")
    return [_place_from_photon(feature) for feature in data.get("features", [])]


def _place_from_photon(feature: dict[str, Any]) -> Place:
    props = feature["properties"]
    lon, lat = feature["geometry"]["coordinates"]

    parts: list[str] = []
    for key in ("name", "city", "state", "country"):
        value = props.get(key)
        if value and value not in parts:  # skip "Dallas, Dallas, ..."
            parts.append(value)
    return Place(label=", ".join(parts), location=LatLon(lat, lon))


def _search_mapbox(query: str, limit: int) -> list[Place]:
    params = {
        "q": query,
        "limit": limit,
        "autocomplete": "true",
        "access_token": settings.MAPBOX_TOKEN,
    }
    data = get_json(MAPBOX_GEOCODING_URL, params, "Place search")
    return [_place_from_mapbox(feature) for feature in data.get("features", [])]


def _place_from_mapbox(feature: dict[str, Any]) -> Place:
    props = feature["properties"]
    lon, lat = feature["geometry"]["coordinates"]
    label = props.get("full_address") or props.get("name", "")
    return Place(label=label, location=LatLon(lat, lon))
