"""
Weather heatmap over the trip corridor for every hour from 0 to 48 h.

All 49 hours are fetched in one batched forecast call and returned together,
so the frontend slider can switch hours instantly without new requests.
Raw forecasts are cached for 10 minutes: they don't depend on the load, so
changing the load weight re-scores cached data without hitting the API.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from django.core.cache import cache

from .logic.geo import LatLon
from .logic.heatmap import Bounds, grid_points, heat_intensity, padded
from .services.weather import HourlyForecast, fetch_hourly_forecasts

GRID_SIZE = 15  # 15 x 15 = 225 forecast points
FORECAST_HOURS = 48
PAD_SHARE = 0.1
PAD_MIN_DEGREES = 0.5
CACHE_SECONDS = 10 * 60

ForecastFetcher = Callable[[Sequence[LatLon], datetime, datetime], list[HourlyForecast]]


@dataclass(frozen=True)
class HeatmapFrame:
    time: datetime
    intensity: list[float]  # one value per grid point, 0 (calm) .. 1 (No Travel)


@dataclass(frozen=True)
class Heatmap:
    points: list[LatLon]
    frames: list[HeatmapFrame]  # hour 0 .. FORECAST_HOURS after the start


def build_heatmap(
    route_bounds: Bounds,
    start: datetime,
    load_lb: float,
    *,
    forecast_fetcher: ForecastFetcher = fetch_hourly_forecasts,
) -> Heatmap:
    area = padded(route_bounds, PAD_SHARE, PAD_MIN_DEGREES)
    points = grid_points(area, GRID_SIZE)
    first_hour = start.astimezone(UTC).replace(minute=0, second=0, microsecond=0)

    forecasts = _cached_forecasts(area, points, first_hour, forecast_fetcher)

    frames = []
    for hour_offset in range(FORECAST_HOURS + 1):
        moment = first_hour + timedelta(hours=hour_offset)
        intensity = [
            round(heat_intensity(forecast.conditions_at(moment)[1], load_lb), 3)
            for forecast in forecasts
        ]
        frames.append(HeatmapFrame(time=moment, intensity=intensity))
    return Heatmap(points=points, frames=frames)


def _cached_forecasts(
    area: Bounds, points: list[LatLon], first_hour: datetime, fetcher: ForecastFetcher
) -> list[HourlyForecast]:
    corners = ",".join(f"{value:.2f}" for value in (area.south, area.west, area.north, area.east))
    key = f"heatmap:{corners}:{first_hour.isoformat()}"

    forecasts = cache.get(key)
    if forecasts is None:
        forecasts = fetcher(points, first_hour, first_hour + timedelta(hours=FORECAST_HOURS))
        cache.set(key, forecasts, CACHE_SECONDS)
    return forecasts
