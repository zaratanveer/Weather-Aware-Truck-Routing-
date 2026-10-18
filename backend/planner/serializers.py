"""
Request validation (DRF serializers) and response shaping (plain functions).

DRF serializers check incoming JSON and convert it to Python types, like a
DTO + validation pipe. Responses are built with small functions because our
results are plain dataclasses, not database models.
"""

from datetime import datetime, timedelta
from typing import Any

from django.utils import timezone
from rest_framework import serializers

from .corridor_heatmap import Heatmap
from .logic.geo import LatLon, haversine_miles
from .logic.heatmap import Bounds
from .logic.risk import RiskLevel
from .services.geocoding import Place
from .trip_planner import PlannedCheckpoint, PlannedRoute, TripPlan

CHECKPOINT_INTERVALS_MILES = (10, 25, 50)
# U.S. federal gross weight limit for a truck on Interstates.
MAX_LOAD_LB = 80_000
# Forecasts get less reliable further out; 7 days keeps every trip well inside
# Open-Meteo's 16-day forecast range.
MAX_DAYS_AHEAD = 7
# Allow a small grace period so "now" is still valid when the request arrives.
PAST_GRACE = timedelta(hours=1)
MIN_TRIP_MILES = 1
# Roughly the width of the contiguous U.S.; larger areas make a useless grid.
MAX_HEATMAP_SPAN_DEGREES = 60


def validate_departure_window(value: datetime) -> datetime:
    """Shared by the plan and heatmap requests: a departure we have forecasts for."""
    now = timezone.now()
    if value < now - PAST_GRACE:
        raise serializers.ValidationError("Departure time cannot be in the past.")
    if value > now + timedelta(days=MAX_DAYS_AHEAD):
        raise serializers.ValidationError(
            f"Departure must be within the next {MAX_DAYS_AHEAD} days (forecast range)."
        )
    return value


class LocationSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)

    def to_internal_value(self, data: Any) -> LatLon:
        values = super().to_internal_value(data)
        return LatLon(values["lat"], values["lon"])


class PlanRequestSerializer(serializers.Serializer):
    origin = LocationSerializer()
    destination = LocationSerializer()
    departure = serializers.DateTimeField()
    load_lb = serializers.FloatField(min_value=0, max_value=MAX_LOAD_LB)
    interval_miles = serializers.ChoiceField(choices=CHECKPOINT_INTERVALS_MILES)

    def validate_departure(self, value: datetime) -> datetime:
        return validate_departure_window(value)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if haversine_miles(attrs["origin"], attrs["destination"]) < MIN_TRIP_MILES:
            raise serializers.ValidationError("Origin and destination must be different places.")
        return attrs


class GeocodeQuerySerializer(serializers.Serializer):
    q = serializers.CharField(max_length=200, trim_whitespace=True)


class HeatmapQuerySerializer(serializers.Serializer):
    """The routes' bounding box, the departure time and the load."""

    south = serializers.FloatField(min_value=-90, max_value=90)
    west = serializers.FloatField(min_value=-180, max_value=180)
    north = serializers.FloatField(min_value=-90, max_value=90)
    east = serializers.FloatField(min_value=-180, max_value=180)
    start = serializers.DateTimeField()
    load_lb = serializers.FloatField(min_value=0, max_value=MAX_LOAD_LB)

    def validate_start(self, value: datetime) -> datetime:
        return validate_departure_window(value)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["south"] >= attrs["north"] or attrs["west"] >= attrs["east"]:
            raise serializers.ValidationError("South/west must be smaller than north/east.")
        if attrs["north"] - attrs["south"] > MAX_HEATMAP_SPAN_DEGREES or (
            attrs["east"] - attrs["west"] > MAX_HEATMAP_SPAN_DEGREES
        ):
            raise serializers.ValidationError("The heatmap area is too large.")
        return attrs

    def bounds(self) -> Bounds:
        data = self.validated_data
        return Bounds(data["south"], data["west"], data["north"], data["east"])


# --- Responses --------------------------------------------------------------


def place_to_json(place: Place) -> dict[str, Any]:
    return {"label": place.label, "lat": place.location.lat, "lon": place.location.lon}


def plan_to_json(plan: TripPlan) -> dict[str, Any]:
    recommended = plan.recommendation.route_index
    return {
        "routes": [
            _route_to_json(index, route, is_recommended=index == recommended)
            for index, route in enumerate(plan.routes)
        ],
        "recommendation": {"route_index": recommended, "reason": plan.recommendation.reason},
        "notices": plan.notices,
    }


def _route_to_json(index: int, planned: PlannedRoute, is_recommended: bool) -> dict[str, Any]:
    summary = planned.summary
    return {
        "id": index,
        "name": planned.name,
        "is_recommended": is_recommended,
        "is_detour": planned.route.is_detour,
        "distance_miles": round(summary.distance_miles, 1),
        "duration_seconds": round(summary.duration_seconds),
        # GeoJSON order ([lon, lat]) so the map can use it directly; 5 decimals ~ 1 m.
        "geometry": [[round(p.lon, 5), round(p.lat, 5)] for p in planned.route.points],
        "summary": {
            "miles_by_level": {
                level.label: round(miles, 1) for level, miles in summary.miles_by_level.items()
            },
            "average_risk": round(summary.average_risk, 2),
            "worst_level": summary.worst_level.label,
            "has_no_travel": summary.has_no_travel,
        },
        "checkpoints": [_checkpoint_to_json(p) for p in planned.checkpoints],
    }


def _checkpoint_to_json(planned: PlannedCheckpoint) -> dict[str, Any]:
    checkpoint, conditions = planned.checkpoint, planned.conditions
    level: RiskLevel = planned.assessment.level
    return {
        "index": checkpoint.index,
        "mile": round(checkpoint.mile, 1),
        "lat": round(checkpoint.location.lat, 5),
        "lon": round(checkpoint.location.lon, 5),
        "eta": checkpoint.eta.isoformat(timespec="seconds"),
        "forecast_hour": planned.forecast_hour.isoformat(),
        "wind_mph": round(conditions.wind_mph, 1),
        "rain_in_per_hr": round(conditions.rain_in_per_hr, 2),
        "snow_in_per_hr": round(conditions.snow_in_per_hr, 2),
        "level": level.label,
        "drivers": list(planned.assessment.drivers),
    }


def heatmap_to_json(heatmap: Heatmap) -> dict[str, Any]:
    return {
        "points": [[round(p.lon, 4), round(p.lat, 4)] for p in heatmap.points],
        "frames": [
            {"time": frame.time.isoformat(), "intensity": frame.intensity}
            for frame in heatmap.frames
        ],
    }
