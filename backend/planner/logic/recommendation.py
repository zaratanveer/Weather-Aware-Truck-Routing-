"""
Picks the best route and explains the choice in plain English.

Spec preference order, applied one criterion at a time:
  1. fewest Severe miles
  2. fewest High miles
  3. lowest average risk
  4. shortest travel time
No Travel is worse than Severe, so any route with No Travel conditions is
ranked behind every route without them (and fewer No Travel miles first).
"""

from collections.abc import Sequence
from dataclasses import dataclass

from .risk import RiskLevel
from .summary import RouteSummary

# Values are rounded before comparing so floating-point noise (e.g. 12.0000001
# vs 12.0 miles) can never decide between two routes.
_MILES_PRECISION = 1
_RISK_PRECISION = 2


@dataclass(frozen=True)
class Recommendation:
    route_index: int
    reason: str


def ranking_key(summary: RouteSummary) -> tuple[bool, float, float, float, float, float]:
    """Sort key: smaller is better. Tuples compare item by item, left to right."""
    return (
        summary.has_no_travel,
        round(summary.miles_at(RiskLevel.NO_TRAVEL), _MILES_PRECISION),
        round(summary.miles_at(RiskLevel.SEVERE), _MILES_PRECISION),
        round(summary.miles_at(RiskLevel.HIGH), _MILES_PRECISION),
        round(summary.average_risk, _RISK_PRECISION),
        summary.duration_seconds,
    )


def recommend_route(summaries: Sequence[RouteSummary]) -> Recommendation:
    """The best route by `ranking_key`, with the reason it beat the runner-up."""
    if not summaries:
        raise ValueError("Cannot recommend from an empty list of routes.")

    ranked = sorted(range(len(summaries)), key=lambda i: ranking_key(summaries[i]))
    best_index = ranked[0]
    best = summaries[best_index]

    if len(summaries) == 1:
        reason = "Only one route was found, so it is the recommendation."
    else:
        runner_up_index = ranked[1]
        reason = _explain(best, summaries[runner_up_index], route_name(runner_up_index))

    if best.has_no_travel:
        reason += (
            " Warning: every route has No Travel conditions at the planned time;"
            " consider delaying departure."
        )
    return Recommendation(route_index=best_index, reason=reason)


def route_name(index: int) -> str:
    return f"Route {index + 1}"


def format_duration(seconds: float) -> str:
    """3725 -> "1 h 2 min"."""
    hours, minutes = divmod(round(seconds / 60), 60)
    return f"{hours} h {minutes} min" if hours else f"{minutes} min"


def _explain(best: RouteSummary, runner_up: RouteSummary, runner_up_name: str) -> str:
    """Names the first criterion where `best` beats the runner-up."""
    vs = f"vs {runner_up_name}"
    best_key, other_key = ranking_key(best), ranking_key(runner_up)

    if best_key[0] != other_key[0]:
        return f"It avoids the No Travel conditions found on {runner_up_name}."
    if best_key[1] != other_key[1]:
        return f"Fewest No Travel miles ({best_key[1]:g} {vs}: {other_key[1]:g})."
    if best_key[2] != other_key[2]:
        return f"Fewest Severe-risk miles ({best_key[2]:g} {vs}: {other_key[2]:g})."
    if best_key[3] != other_key[3]:
        return (
            "Same Severe mileage, fewest High-risk miles "
            f"({best_key[3]:g} {vs}: {other_key[3]:g})."
        )
    if best_key[4] != other_key[4]:
        return (
            "Same Severe and High mileage, lowest average risk "
            f"({best_key[4]:.2f} {vs}: {other_key[4]:.2f})."
        )
    if best_key[5] != other_key[5]:
        return (
            "Weather risk is the same, and it is the fastest "
            f"({format_duration(best.duration_seconds)} {vs}: "
            f"{format_duration(runner_up.duration_seconds)})."
        )
    return "All routes are rated the same; this is the first option."
