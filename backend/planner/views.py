from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response


@api_view(["GET"])
def health(request: Request) -> Response:
    """Lightweight liveness check used by the frontend and the hosting platform."""
    return Response({"status": "ok"})
