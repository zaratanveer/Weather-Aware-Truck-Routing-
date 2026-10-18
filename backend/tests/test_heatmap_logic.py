import math

import pytest

from planner.logic.assessment import WeatherConditions, assess_risk
from planner.logic.geo import LatLon
from planner.logic.heatmap import Bounds, grid_points, heat_intensity, padded


def weather(wind: float = 0, rain: float = 0, snow: float = 0) -> WeatherConditions:
    return WeatherConditions(wind_mph=wind, rain_in_per_hr=rain, snow_in_per_hr=snow)


class TestGridPoints:
    def test_corners_and_count(self) -> None:
        points = grid_points(Bounds(south=30, west=-100, north=40, east=-90), size=3)

        assert len(points) == 9
        assert points[0] == LatLon(30, -100)  # south-west
        assert points[2] == LatLon(30, -90)  # south-east
        assert points[4] == LatLon(35, -95)  # centre
        assert points[-1] == LatLon(40, -90)  # north-east

    def test_rejects_tiny_grid(self) -> None:
        with pytest.raises(ValueError):
            grid_points(Bounds(0, 0, 1, 1), size=1)


class TestPadded:
    def test_grows_by_a_share_of_the_span(self) -> None:
        assert padded(Bounds(30, -100, 40, -80), share=0.1, minimum_degrees=0.5) == Bounds(
            29, -102, 41, -78
        )

    def test_uses_the_minimum_for_small_areas(self) -> None:
        assert padded(Bounds(30, -100, 30.1, -99.9), share=0.1, minimum_degrees=0.5) == Bounds(
            29.5, -100.5, 30.6, -99.4
        )


class TestHeatIntensity:
    def test_calm_is_zero(self) -> None:
        assert heat_intensity(weather(), load_lb=0) == 0

    def test_slides_smoothly_inside_a_level(self) -> None:
        # Wind 30 mph is halfway from Moderate (25) to High (35): 1.5 / 4.
        assert heat_intensity(weather(wind=30), load_lb=0) == pytest.approx(1.5 / 4)

    def test_no_travel_is_one(self) -> None:
        assert heat_intensity(weather(snow=4), load_lb=0) == 1

    def test_load_rule_raises_the_intensity(self) -> None:
        # 40 mph alone is High (0.5..0.75); over 40,000 lb it is Severe (>= 0.75).
        assert heat_intensity(weather(wind=40), load_lb=10_000) < 0.75
        assert heat_intensity(weather(wind=40), load_lb=42_000) >= 0.75

    @pytest.mark.parametrize(
        "conditions",
        [
            weather(wind=24.9),
            weather(wind=25),
            weather(rain=1.0),  # Severe even though it is the No Travel threshold
            weather(rain=0.3, snow=1.5, wind=44),
            weather(wind=50),
        ],
    )
    @pytest.mark.parametrize("load_lb", [0, 35_000, 45_000])
    def test_always_inside_the_official_level_band(self, conditions: WeatherConditions, load_lb: float) -> None:
        level = assess_risk(conditions, load_lb).level

        assert math.floor(heat_intensity(conditions, load_lb) * 4) == level
