"""Small geometry helpers for working with latitude/longitude points."""

import math
from typing import NamedTuple

EARTH_RADIUS_MILES = 3958.7613


class LatLon(NamedTuple):
    """A point on Earth in decimal degrees.

    Note: GeoJSON and most map libraries use the opposite order, [lon, lat].
    """

    lat: float
    lon: float


def haversine_miles(a: LatLon, b: LatLon) -> float:
    """Great-circle ("as the crow flies") distance between two points, in miles."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a.lat, a.lon, b.lat, b.lon))
    d_lat = lat2 - lat1
    d_lon = lon2 - lon1

    h = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(h))


def interpolate(a: LatLon, b: LatLon, fraction: float) -> LatLon:
    """The point `fraction` (0..1) of the way from a to b.

    A straight-line blend of the coordinates. Route polylines have points every
    few hundred metres, so the error over one segment is negligible.
    """
    return LatLon(
        lat=a.lat + (b.lat - a.lat) * fraction,
        lon=a.lon + (b.lon - a.lon) * fraction,
    )
