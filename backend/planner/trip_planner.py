"""
Builds a complete trip plan: routes -> checkpoints -> weather -> risk -> recommendation.

This is the only place that combines the external services with the pure
logic. The services are passed in as arguments (with the real ones as
defaults) so tests can swap in fakes without any network access.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from .logic.assessment import RiskAssessment, WeatherConditions, assess_risk
from .logic.checkpoints import Checkpoint, build_checkpoints
from .logic.geo import LatLon
from .logic.recommendation import Recommendation, recommend_route, route_name
from .logic.summary import RouteSummary, summarize_route
from .services.routing import MAX_ROUTES, Route, fetch_routes
from .services.weather import HourlyForecast, fetch_hourly_forecasts

RouteFetcher = Callable[[LatLon, LatLon], list[Route]]
ForecastFetcher = Callable[[Sequence[LatLon], datetime, datetime], list[HourlyForecast]]


@dataclass(frozen=True)
class PlannedCheckpoint:
    checkpoint: Checkpoint
    forecast_hour: datetime  # the forecast hour used for this checkpoint's ETA
    conditions: WeatherConditions
    assessment: RiskAssessment


@dataclass(frozen=True)
class PlannedRoute:
    name: str
    route: Route
    checkpoints: list[PlannedCheckpoint]
    summary: RouteSummary


@dataclass(frozen=True)
class TripPlan:
    routes: list[PlannedRoute]
    recommendation: Recommendation
    notices: list[str]  # things the driver should know, e.g. "only 2 routes found"


def plan_trip(
    origin: LatLon,
    destination: LatLon,
    departure: datetime,
    load_lb: float,
    interval_miles: float,
    *,
    route_fetcher: RouteFetcher = fetch_routes,
    forecast_fetcher: ForecastFetcher = fetch_hourly_forecasts,
) -> TripPlan:
    routes = route_fetcher(origin, destination)
    checkpoints_per_route = [
        build_checkpoints(route.points, route.segment_durations_s, interval_miles, departure)
        for route in routes
    ]

    # One batched weather request for every checkpoint on every route.
    all_checkpoints = [cp for checkpoints in checkpoints_per_route for cp in checkpoints]
    latest_eta = max(cp.eta for cp in all_checkpoints)
    forecasts = iter(
        forecast_fetcher([cp.location for cp in all_checkpoints], departure, latest_eta)
    )

    planned_routes = []
    for index, (route, checkpoints) in enumerate(zip(routes, checkpoints_per_route)):
        planned = [_assess_checkpoint(cp, next(forecasts), load_lb) for cp in checkpoints]
        summary = summarize_route(
            [p.checkpoint.mile for p in planned],
            [p.assessment.level for p in planned],
            route.duration_seconds,
        )
        planned_routes.append(PlannedRoute(route_name(index), route, planned, summary))

    return TripPlan(
        routes=planned_routes,
        recommendation=recommend_route([route.summary for route in planned_routes]),
        notices=_notices(routes),
    )


def _assess_checkpoint(
    checkpoint: Checkpoint, forecast: HourlyForecast, load_lb: float
) -> PlannedCheckpoint:
    forecast_hour, conditions = forecast.conditions_at(checkpoint.eta)
    return PlannedCheckpoint(
        checkpoint=checkpoint,
        forecast_hour=forecast_hour,
        conditions=conditions,
        assessment=assess_risk(conditions, load_lb),
    )


def _notices(routes: list[Route]) -> list[str]:
    notices = []
    if len(routes) < MAX_ROUTES:
        found = f"{len(routes)} route" + ("" if len(routes) == 1 else "s")
        notices.append(f"Only {found} could be found between these places.")
    detours = [route_name(i) for i, route in enumerate(routes) if route.is_detour]
    if detours:
        notices.append(
            f"{' and '.join(detours)} {'is a detour' if len(detours) == 1 else 'are detours'} "
            "through a nearby area, because the routing service offered fewer than 3 routes."
        )
    return notices
