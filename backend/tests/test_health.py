from django.test import Client


def test_health_endpoint_returns_ok() -> None:
    response = Client().get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_frontend_origin_is_allowed_by_cors() -> None:
    response = Client().get("/api/health/", HTTP_ORIGIN="http://localhost:5173")

    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"


def test_unknown_origin_gets_no_cors_header() -> None:
    response = Client().get("/api/health/", HTTP_ORIGIN="https://evil.example")

    assert "Access-Control-Allow-Origin" not in response.headers
