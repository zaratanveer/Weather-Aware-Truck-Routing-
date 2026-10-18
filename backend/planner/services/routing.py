"""
Driving routes between two places, with up to 3 alternatives.

Default: the public OSRM server (router.project-osrm.org), free and key-less.
If MAPBOX_TOKEN is set, Mapbox Directions is used instead. Both return the
same shape: a GeoJSON line plus the driving time of every line segment.

The routing engines often return fewer than 3 routes. When that happens we
ask the same engine for routes forced through a detour point on either side
of the trip's midpoint. These are real drivable routes, labelled as detours,
and are only kept when they are clearly different and not much slower. If
a detour drives out to its detour point and straight back (a "spur" up a
side road), that pointless out-and-back part is cut off first.
"""

import math
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from itertools import accumulate
from typing import Any

from django.conf import settings

from ..logic.geo import LatLon, haversine_miles, interpolate
from .http import ExternalServiceError, get_json

OSRM_URL = "https://router.project-osrm.org/route/v1/driving/"
MAPBOX_DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox/driving/"

MAX_ROUTES = 3
# Detour routes: how far to the side detour points are placed, as shares of
# the straight-line trip distance (nearer ones are tried first), and the
# slowest detour we still offer.
DETOUR_OFFSET_SHARES = (0.15, 0.3)
DETOUR_MAX_SLOWDOWN = 1.5
# Two routes whose distance and duration are both within 1% are the same road.
SAME_ROUTE_TOLERANCE = 0.01
# Spur detection: walking the same distance back and forward from a detour
# point, a real through-route quickly moves apart, while an out-and-back spur
# stays within this gap (the two directions of the same road).
SPUR_MAX_GAP_MILES = 0.5
SPUR_SCAN_STEP_MILES = 0.25
SPUR_MAX_MILES = 50.0

_NO_ROUTE_CODES = {"NoRoute", "NoSegment"}


class NoRouteError(Exception):
    """The routing engine found no drivable road between the two places."""


@dataclass(frozen=True)
class Route:
    points: list[LatLon]
    segment_durations_s: list[float]  # driving time from points[i] to points[i + 1]
    is_detour: bool = False
    # Indexes in `points` where the route passes an intermediate (detour) waypoint.
    waypoint_indexes: tuple[int, ...] = ()

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
        for share in DETOUR_OFFSET_SHARES:
            for via in _detour_points(origin, destination, share):
                if len(routes) >= MAX_ROUTES:
                    return routes
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
    durations: list[float] = []
    waypoint_indexes: list[int] = []
    for leg in route["legs"]:
        if durations:
            waypoint_indexes.append(len(durations))  # where the previous leg ended
        durations.extend(float(seconds) for seconds in leg["annotation"]["duration"])

    if len(durations) != len(points) - 1:
        raise ExternalServiceError("Routing service returned an inconsistent route.")
    return Route(points, durations, is_detour, tuple(waypoint_indexes))


def _detour_points(origin: LatLon, destination: LatLon, share: float) -> list[LatLon]:
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

    offset = share * length
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
    return _without_spurs(route)


def _is_useful_detour(detour: Route, fastest: Route, existing: list[Route]) -> bool:
    if detour.duration_seconds > fastest.duration_seconds * DETOUR_MAX_SLOWDOWN:
        return False
    return not any(_is_same_route(detour, route) for route in existing)


def _without_spurs(route: Route) -> Route:
    """The detour with any out-and-back spur at its detour points cut off."""
    points, durations = list(route.points), list(route.segment_durations_s)
    # Last waypoint first, so cutting doesn't shift the earlier indexes.
    for waypoint in sorted(route.waypoint_indexes, reverse=True):
        miles_at = _cumulative_miles(points)
        spur_miles = _spur_length(points, miles_at, waypoint)
        if spur_miles == 0:
            continue
        # The two ends of the spur are within SPUR_MAX_GAP_MILES of each other;
        # join them directly (a few seconds of driving, so no time is added).
        reach = spur_miles + SPUR_MAX_GAP_MILES
        start = bisect_left(miles_at, miles_at[waypoint] - reach)
        end = bisect_right(miles_at, miles_at[waypoint] + reach) - 1
        points = points[: start + 1] + points[end:]
        durations = durations[:start] + [0.0] + durations[end:]
    return Route(points, durations, is_detour=True)


def _spur_length(points: list[LatLon], miles_at: list[float], index: int) -> float:
    """How many miles the route drives out to points[index] and back the same way.

    Walking the same distance back and forward from the detour point, a
    through-route spreads ~2 x that distance apart, while a spur's two
    directions stay close. The whole range is scanned (not just until the
    first miss) because a spur often ends in a small turnaround loop.
    """
    length = 0.0
    miles = SPUR_SCAN_STEP_MILES
    while miles <= SPUR_MAX_MILES:
        before = _point_at_mile(points, miles_at, miles_at[index] - miles)
        after = _point_at_mile(points, miles_at, miles_at[index] + miles)
        if haversine_miles(before, after) < min(SPUR_MAX_GAP_MILES, miles):
            length = miles
        miles += SPUR_SCAN_STEP_MILES
    return length


def _cumulative_miles(points: list[LatLon]) -> list[float]:
    """miles_at[i] = distance along the route from the start to points[i]."""
    return [0.0, *accumulate(haversine_miles(a, b) for a, b in zip(points, points[1:]))]


def _point_at_mile(points: list[LatLon], miles_at: list[float], mile: float) -> LatLon:
    """The spot `mile` miles from the start of the route (clamped to the route)."""
    mile = min(max(mile, 0.0), miles_at[-1])
    index = bisect_right(miles_at, mile) - 1  # binary search: fast on long routes
    if index >= len(points) - 1:
        return points[-1]
    segment = miles_at[index + 1] - miles_at[index]
    if segment == 0:
        return points[index]
    return interpolate(points[index], points[index + 1], (mile - miles_at[index]) / segment)


def _is_same_route(a: Route, b: Route) -> bool:
    def close(x: float, y: float) -> bool:
        return abs(x - y) <= SAME_ROUTE_TOLERANCE * max(x, y)

    return close(a.distance_miles, b.distance_miles) and close(
        a.duration_seconds, b.duration_seconds
    )
