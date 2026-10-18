from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from .corridor_heatmap import build_heatmap
from .serializers import (
    GeocodeQuerySerializer,
    HeatmapQuerySerializer,
    PlanRequestSerializer,
    heatmap_to_json,
    place_to_json,
    plan_to_json,
)
from .services.geocoding import search_places
from .services.http import ExternalServiceError
from .services.routing import NoRouteError
from .trip_planner import plan_trip

MIN_QUERY_LENGTH = 2
GEOCODE_CACHE_SECONDS = 24 * 60 * 60  # place coordinates don't change


@api_view(["GET"])
def health(request: Request) -> Response:
    """Lightweight liveness check used by the frontend and the hosting platform."""
    return Response({"status": "ok"})


@api_view(["GET"])
def geocode(request: Request) -> Response:
    """GET /api/geocode/?q=dall -> {"results": [{"label", "lat", "lon"}, ...]}"""
    query = GeocodeQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    text = query.validated_data["q"]
    if len(text) < MIN_QUERY_LENGTH:
        return Response({"results": []})

    cache_key = f"geocode:{text.lower()}"
    results = cache.get(cache_key)
    if results is None:
        try:
            results = [place_to_json(place) for place in search_places(text)]
        except ExternalServiceError as error:
            return Response({"detail": str(error)}, status=status.HTTP_502_BAD_GATEWAY)
        cache.set(cache_key, results, GEOCODE_CACHE_SECONDS)
    return Response({"results": results})


@api_view(["POST"])
def plan(request: Request) -> Response:
    """POST /api/plan/ -> routes with checkpoints, risk summaries and a recommendation."""
    trip = PlanRequestSerializer(data=request.data)
    trip.is_valid(raise_exception=True)  # invalid input -> 400 with field errors
    data = trip.validated_data

    try:
        result = plan_trip(
            origin=data["origin"],
            destination=data["destination"],
            departure=data["departure"],
            load_lb=data["load_lb"],
            interval_miles=data["interval_miles"],
        )
    except NoRouteError as error:
        return Response({"detail": str(error)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    except ExternalServiceError as error:
        return Response({"detail": str(error)}, status=status.HTTP_502_BAD_GATEWAY)
    return Response(plan_to_json(result))


@api_view(["GET"])
def heatmap(request: Request) -> Response:
    """GET /api/heatmap/?south=&west=&north=&east=&start=&load_lb= -> 49 hourly frames."""
    query = HeatmapQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)

    try:
        result = build_heatmap(
            query.bounds(),
            start=query.validated_data["start"],
            load_lb=query.validated_data["load_lb"],
        )
    except ExternalServiceError as error:
        return Response({"detail": str(error)}, status=status.HTTP_502_BAD_GATEWAY)
    return Response(heatmap_to_json(result))
