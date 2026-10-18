"""
Driving routes between two places, with up to 3 alternatives.

Default: the public OSRM server (router.project-osrm.org), free and key-less.
If MAPBOX_TOKEN is set, Mapbox Directions is used instead. Both return the
same shape: a GeoJSON line plus the driving time of every line segment.

The routing engines often return fewer than 3 routes. When that happens we
ask the same engine for routes forced through a detour point on either side
of the fastest route. These are real drivable routes, labelled as detours,
and are only kept when they are clearly different and not much slower.
"""

import math
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from ..logic.geo import LatLon, haversine_miles
from .http import ExternalServiceError, get_json

OSRM_URL = "https://router.project-osrm.org/route/v1/driving/"
MAPBOX_DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox/driving/"

MAX_ROUTES = 3
# Detour routes: how far to the side the detour point is placed, as a share
# of the straight-line trip distance, and the slowest detour we still offer.
DETOUR_OFFSET_SHARE = 0.15
DETOUR_MAX_SLOWDOWN = 1.5
# Two routes whose distance and duration are both within 1% are the same road.
SAME_ROUTE_TOLERANCE = 0.01

_NO_ROUTE_CODES = {"NoRoute", "NoSegment"}


class NoRouteError(Exception):
    """The routing engine found no drivable road between the two places."""


@dataclass(frozen=True)
class Route:
    points: list[LatLon]
    segment_durations_s: list[float]  # driving time from points[i] to points[i + 1]
    is_detour: bool = False

    @property
    def duration_seconds(self) -> float:
        return sum(self.segment_durations_s)

    @property
    def distance_miles(self) -> float:
        return sum(haversine_miles(a, b) for a, b in zip(self.points, self.points[1:]))


def fetch_routes(origin: LatLon, destination: LatLon) -> list[Route]:
    """Up to MAX_ROUTES distinct driving routes, fastest first."""
    routes = _request_routes([origin, destination], alternatives=True)[:MAX_ROUTES]

    if len(routes) < MAX_ROUTES:
        fastest = routes[0]
        for via in _detour_points(origin, destination):
            if len(routes) >= MAX_ROUTES:
                break
            detour = _try_detour(origin, via, destination)
            if detour and _is_useful_detour(detour, fastest, routes):
                routes.append(detour)
    return routes


def _request_routes(waypoints: list[LatLon], alternatives: bool) -> list[Route]:
    coordinates = ";".join(f"{point.lon},{point.lat}" for point in waypoints)
    params: dict[str, Any] = {
        "alternatives": "true" if alternatives else "false",
        "overview": "full",
        "geometries": "geojson",
        "annotations": "duration",
        "steps": "false",
    }
    if settings.MAPBOX_TOKEN:
        url = MAPBOX_DIRECTIONS_URL + coordinates
        params["access_token"] = settings.MAPBOX_TOKEN
    else:
        url = OSRM_URL + coordinates

    try:
        data = get_json(url, params, "Routing service")
    except ExternalServiceError as error:
        if isinstance(error.payload, dict) and error.payload.get("code") in _NO_ROUTE_CODES:
            raise NoRouteError("No drivable route was found between these places.") from error
        raise

    if data.get("code") in _NO_ROUTE_CODES or not data.get("routes"):
        raise NoRouteError("No drivable route was found between these places.")
    return [_parse_route(route) for route in data["routes"]]


def _parse_route(route: dict[str, Any], is_detour: bool = False) -> Route:
    points = [LatLon(lat, lon) for lon, lat in route["geometry"]["coordinates"]]
    # A route through a detour point has one "leg" per stretch; join them.
    durations = [
        float(seconds) for leg in route["legs"] for seconds in leg["annotation"]["duration"]
    ]
    if len(durations) != len(points) - 1:
        raise ExternalServiceError("Routing service returned an inconsistent route.")
    return Route(points=points, segment_durations_s=durations, is_detour=is_detour)


def _detour_points(origin: LatLon, destination: LatLon) -> list[LatLon]:
    """Two points beside the trip's midpoint, one on each side of the straight line."""
    mid_lat = (origin.lat + destination.lat) / 2
    mid_lon = (origin.lon + destination.lon) / 2

    # Work in a local flat grid where one unit = one degree of latitude.
    lon_scale = math.cos(math.radians(mid_lat))
    dx = (destination.lon - origin.lon) * lon_scale
    dy = destination.lat - origin.lat
    length = math.hypot(dx, dy)
    if length == 0:
        return []

    offset = DETOUR_OFFSET_SHARE * length
    # (-dy, dx) is perpendicular to the direction of travel.
    side_lat = -dx / length * offset
    side_lon = dy / length * offset / lon_scale
    return [
        LatLon(mid_lat + side_lat, mid_lon + side_lon),
        LatLon(mid_lat - side_lat, mid_lon - side_lon),
    ]


def _try_detour(origin: LatLon, via: LatLon, destination: LatLon) -> Route | None:
    try:
        route = _request_routes([origin, via, destination], alternatives=False)[0]
    except (NoRouteError, ExternalServiceError):
        # e.g. the detour point is in the sea. The main routes are still fine.
        return None
    return Route(route.points, route.segment_durations_s, is_detour=True)


def _is_useful_detour(detour: Route, fastest: Route, existing: list[Route]) -> bool:
    if detour.duration_seconds > fastest.duration_seconds * DETOUR_MAX_SLOWDOWN:
        return False
    return not any(_is_same_route(detour, route) for route in existing)


def _is_same_route(a: Route, b: Route) -> bool:
    def close(x: float, y: float) -> bool:
        return abs(x - y) <= SAME_ROUTE_TOLERANCE * max(x, y)

    return close(a.distance_miles, b.distance_miles) and close(
        a.duration_seconds, b.duration_seconds
    )
