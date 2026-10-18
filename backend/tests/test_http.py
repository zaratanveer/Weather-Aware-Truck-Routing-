from unittest.mock import Mock

import pytest
import requests

from planner.services import http
from planner.services.http import ExternalServiceError, get_json


def fake_response(ok: bool = True, payload: object = None) -> Mock:
    response = Mock()
    response.ok = ok
    if payload is None:
        response.json.side_effect = ValueError("not JSON")
    else:
        response.json.return_value = payload
    return response


@pytest.fixture
def fake_get(monkeypatch: pytest.MonkeyPatch) -> Mock:
    fake = Mock()
    monkeypatch.setattr(http._session, "get", fake)
    return fake


class TestGetJson:
    def test_returns_decoded_json(self, fake_get: Mock) -> None:
        fake_get.return_value = fake_response(payload={"ok": True})

        assert get_json("https://example.test", {"a": 1}, "Test") == {"ok": True}

    def test_sends_user_agent_and_timeout(self, fake_get: Mock, settings) -> None:
        settings.HTTP_USER_AGENT = "TestAgent/1.0"
        settings.HTTP_TIMEOUT_SECONDS = 7
        fake_get.return_value = fake_response(payload={})

        get_json("https://example.test", {"a": 1}, "Test")

        assert fake_get.call_args.kwargs["params"] == {"a": 1}
        assert fake_get.call_args.kwargs["headers"] == {"User-Agent": "TestAgent/1.0"}
        assert fake_get.call_args.kwargs["timeout"] == 7

    def test_network_failure_becomes_external_service_error(self, fake_get: Mock) -> None:
        fake_get.side_effect = requests.ConnectionError("down")

        with pytest.raises(ExternalServiceError, match="Place search is not responding"):
            get_json("https://example.test", {}, "Place search")

    def test_error_status_keeps_the_json_error_body(self, fake_get: Mock) -> None:
        fake_get.return_value = fake_response(ok=False, payload={"code": "NoRoute"})

        with pytest.raises(ExternalServiceError) as caught:
            get_json("https://example.test", {}, "Routing")

        assert caught.value.payload == {"code": "NoRoute"}

    def test_non_json_body_is_an_error(self, fake_get: Mock) -> None:
        fake_get.return_value = fake_response(ok=True, payload=None)

        with pytest.raises(ExternalServiceError):
            get_json("https://example.test", {}, "Weather")
