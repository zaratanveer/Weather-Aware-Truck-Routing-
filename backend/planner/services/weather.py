"""
Hourly forecasts from Open-Meteo (free, no API key).

Open-Meteo accepts many coordinates in one request, so every checkpoint of
every route is fetched in a few batched calls instead of one call each.
Units match the spec: wind in mph, rain and snow in inches per hour.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from ..logic.assessment import WeatherConditions
from ..logic.geo import LatLon
from .http import ExternalServiceError, get_json

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
# Keeps the request URL a safe length (each location adds ~20 characters).
MAX_LOCATIONS_PER_REQUEST = 100
# ~1 km. Points closer than this share a forecast, so overlapping routes are
# only fetched once. Forecast models are coarser than this anyway.
COORDINATE_DECIMALS = 2


@dataclass(frozen=True)
class HourlyForecast:
    """One location's forecast. Lists are aligned with `hours`; None = missing value."""

    hours: list[datetime]
    wind_mph: list[float | None]
    rain_in_per_hr: list[float | None]
    snow_in_per_hr: list[float | None]

    def conditions_at(self, moment: datetime) -> tuple[datetime, WeatherConditions]:
        """The forecast hour nearest to `moment` that has complete data."""
        complete = [
            i
            for i in range(len(self.hours))
            if None not in (self.wind_mph[i], self.rain_in_per_hr[i], self.snow_in_per_hr[i])
        ]
        if not complete:
            raise ExternalServiceError("No forecast data is available for this time.")

        nearest = min(complete, key=lambda i: abs(self.hours[i] - moment))
        conditions = WeatherConditions(
            wind_mph=self.wind_mph[nearest],
            rain_in_per_hr=self.rain_in_per_hr[nearest],
            snow_in_per_hr=self.snow_in_per_hr[nearest],
        )
        return self.hours[nearest], conditions


def fetch_hourly_forecasts(
    locations: Sequence[LatLon], start: datetime, end: datetime
) -> list[HourlyForecast]:
    """Forecasts covering start..end (whole hours), in the same order as `locations`."""
    keys = [_location_key(location) for location in locations]
    unique_keys = list(dict.fromkeys(keys))  # de-duplicate, keep order

    by_key: dict[LatLon, HourlyForecast] = {}
    for offset in range(0, len(unique_keys), MAX_LOCATIONS_PER_REQUEST):
        batch = unique_keys[offset : offset + MAX_LOCATIONS_PER_REQUEST]
        by_key.update(zip(batch, _fetch_batch(batch, start, end)))

    return [by_key[key] for key in keys]


def _location_key(location: LatLon) -> LatLon:
    return LatLon(round(location.lat, COORDINATE_DECIMALS), round(location.lon, COORDINATE_DECIMALS))


def _fetch_batch(locations: list[LatLon], start: datetime, end: datetime) -> list[HourlyForecast]:
    first_hour = start.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    last_hour = end.astimezone(UTC).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    params = {
        "latitude": ",".join(str(location.lat) for location in locations),
        "longitude": ",".join(str(location.lon) for location in locations),
        # "rain" is steady rain; "showers" is convective rain. Both are rain.
        "hourly": "wind_speed_10m,rain,showers,snowfall",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "GMT",
        "timeformat": "unixtime",
        "start_hour": first_hour.strftime("%Y-%m-%dT%H:%M"),
        "end_hour": last_hour.strftime("%Y-%m-%dT%H:%M"),
    }
    data = get_json(OPEN_METEO_URL, params, "Weather service")

    # A single location comes back as an object, several as a list.
    results = data if isinstance(data, list) else [data]
    if len(results) != len(locations):
        raise ExternalServiceError("Weather service returned the wrong number of locations.")
    return [_parse_forecast(result["hourly"]) for result in results]


def _parse_forecast(hourly: dict[str, Any]) -> HourlyForecast:
    rain = [_add(steady, shower) for steady, shower in zip(hourly["rain"], hourly["showers"])]
    return HourlyForecast(
        hours=[datetime.fromtimestamp(timestamp, tz=UTC) for timestamp in hourly["time"]],
        wind_mph=hourly["wind_speed_10m"],
        rain_in_per_hr=rain,
        snow_in_per_hr=hourly["snowfall"],
    )


def _add(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a + b
