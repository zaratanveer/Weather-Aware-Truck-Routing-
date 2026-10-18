from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from django.test import Client

from planner import views
from planner.logic.geo import LatLon
from planner.services.geocoding import Place
from planner.services.http import ExternalServiceError
from planner.services.routing import NoRouteError, Route
from planner.services.weather import HourlyForecast
from planner.trip_planner import plan_trip


def future(hours: float = 2) -> datetime:
    return (datetime.now(UTC) + timedelta(hours=hours)).replace(microsecond=0)


def valid_body(**overrides) -> dict:
    body = {
        "origin": {"lat": 32.7767, "lon": -96.797},
        "destination": {"lat": 41.8781, "lon": -87.6298},
        "departure": future().isoformat(),
        "load_lb": 35_000,
        "interval_miles": 25,
    }
    body.update(overrides)
    return body


def post_plan(body: dict):
    return Client().post("/api/plan/", body, content_type="application/json")


def fake_plan_trip(**kwargs):
    """The real planner, with fake routing and weather (wind 48 mph everywhere)."""

    def routes(origin: LatLon, destination: LatLon) -> list[Route]:
        return [Route([LatLon(0, 0), LatLon(0, 1)], [3600])]

    def forecasts(locations, start, end) -> list[HourlyForecast]:
        hours = [start.replace(minute=0, second=0) + timedelta(hours=h) for h in range(4)]
        return [HourlyForecast(hours, [48.0] * 4, [0.0] * 4, [0.0] * 4) for _ in locations]

    return plan_trip(**kwargs, route_fetcher=routes, forecast_fetcher=forecasts)


class TestPlanEndpoint:
    def test_returns_routes_checkpoints_and_recommendation(self, monkeypatch) -> None:
        monkeypatch.setattr(views, "plan_trip", fake_plan_trip)

        response = post_plan(valid_body())

        assert response.status_code == 200
        data = response.json()
        [route] = data["routes"]
        assert route["name"] == "Route 1"
        assert route["is_recommended"] is True
        assert route["geometry"] == [[0, 0], [1, 0]]  # [lon, lat] for the map
        assert route["duration_seconds"] == 3600
        assert [cp["mile"] for cp in route["checkpoints"]] == [0, 25, 50, 69.1]
        checkpoint = route["checkpoints"][0]
        # 48 mph wind is Severe; 35,000 lb in 45–54 mph wind is No Travel.
        assert checkpoint["level"] == "No Travel"
        assert checkpoint["drivers"] == ["load"]
        assert checkpoint["wind_mph"] == 48
        assert route["summary"]["miles_by_level"]["No Travel"] == 69.1
        assert route["summary"]["has_no_travel"] is True
        assert data["recommendation"]["route_index"] == 0
        assert data["notices"] == ["Only 1 route could be found between these places."]

    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            ({"load_lb": -5}, "load_lb"),
            ({"load_lb": 90_000}, "load_lb"),
            ({"interval_miles": 15}, "interval_miles"),
            ({"departure": "not a date"}, "departure"),
            ({"departure": future(hours=-3).isoformat()}, "departure"),
            ({"departure": future(hours=24 * 8).isoformat()}, "departure"),
            ({"origin": {"lat": 95, "lon": 0}}, "origin"),
            ({"destination": {"lat": 32.7767, "lon": -96.797}}, "non_field_errors"),
        ],
    )
    def test_invalid_input_is_rejected_with_field_errors(self, overrides: dict, field: str) -> None:
        response = post_plan(valid_body(**overrides))

        assert response.status_code == 400
        assert field in response.json()

    def test_missing_fields_are_reported(self) -> None:
        response = post_plan({})

        assert response.status_code == 400
        assert set(response.json()) == {"origin", "destination", "departure", "load_lb", "interval_miles"}

    def test_no_route_is_422(self, monkeypatch) -> None:
        monkeypatch.setattr(views, "plan_trip", Mock(side_effect=NoRouteError("No drivable route.")))

        response = post_plan(valid_body())

        assert response.status_code == 422
        assert response.json() == {"detail": "No drivable route."}

    def test_external_failure_is_502(self, monkeypatch) -> None:
        monkeypatch.setattr(views, "plan_trip", Mock(side_effect=ExternalServiceError("Weather is down.")))

        response = post_plan(valid_body())

        assert response.status_code == 502
        assert response.json() == {"detail": "Weather is down."}

    def test_get_is_not_allowed(self) -> None:
        assert Client().get("/api/plan/").status_code == 405


class TestGeocodeEndpoint:
    def test_returns_places(self, monkeypatch) -> None:
        fake = Mock(return_value=[Place("Dallas, Texas, United States", LatLon(32.78, -96.8))])
        monkeypatch.setattr(views, "search_places", fake)

        response = Client().get("/api/geocode/", {"q": "dallas"})

        assert response.status_code == 200
        assert response.json() == {
            "results": [{"label": "Dallas, Texas, United States", "lat": 32.78, "lon": -96.8}]
        }

    def test_results_are_cached(self, monkeypatch) -> None:
        fake = Mock(return_value=[])
        monkeypatch.setattr(views, "search_places", fake)

        Client().get("/api/geocode/", {"q": "Dallas"})
        Client().get("/api/geocode/", {"q": "dallas"})

        assert fake.call_count == 1

    def test_very_short_query_returns_nothing_without_calling_the_service(self, monkeypatch) -> None:
        fake = Mock()
        monkeypatch.setattr(views, "search_places", fake)

        response = Client().get("/api/geocode/", {"q": "d"})

        assert response.json() == {"results": []}
        fake.assert_not_called()

    def test_missing_query_is_400(self) -> None:
        assert Client().get("/api/geocode/").status_code == 400

    def test_service_failure_is_502(self, monkeypatch) -> None:
        monkeypatch.setattr(views, "search_places", Mock(side_effect=ExternalServiceError("Down.")))

        response = Client().get("/api/geocode/", {"q": "dallas"})

        assert response.status_code == 502
