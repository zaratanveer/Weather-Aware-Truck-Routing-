"""Shared HTTP helper so every external call has the same timeout, headers and errors."""

from typing import Any

import requests
from django.conf import settings

# One session reuses TCP connections across calls to the same host.
_session = requests.Session()


class ExternalServiceError(Exception):
    """A third-party API failed, timed out or returned an unusable response.

    `payload` holds the decoded JSON error body when the service sent one, so a
    client can tell a real outage from an answer like "no route found".
    """

    def __init__(self, message: str, payload: Any = None) -> None:
        super().__init__(message)
        self.payload = payload


def get_json(url: str, params: dict[str, Any], service_name: str) -> Any:
    """GET `url` and return the decoded JSON body, or raise ExternalServiceError."""
    message = f"{service_name} is not responding right now."
    try:
        response = _session.get(
            url,
            params=params,
            headers={"User-Agent": settings.HTTP_USER_AGENT},
            timeout=settings.HTTP_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        raise ExternalServiceError(message) from error

    try:
        payload = response.json()
    except ValueError:
        payload = None

    if not response.ok or payload is None:
        raise ExternalServiceError(message, payload=payload)
    return payload
