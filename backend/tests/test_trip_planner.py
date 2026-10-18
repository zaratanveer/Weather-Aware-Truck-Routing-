from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from planner.logic.geo import LatLon
from planner.logic.risk import RiskLevel
from planner.services.routing import Route
from planner.services.weather import HourlyForecast
from planner.trip_planner import plan_trip

DEPARTURE = datetime(2026, 10, 20, 8, 0, tzinfo=UTC)
ORIGIN, DESTINATION = LatLon(0, 0), LatLon(0, 2)
HOURS = [DEPARTURE + timedelta(hours=h) for h in range(12)]


def straight_route(hours_per_degree: float, is_detour: bool = False) -> Route:
    """A ~138-mile route along the equator, 1 degree per segment."""
    return Route(
        points=[LatLon(0, 0), LatLon(0, 1), LatLon(0, 2)],
        segment_durations_s=[hours_per_degree * 3600] * 2,
        is_detour=is_detour,
    )


def steady_forecast(wind_mph: float) -> HourlyForecast:
    return HourlyForecast(
        hours=HOURS,
        wind_mph=[wind_mph] * len(HOURS),
        rain_in_per_hr=[0.0] * len(HOURS),
        snow_in_per_hr=[0.0] * len(HOURS),
    )


class FakeForecasts:
    """Returns a forecast per location; records what was asked for."""

    def __init__(self, wind_for_route: list[float], checkpoints_per_route: int) -> None:
        self.winds = [w for w in wind_for_route for _ in range(checkpoints_per_route)]
        self.calls: list[tuple[int, datetime, datetime]] = []

    def __call__(self, locations: Sequence[LatLon], start: datetime, end: datetime) -> list[HourlyForecast]:
        self.calls.append((len(locations), start, end))
        return [steady_forecast(wind) for wind in self.winds]


def plan(routes: list[Route], forecasts: FakeForecasts, load_lb: float = 20_000):
    return plan_trip(
        ORIGIN,
        DESTINATION,
        DEPARTURE,
        load_lb=load_lb,
        interval_miles=50,
        route_fetcher=lambda origin, destination: routes,
        forecast_fetcher=forecasts,
    )


class TestPlanTrip:
    def test_every_checkpoint_gets_weather_risk_and_eta(self) -> None:
        # ~138 miles at 50-mile interval -> checkpoints at 0, 50, 100, end.
        forecasts = FakeForecasts([30], checkpoints_per_route=4)

        result = plan([straight_route(1)], forecasts)

        [route] = result.routes
        assert [round(p.checkpoint.mile) for p in route.checkpoints] == [0, 50, 100, 138]
        assert all(p.assessment.level is RiskLevel.MODERATE for p in route.checkpoints)
        assert route.checkpoints[-1].checkpoint.eta == DEPARTURE + timedelta(hours=2)
        assert route.checkpoints[-1].forecast_hour == DEPARTURE + timedelta(hours=2)
        assert route.summary.miles_at(RiskLevel.MODERATE) == pytest.approx(138.2, abs=0.1)

    def test_weather_is_fetched_once_for_all_routes(self) -> None:
        forecasts = FakeForecasts([10, 10], checkpoints_per_route=4)

        plan([straight_route(1), straight_route(1.5)], forecasts)

        assert len(forecasts.calls) == 1
        count, start, end = forecasts.calls[0]
        assert count == 8
        assert start == DEPARTURE
        assert end == DEPARTURE + timedelta(hours=3)  # the slower route's arrival

    def test_recommends_the_safer_route_even_if_slower(self) -> None:
        # Route 1 is fast but windy (40 mph -> High), route 2 is slower but calm.
        forecasts = FakeForecasts([40, 10], checkpoints_per_route=4)

        result = plan([straight_route(1), straight_route(2)], forecasts)

        assert result.recommendation.route_index == 1
        assert "High-risk miles" in result.recommendation.reason

    def test_load_weight_is_applied(self) -> None:
        # 40 mph wind is High, but over 40,000 lb it becomes Severe.
        forecasts = FakeForecasts([40], checkpoints_per_route=4)

        result = plan([straight_route(1)], forecasts, load_lb=45_000)

        checkpoint = result.routes[0].checkpoints[0]
        assert checkpoint.assessment.level is RiskLevel.SEVERE
        assert checkpoint.assessment.drivers == ("load",)

    def test_routes_are_named_in_order(self) -> None:
        forecasts = FakeForecasts([10, 10, 10], checkpoints_per_route=4)

        result = plan([straight_route(1)] * 3, forecasts)

        assert [route.name for route in result.routes] == ["Route 1", "Route 2", "Route 3"]
        assert result.notices == []

    def test_notices_explain_missing_and_detour_routes(self) -> None:
        forecasts = FakeForecasts([10, 10], checkpoints_per_route=4)

        result = plan([straight_route(1), straight_route(1.2, is_detour=True)], forecasts)

        assert result.notices == [
            "Only 2 routes could be found between these places.",
            "Route 2 is a detour through a nearby area, because the routing service "
            "offered fewer than 3 routes.",
        ]
