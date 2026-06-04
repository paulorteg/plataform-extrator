import logging
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api_errors import unhandled_exception_handler
from app.middleware.request_context import REQUEST_ID_HEADER, RequestContextMiddleware


def test_generates_request_id_when_missing():
    from app.main import app

    response = TestClient(app).get("/health")

    request_id = response.headers[REQUEST_ID_HEADER]
    assert UUID(request_id)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_reuses_valid_request_id():
    from app.main import app

    response = TestClient(app).get("/health", headers={REQUEST_ID_HEADER: "client-request-1"})

    assert response.headers[REQUEST_ID_HEADER] == "client-request-1"


def test_replaces_invalid_request_id():
    from app.main import app

    response = TestClient(app).get("/health", headers={REQUEST_ID_HEADER: "bad request id"})

    assert response.headers[REQUEST_ID_HEADER] != "bad request id"
    assert UUID(response.headers[REQUEST_ID_HEADER])


def test_unhandled_error_response_includes_request_id():
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.get("/boom")
    def boom():
        raise RuntimeError("sensitive internal detail")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom", headers={REQUEST_ID_HEADER: "error-request-1"})

    assert response.status_code == 500
    assert response.headers[REQUEST_ID_HEADER] == "error-request-1"
    assert response.json() == {
        "code": "internal_server_error",
        "message": "Internal server error.",
        "details": {},
        "request_id": "error-request-1",
    }


def test_request_log_excludes_body_and_authorization(caplog):
    from app.main import app

    caplog.set_level(logging.INFO, logger="mercadoia.api.request")

    response = TestClient(app).get(
        "/health",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200

    messages = "\n".join(record.getMessage() for record in caplog.records)
    rendered_records = "\n".join(str(record.__dict__) for record in caplog.records)

    assert "secret-token" not in messages
    assert "secret-token" not in rendered_records
    assert "Authorization" not in messages
    assert "Authorization" not in rendered_records
    assert "body" not in messages.lower()
