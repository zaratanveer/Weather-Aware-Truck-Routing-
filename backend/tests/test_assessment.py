import pytest

from planner.logic.assessment import (
    RiskAssessment,
    WeatherConditions,
    assess_risk,
    load_rule_level,
)
from planner.logic.risk import RiskLevel

CALM = WeatherConditions(wind_mph=5, rain_in_per_hr=0, snow_in_per_hr=0)


def weather(wind: float = 0, rain: float = 0, snow: float = 0) -> WeatherConditions:
    return WeatherConditions(wind_mph=wind, rain_in_per_hr=rain, snow_in_per_hr=snow)


class TestWorstOfFactors:
    def test_calm_weather_is_low_with_no_drivers(self) -> None:
        assert assess_risk(CALM, load_lb=10_000) == RiskAssessment(RiskLevel.LOW, ())

    def test_worst_factor_wins(self) -> None:
        # Wind Moderate (30), rain High (0.3), snow Low (0.1) -> High because of rain.
        result = assess_risk(weather(wind=30, rain=0.3, snow=0.1), load_lb=0)

        assert result == RiskAssessment(RiskLevel.HIGH, ("rain",))

    def test_ties_list_every_factor_at_the_worst_level(self) -> None:
        # Rain Severe (0.6) and snow Severe (2.5).
        result = assess_risk(weather(rain=0.6, snow=2.5), load_lb=0)

        assert result == RiskAssessment(RiskLevel.SEVERE, ("rain", "snow"))

    def test_snow_no_travel(self) -> None:
        assert assess_risk(weather(snow=3.5), load_lb=0).level is RiskLevel.NO_TRAVEL


class TestLoadRuleLevel:
    @pytest.mark.parametrize(
        ("wind_mph", "load_lb", "expected"),
        [
            # >= 55 mph: No Travel for any load
            (55, 0, RiskLevel.NO_TRAVEL),
            (70, 1_000, RiskLevel.NO_TRAVEL),
            # 45–54 mph: No Travel only above 30,000 lb
            (45, 30_000, RiskLevel.LOW),
            (45, 30_001, RiskLevel.NO_TRAVEL),
            (54.9, 45_000, RiskLevel.NO_TRAVEL),
            # 35–44 mph: Severe only above 40,000 lb
            (35, 40_000, RiskLevel.LOW),
            (35, 40_001, RiskLevel.SEVERE),
            (44.9, 79_000, RiskLevel.SEVERE),
            # below 35 mph: load never matters
            (34.9, 79_000, RiskLevel.LOW),
        ],
    )
    def test_spec_load_rules(self, wind_mph: float, load_lb: float, expected: RiskLevel) -> None:
        assert load_rule_level(wind_mph, load_lb) is expected

    def test_negative_load_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            load_rule_level(10, -1)


class TestLoadOverrides:
    def test_heavy_load_in_45_mph_wind_is_no_travel(self) -> None:
        # Wind alone is Severe (45–54); a 35,000 lb load makes it No Travel.
        result = assess_risk(weather(wind=48), load_lb=35_000)

        assert result == RiskAssessment(RiskLevel.NO_TRAVEL, ("load",))

    def test_light_load_in_45_mph_wind_stays_severe(self) -> None:
        result = assess_risk(weather(wind=48), load_lb=20_000)

        assert result == RiskAssessment(RiskLevel.SEVERE, ("wind",))

    def test_heavy_load_in_40_mph_wind_is_severe(self) -> None:
        # Wind alone is High (35–44); over 40,000 lb raises it to Severe.
        result = assess_risk(weather(wind=40), load_lb=42_000)

        assert result == RiskAssessment(RiskLevel.SEVERE, ("load",))

    def test_load_rule_never_lowers_the_level(self) -> None:
        # Severe rain with a 40 mph wind and heavy load: load rule gives Severe,
        # rain already gives No Travel -> stays No Travel.
        result = assess_risk(weather(wind=40, rain=1.5), load_lb=42_000)

        assert result == RiskAssessment(RiskLevel.NO_TRAVEL, ("rain",))

    def test_load_rule_equal_to_weather_level_is_not_a_driver(self) -> None:
        # Rain Severe (0.7) and load rule Severe (40 mph, 42,000 lb): rain explains it.
        result = assess_risk(weather(wind=40, rain=0.7), load_lb=42_000)

        assert result == RiskAssessment(RiskLevel.SEVERE, ("rain",))
