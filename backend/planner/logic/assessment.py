"""
Combines the per-factor weather levels into one risk level for a truck.

1. Wind, rain and snow are each classified on their own (see risk.py).
2. The overall weather level is the worst of the three.
3. The load-weight rules from the spec can then raise the level, never lower it.
"""

from dataclasses import dataclass

from .risk import RiskLevel, classify_rain, classify_snow, classify_wind

# Load-rule thresholds from the spec, in pounds.
NO_TRAVEL_LOAD_LIMIT_LB = 30_000  # with wind 45–54 mph
SEVERE_LOAD_LIMIT_LB = 40_000  # with wind 35–44 mph


@dataclass(frozen=True)
class WeatherConditions:
    """Forecast weather at one place and hour, in the units the spec uses."""

    wind_mph: float
    rain_in_per_hr: float
    snow_in_per_hr: float


@dataclass(frozen=True)
class RiskAssessment:
    """The final level plus which factors produced it (for explaining it in the UI)."""

    level: RiskLevel
    drivers: tuple[str, ...]  # e.g. ("wind",), ("rain", "snow") or ("load",); empty when Low


def load_rule_level(wind_mph: float, load_lb: float) -> RiskLevel:
    """Spec load rules (the level a heavy load forces at a given wind speed).

    - wind >= 55 mph            -> No Travel for any load
    - wind 45–54 mph, > 30,000 lb -> No Travel
    - wind 35–44 mph, > 40,000 lb -> Severe
    Anything else adds no extra risk (Low).
    """
    if load_lb < 0:
        raise ValueError(f"Load weight cannot be negative: {load_lb}")
    if wind_mph >= 55:
        return RiskLevel.NO_TRAVEL
    if wind_mph >= 45 and load_lb > NO_TRAVEL_LOAD_LIMIT_LB:
        return RiskLevel.NO_TRAVEL
    if 35 <= wind_mph < 45 and load_lb > SEVERE_LOAD_LIMIT_LB:
        return RiskLevel.SEVERE
    return RiskLevel.LOW


def assess_risk(conditions: WeatherConditions, load_lb: float) -> RiskAssessment:
    """Overall risk for a truck carrying `load_lb` in the given weather."""
    factor_levels = {
        "wind": classify_wind(conditions.wind_mph),
        "rain": classify_rain(conditions.rain_in_per_hr),
        "snow": classify_snow(conditions.snow_in_per_hr),
    }
    weather_level = max(factor_levels.values())
    load_level = load_rule_level(conditions.wind_mph, load_lb)

    # The load rule only "drives" the result when it raised the level.
    if load_level > weather_level:
        return RiskAssessment(level=load_level, drivers=("load",))

    if weather_level is RiskLevel.LOW:
        return RiskAssessment(level=RiskLevel.LOW, drivers=())

    drivers = tuple(name for name, level in factor_levels.items() if level == weather_level)
    return RiskAssessment(level=weather_level, drivers=drivers)
