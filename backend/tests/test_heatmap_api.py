from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from django.test import Client

from planner import views
from planner.corridor_heatmap import FORECAST_HOURS, GRID_SIZE, build_heatmap
from planner.logic.geo import LatLon
from planner.logic.heatmap import Bounds
from planner.services.http import ExternalServiceError
from planner.services.weather import HourlyForecast

START = datetime(2026, 10, 20, 8, 25, tzinfo=UTC)
BOUNDS = Bounds(south=32, west=-97, north=42, east=-87)


class FakeForecasts:
    """Wind rises by 1 mph every hour, everywhere."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, points: Sequence[LatLon], start: datetime, end: datetime) -> list[HourlyForecast]:
        self.calls += 1
        hours = [start + timedelta(hours=h) for h in range(FORECAST_HOURS + 1)]
        winds = [float(h) for h in range(len(hours))]
        zeros = [0.0] * len(hours)
        return [HourlyForecast(hours, winds, zeros, zeros) for _ in points]


class TestBuildHeatmap:
    def test_has_a_frame_for_every_hour_0_to_48(self) -> None:
        heatmap = build_heatmap(BOUNDS, START, load_lb=0, forecast_fetcher=FakeForecasts())

        assert len(heatmap.frames) == 49
        assert heatmap.frames[0].time == datetime(2026, 10, 20, 8, 0, tzinfo=UTC)
        assert heatmap.frames[-1].time == datetime(2026, 10, 22, 8, 0, tzinfo=UTC)

    def test_grid_covers_the_padded_route_area(self) -> None:
        heatmap = build_heatmap(BOUNDS, START, load_lb=0, forecast_fetcher=FakeForecasts())

        assert len(heatmap.points) == GRID_SIZE * GRID_SIZE
        assert all(len(frame.intensity) == len(heatmap.points) for frame in heatmap.frames)
        assert heatmap.points[0] == LatLon(31, -98)  # 10% padding on each side
        assert heatmap.points[-1] == LatLon(43, -86)

    def test_intensity_follows_the_forecast_hour(self) -> None:
        heatmap = build_heatmap(BOUNDS, START, load_lb=0, forecast_fetcher=FakeForecasts())

        assert heatmap.frames[0].intensity[0] == 0  # 0 mph
        assert heatmap.frames[30].intensity[0] == pytest.approx(1.5 / 4)  # 30 mph

    def test_forecasts_are_cached_and_reused_for_a_different_load(self) -> None:
        fetcher = FakeForecasts()

        light = build_heatmap(BOUNDS, START, load_lb=0, forecast_fetcher=fetcher)
        heavy = build_heatmap(BOUNDS, START, load_lb=45_000, forecast_fetcher=fetcher)

        assert fetcher.calls == 1
        # Hour 40 = 40 mph: High normally, Severe over 40,000 lb.
        assert light.frames[40].intensity[0] < 0.75 <= heavy.frames[40].intensity[0]


class TestHeatmapEndpoint:
    @staticmethod
    def query(**overrides) -> dict:
        params = {
            "south": 32,
            "west": -97,
            "north": 42,
            "east": -87,
            "start": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "load_lb": 20_000,
        }
        params.update(overrides)
        return params

    def test_returns_points_and_frames(self, monkeypatch) -> None:
        # The view calls build_heatmap with the real weather client; swap in the fake.
        monkeypatch.setattr(
            views,
            "build_heatmap",
            lambda *args, **kwargs: build_heatmap(*args, **kwargs, forecast_fetcher=FakeForecasts()),
        )

        response = Client().get("/api/heatmap/", self.query())

        assert response.status_code == 200
        data = response.json()
        assert len(data["points"]) == 225
        assert data["points"][0] == [-98, 31]  # [lon, lat] for the map
        assert len(data["frames"]) == 49
        assert len(data["frames"][0]["intensity"]) == 225

    @pytest.mark.parametrize(
        "overrides",
        [
            {"south": 45},  # south above north
            {"west": -80},  # west east of east
            {"west": -170},  # wider than 60 degrees
            {"load_lb": -1},
            {"start": "yesterday"},
        ],
    )
    def test_invalid_query_is_400(self, overrides: dict) -> None:
        assert Client().get("/api/heatmap/", self.query(**overrides)).status_code == 400

    def test_weather_failure_is_502(self, monkeypatch) -> None:
        monkeypatch.setattr(views, "build_heatmap", Mock(side_effect=ExternalServiceError("Down.")))

        assert Client().get("/api/heatmap/", self.query()).status_code == 502
