"""
Pure helpers for the weather heatmap: the sample grid and a smooth intensity.

Risk levels jump in steps (Low -> Moderate at exactly 25 mph). A heatmap
looks better with a smooth value, so the intensity slides between levels
(20 mph is "most of the way to Moderate"). It is clamped so it always stays
inside the official level band: floor(intensity * 4) == the risk level.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from .assessment import WeatherConditions, assess_risk
from .geo import LatLon

# Values at which each spec level starts: Low, Moderate, High, Severe, No Travel.
WIND_STEPS_MPH = (0, 25, 35, 45, 55)
RAIN_STEPS_IN = (0, 0.10, 0.25, 0.50, 1.00)
SNOW_STEPS_IN = (0, 0.5, 1.0, 2.0, 3.0)

MAX_LEVEL = 4
_JUST_BELOW_NEXT_LEVEL = 0.99


@dataclass(frozen=True)
class Bounds:
    south: float
    west: float
    north: float
    east: float


def grid_points(bounds: Bounds, size: int) -> list[LatLon]:
    """A size x size grid of evenly spaced points, row by row from south-west."""
    if size < 2:
        raise ValueError("A grid needs at least 2 points per side.")
    lat_step = (bounds.north - bounds.south) / (size - 1)
    lon_step = (bounds.east - bounds.west) / (size - 1)
    return [
        LatLon(bounds.south + row * lat_step, bounds.west + col * lon_step)
        for row in range(size)
        for col in range(size)
    ]


def padded(bounds: Bounds, share: float, minimum_degrees: float) -> Bounds:
    """`bounds` grown on every side, so the heatmap surrounds the routes."""
    lat_pad = max((bounds.north - bounds.south) * share, minimum_degrees)
    lon_pad = max((bounds.east - bounds.west) * share, minimum_degrees)
    return Bounds(
        south=max(bounds.south - lat_pad, -90),
        west=max(bounds.west - lon_pad, -180),
        north=min(bounds.north + lat_pad, 90),
        east=min(bounds.east + lon_pad, 180),
    )


def heat_intensity(conditions: WeatherConditions, load_lb: float) -> float:
    """0.0 (calm) .. 1.0 (No Travel), smooth but consistent with the risk level."""
    level = assess_risk(conditions, load_lb).level
    smooth = max(
        _position_between_steps(conditions.wind_mph, WIND_STEPS_MPH),
        _position_between_steps(conditions.rain_in_per_hr, RAIN_STEPS_IN),
        _position_between_steps(conditions.snow_in_per_hr, SNOW_STEPS_IN),
    )
    clamped = min(max(smooth, level), level + _JUST_BELOW_NEXT_LEVEL, MAX_LEVEL)
    return clamped / MAX_LEVEL


def _position_between_steps(value: float, steps: Sequence[float]) -> float:
    """E.g. wind 30 with steps (0, 25, 35, ...) -> 1.5 (halfway Moderate -> High)."""
    if value >= steps[-1]:
        return float(len(steps) - 1)
    for index in range(len(steps) - 1):
        low, high = steps[index], steps[index + 1]
        if value < high:
            return index + (max(value, low) - low) / (high - low)
    return float(len(steps) - 1)  # unreachable; keeps type checkers happy
