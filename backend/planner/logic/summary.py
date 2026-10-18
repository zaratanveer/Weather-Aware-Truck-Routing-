"""
Summarises the risk along one route.

Each checkpoint "owns" the stretch of road from itself to the next
checkpoint: its risk level applies to those miles. The final checkpoint
(the destination) owns no miles but still counts towards `has_no_travel`.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from .risk import RiskLevel


@dataclass(frozen=True)
class RouteSummary:
    distance_miles: float
    duration_seconds: float
    miles_by_level: dict[RiskLevel, float]
    average_risk: float  # mile-weighted, on the 0 (Low) .. 4 (No Travel) scale
    worst_level: RiskLevel
    has_no_travel: bool

    def miles_at(self, level: RiskLevel) -> float:
        return self.miles_by_level[level]


def summarize_route(
    checkpoint_miles: Sequence[float],
    checkpoint_levels: Sequence[RiskLevel],
    duration_seconds: float,
) -> RouteSummary:
    """Miles per risk level, mile-weighted average risk and No Travel flag."""
    if len(checkpoint_miles) != len(checkpoint_levels):
        raise ValueError("Every checkpoint needs exactly one risk level.")
    if not checkpoint_miles:
        raise ValueError("A route summary needs at least one checkpoint.")

    miles_by_level = {level: 0.0 for level in RiskLevel}
    for index, level in enumerate(checkpoint_levels[:-1]):
        miles_by_level[level] += checkpoint_miles[index + 1] - checkpoint_miles[index]

    distance = checkpoint_miles[-1]
    if distance > 0:
        average = sum(level * miles for level, miles in miles_by_level.items()) / distance
    else:
        average = float(checkpoint_levels[0])

    worst = max(checkpoint_levels)
    return RouteSummary(
        distance_miles=distance,
        duration_seconds=duration_seconds,
        miles_by_level=miles_by_level,
        average_risk=average,
        worst_level=worst,
        has_no_travel=worst is RiskLevel.NO_TRAVEL,
    )
