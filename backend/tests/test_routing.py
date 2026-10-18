from unittest.mock import Mock

import pytest

from planner.logic.geo import LatLon
from planner.services import routing
from planner.services.http import ExternalServiceError
from planner.services.routing import NoRouteError, Route, fetch_routes

ORIGIN = LatLon(32.78, -96.80)
DESTINATION = LatLon(41.88, -87.63)


def osrm_route(lons: list[float], seconds_per_segment: float, legs: int = 1) -> dict:
    """A minimal OSRM/Mapbox route: a line along the equator split into `legs` legs."""
    durations = [seconds_per_segment] * (len(lons) - 1)
    per_leg = len(durations) // legs
    return {
        "geometry": {"coordinates": [[lon, 0.0] for lon in lons]},
        "legs": [
            {"annotation": {"duration": durations[i * per_leg : (i + 1) * per_leg]}}
            for i in range(legs)
        ],
    }


def ok(*routes: dict) -> dict:
    return {"code": "Ok", "routes": list(routes)}


@pytest.fixture
def fake_get_json(monkeypatch: pytest.MonkeyPatch, settings) -> Mock:
    settings.MAPBOX_TOKEN = ""
    fake = Mock()
    monkeypatch.setattr(routing, "get_json", fake)
    return fake


class TestFetchRoutes:
    def test_parses_three_alternatives_without_detours(self, fake_get_json: Mock) -> None:
        fake_get_json.return_value = ok(
            osrm_route([0, 1, 2], 60), osrm_route([0, 1.5, 2.5], 70), osrm_route([0, 3], 80)
        )

        routes = fetch_routes(ORIGIN, DESTINATION)

        assert len(routes) == 3
        assert fake_get_json.call_count == 1
        assert routes[0].points == [LatLon(0, 0), LatLon(0, 1), LatLon(0, 2)]
        assert routes[0].segment_durations_s == [60, 60]
        assert routes[0].duration_seconds == 120
        assert not any(route.is_detour for route in routes)

    def test_request_uses_lon_lat_order_and_full_geojson(self, fake_get_json: Mock) -> None:
        fake_get_json.return_value = ok(osrm_route([0, 1], 60), osrm_route([0, 2], 60), osrm_route([0, 3], 60))

        fetch_routes(ORIGIN, DESTINATION)

        url, params, _ = fake_get_json.call_args.args
        assert url == routing.OSRM_URL + "-96.8,32.78;-87.63,41.88"
        assert params["alternatives"] == "true"
        assert params["geometries"] == "geojson"
        assert params["overview"] == "full"
        assert params["annotations"] == "duration"

    def test_never_returns_more_than_three(self, fake_get_json: Mock) -> None:
        fake_get_json.return_value = ok(*[osrm_route([0, i + 1], 60) for i in range(4)])

        assert len(fetch_routes(ORIGIN, DESTINATION)) == 3

    def test_adds_detour_routes_when_fewer_than_three(self, fake_get_json: Mock) -> None:
        fake_get_json.side_effect = [
            ok(osrm_route([0, 1, 2], 600)),  # main request: only one route
            ok(osrm_route([0, 0.8, 1.6, 2.2], 450, legs=3)),  # detour on one side
            ok(osrm_route([0, 1.2, 2.4], 650, legs=2)),  # detour on the other side
        ]

        routes = fetch_routes(ORIGIN, DESTINATION)

        assert [route.is_detour for route in routes] == [False, True, True]
        # Detour requests go through a third (via) waypoint and want one route.
        detour_url, detour_params, _ = fake_get_json.call_args_list[1].args
        assert detour_url.count(";") == 2
        assert detour_params["alternatives"] == "false"

    def test_multi_leg_durations_are_joined(self, fake_get_json: Mock) -> None:
        fake_get_json.side_effect = [
            ok(osrm_route([0, 1], 600)),
            ok(osrm_route([0, 0.5, 1, 1.5, 2], 200, legs=2)),
            ok(osrm_route([0, 3], 700)),
        ]

        detour = fetch_routes(ORIGIN, DESTINATION)[1]

        assert detour.segment_durations_s == [200, 200, 200, 200]

    def test_too_slow_or_duplicate_detours_are_dropped(self, fake_get_json: Mock) -> None:
        fake_get_json.side_effect = [
            ok(osrm_route([0, 1, 2], 600)),  # 1,200 s
            ok(osrm_route([0, 1, 2], 1000)),  # 2,000 s: more than 1.5x slower
            ok(osrm_route([0, 1, 2], 601)),  # same distance and time: duplicate
        ]

        assert len(fetch_routes(ORIGIN, DESTINATION)) == 1

    def test_failed_detour_requests_are_skipped(self, fake_get_json: Mock) -> None:
        fake_get_json.side_effect = [
            ok(osrm_route([0, 1], 600)),
            ExternalServiceError("Routing service is not responding right now."),
            {"code": "NoRoute", "routes": []},
        ]

        assert len(fetch_routes(ORIGIN, DESTINATION)) == 1

    def test_no_route_error_from_osrm_400(self, fake_get_json: Mock) -> None:
        fake_get_json.side_effect = ExternalServiceError("bad", payload={"code": "NoRoute"})

        with pytest.raises(NoRouteError):
            fetch_routes(ORIGIN, DESTINATION)

    def test_other_service_errors_are_passed_on(self, fake_get_json: Mock) -> None:
        fake_get_json.side_effect = ExternalServiceError("down")

        with pytest.raises(ExternalServiceError):
            fetch_routes(ORIGIN, DESTINATION)

    def test_mapbox_is_used_when_a_token_is_set(self, fake_get_json: Mock, settings) -> None:
        settings.MAPBOX_TOKEN = "test-token"
        fake_get_json.return_value = ok(osrm_route([0, 1], 60), osrm_route([0, 2], 60), osrm_route([0, 3], 60))

        fetch_routes(ORIGIN, DESTINATION)

        url, params, _ = fake_get_json.call_args.args
        assert url.startswith(routing.MAPBOX_DIRECTIONS_URL)
        assert params["access_token"] == "test-token"

    def test_inconsistent_annotation_is_rejected(self, fake_get_json: Mock) -> None:
        broken = osrm_route([0, 1, 2], 60)
        broken["legs"][0]["annotation"]["duration"] = [60]  # 3 points need 2 durations
        fake_get_json.return_value = ok(broken)

        with pytest.raises(ExternalServiceError):
            fetch_routes(ORIGIN, DESTINATION)


def test_route_distance_is_the_polyline_length() -> None:
    route = Route(points=[LatLon(0, 0), LatLon(0, 1), LatLon(0, 2)], segment_durations_s=[1, 1])

    assert route.distance_miles == pytest.approx(2 * 69.09, abs=0.05)
