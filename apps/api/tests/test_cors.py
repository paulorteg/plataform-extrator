from fastapi.testclient import TestClient

from app.core.config import LOCAL_CORS_ALLOWED_ORIGINS, get_cors_allowed_origins
from app.main import create_app


def test_local_cors_defaults_are_safe(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("APP_ENV", "local")

    assert get_cors_allowed_origins() == list(LOCAL_CORS_ALLOWED_ORIGINS)


def test_production_cors_defaults_to_closed(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("APP_ENV", "production")

    assert get_cors_allowed_origins() == []


def test_cors_preflight_allows_local_frontend_origin(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("APP_ENV", "local")

    response = TestClient(create_app()).options(
        "/api/v1/auth/me",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization,X-Organization-Id",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "Authorization" in response.headers["access-control-allow-headers"]
    assert "X-Organization-Id" in response.headers["access-control-allow-headers"]
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_does_not_allow_unconfigured_origin(monkeypatch):
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("APP_ENV", "local")

    response = TestClient(create_app()).options(
        "/api/v1/auth/me",
        headers={
            "Origin": "https://example.invalid",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization,X-Organization-Id",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
