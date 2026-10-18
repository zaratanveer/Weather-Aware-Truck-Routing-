from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from planner.logic.assessment import WeatherConditions
from planner.logic.geo import LatLon
from planner.services import weather
from planner.services.http import ExternalServiceError
from planner.services.weather import HourlyForecast, fetch_hourly_forecasts

START = datetime(2026, 10, 20, 8, 0, tzinfo=UTC)


def hourly_payload(hours: int = 3, wind: float = 10, rain: float = 0.05, showers: float = 0.02) -> dict:
    """What Open-Meteo returns for one location."""
    return {
        "hourly": {
            "time": [int((START + timedelta(hours=h)).timestamp()) for h in range(hours)],
            "wind_speed_10m": [wind + h for h in range(hours)],
            "rain": [rain] * hours,
            "showers": [showers] * hours,
            "snowfall": [0.0] * hours,
        }
    }


@pytest.fixture
def fake_get_json(monkeypatch: pytest.MonkeyPatch) -> Mock:
    fake = Mock()
    monkeypatch.setattr(weather, "get_json", fake)
    return fake


class TestFetchHourlyForecasts:
    def test_requests_spec_units_and_the_trip_window(self, fake_get_json: Mock) -> None:
        fake_get_json.return_value = [hourly_payload(), hourly_payload()]

        fetch_hourly_forecasts(
            [LatLon(32.7767, -96.797), LatLon(41.8781, -87.6298)],
            start=START + timedelta(minutes=40),
            end=START + timedelta(hours=5, minutes=10),
        )

        params = fake_get_json.call_args.args[1]
        assert params["latitude"] == "32.78,41.88"
        assert params["longitude"] == "-96.8,-87.63"
        assert params["hourly"] == "wind_speed_10m,rain,showers,snowfall"
        assert params["wind_speed_unit"] == "mph"
        assert params["precipitation_unit"] == "inch"
        # Whole hours that cover the trip: 08:00 .. 14:00 for 08:40 .. 13:10.
        assert params["start_hour"] == "2026-10-20T08:00"
        assert params["end_hour"] == "2026-10-20T14:00"

    def test_rain_includes_showers(self, fake_get_json: Mock) -> None:
        fake_get_json.return_value = hourly_payload(rain=0.05, showers=0.02)

        [forecast] = fetch_hourly_forecasts([LatLon(1, 1)], START, START)

        assert forecast.rain_in_per_hr[0] == pytest.approx(0.07)

    def test_single_location_object_response_is_supported(self, fake_get_json: Mock) -> None:
        fake_get_json.return_value = hourly_payload(hours=2)

        [forecast] = fetch_hourly_forecasts([LatLon(1, 1)], START, START)

        assert forecast.hours == [START, START + timedelta(hours=1)]

    def test_nearby_points_share_one_request_slot(self, fake_get_json: Mock) -> None:
        fake_get_json.return_value = [hourly_payload(wind=10), hourly_payload(wind=20)]
        a, a_again, b = LatLon(40.0001, -90.0001), LatLon(40.0002, -90.0002), LatLon(41, -91)

        forecasts = fetch_hourly_forecasts([a, b, a_again], START, START)

        assert fake_get_json.call_args.args[1]["latitude"] == "40.0,41"
        assert [forecast.wind_mph[0] for forecast in forecasts] == [10, 20, 10]

    def test_many_locations_are_split_into_batches(self, fake_get_json: Mock) -> None:
        locations = [LatLon(30 + i * 0.1, -90) for i in range(250)]
        fake_get_json.side_effect = lambda url, params, name: [
            hourly_payload() for _ in params["latitude"].split(",")
        ]

        forecasts = fetch_hourly_forecasts(locations, START, START)

        assert fake_get_json.call_count == 3  # 100 + 100 + 50
        assert len(forecasts) == 250

    def test_wrong_number_of_results_is_an_error(self, fake_get_json: Mock) -> None:
        fake_get_json.return_value = [hourly_payload()]

        with pytest.raises(ExternalServiceError):
            fetch_hourly_forecasts([LatLon(1, 1), LatLon(2, 2)], START, START)


class TestConditionsAt:
    @staticmethod
    def forecast(wind: list[float | None]) -> HourlyForecast:
        hours = [START + timedelta(hours=h) for h in range(len(wind))]
        zeros = [0.0] * len(wind)
        return HourlyForecast(hours=hours, wind_mph=wind, rain_in_per_hr=zeros, snow_in_per_hr=zeros)

    def test_picks_the_nearest_hour_to_the_eta(self) -> None:
        forecast = self.forecast([10, 20, 30])

        hour, conditions = forecast.conditions_at(START + timedelta(hours=1, minutes=20))

        assert hour == START + timedelta(hours=1)
        assert conditions == WeatherConditions(wind_mph=20, rain_in_per_hr=0, snow_in_per_hr=0)

    def test_rounds_up_past_the_half_hour(self) -> None:
        hour, _ = self.forecast([10, 20, 30]).conditions_at(START + timedelta(minutes=45))

        assert hour == START + timedelta(hours=1)

    def test_skips_hours_with_missing_values(self) -> None:
        hour, conditions = self.forecast([10, None, 30]).conditions_at(START + timedelta(hours=1, minutes=40))

        assert hour == START + timedelta(hours=2)
        assert conditions.wind_mph == 30

    def test_no_complete_hour_is_an_error(self) -> None:
        with pytest.raises(ExternalServiceError):
            self.forecast([None, None]).conditions_at(START)
