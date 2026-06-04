import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import CurrentUser, get_current_user
from app.auth.dependencies import get_database_session
from app.auth.errors import AuthError, auth_exception_handler
from app.auth.jwt import decode_supabase_jwt
from app.db.base import Base
from app.middleware.request_context import REQUEST_ID_HEADER, RequestContextMiddleware
from app.models import User


TEST_JWT_SECRET = "test-jwt-secret-with-at-least-32-bytes"
TEST_SUPABASE_URL = "https://example.supabase.co"


@pytest.fixture
def db_session(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("SUPABASE_DB_URL", "sqlite:///:memory:")
    monkeypatch.setenv("SUPABASE_URL", TEST_SUPABASE_URL)
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET_DOCUMENTS", "documents")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET_TEMPLATES", "templates")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET_ARTIFACTS", "artifacts")

    from app.core.config import get_settings

    get_settings.cache_clear()

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    get_settings.cache_clear()


@pytest.fixture
def protected_client(db_session):
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(AuthError, auth_exception_handler)

    def override_get_database_session():
        yield db_session

    app.dependency_overrides[get_database_session] = override_get_database_session

    @app.get("/protected")
    def protected(current_user: CurrentUser = Depends(get_current_user)):
        return {
            "auth_user_id": current_user.auth_user_id,
            "user_id": current_user.user.id,
        }

    return TestClient(app)


def _create_user(session: Session, auth_user_id: str, status: str = "active") -> User:
    user = User(
        auth_user_id=auth_user_id,
        name="User Test",
        email=f"{auth_user_id}@example.test",
        status=status,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _make_token(auth_user_id: str, expires_delta: timedelta = timedelta(minutes=5)) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": auth_user_id,
            "aud": "authenticated",
            "iss": f"{TEST_SUPABASE_URL}/auth/v1",
            "iat": now,
            "exp": now + expires_delta,
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )


def test_missing_token_returns_controlled_error(protected_client):
    response = protected_client.get(
        "/protected",
        headers={REQUEST_ID_HEADER: "auth-request-1"},
    )

    assert response.status_code == 401
    assert response.headers[REQUEST_ID_HEADER] == "auth-request-1"
    assert response.json()["code"] == "missing_token"
    assert response.json()["request_id"] == "auth-request-1"


def test_invalid_token_returns_controlled_error(protected_client):
    response = protected_client.get(
        "/protected",
        headers={
            "Authorization": "Bearer invalid-token",
            REQUEST_ID_HEADER: "auth-request-2",
        },
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"
    assert response.json()["request_id"] == "auth-request-2"


def test_expired_token_returns_controlled_error(protected_client):
    token = _make_token(str(uuid4()), expires_delta=timedelta(minutes=-1))

    response = protected_client.get(
        "/protected",
        headers={
            "Authorization": f"Bearer {token}",
            REQUEST_ID_HEADER: "auth-request-3",
        },
    )

    assert response.status_code == 401
    assert response.json()["code"] == "token_expired"
    assert response.json()["request_id"] == "auth-request-3"


def test_token_without_subject_is_rejected():
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "aud": "authenticated",
            "iss": f"{TEST_SUPABASE_URL}/auth/v1",
            "exp": now + timedelta(minutes=5),
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(AuthError) as exc_info:
        decode_supabase_jwt(token, TEST_JWT_SECRET, TEST_SUPABASE_URL)

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "invalid_token"


def test_valid_token_resolves_active_internal_user(protected_client, db_session):
    auth_user_id = str(uuid4())
    user = _create_user(db_session, auth_user_id)
    token = _make_token(auth_user_id)

    response = protected_client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "auth_user_id": auth_user_id,
        "user_id": user.id,
    }


def test_inactive_internal_user_is_denied(protected_client, db_session):
    auth_user_id = str(uuid4())
    _create_user(db_session, auth_user_id, status="inactive")
    token = _make_token(auth_user_id)

    response = protected_client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "user_inactive"


def test_unknown_internal_user_is_denied(protected_client):
    token = _make_token(str(uuid4()))

    response = protected_client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "user_not_found"


def test_auth_logs_do_not_include_authorization_or_token(
    protected_client,
    db_session,
    caplog,
):
    auth_user_id = str(uuid4())
    _create_user(db_session, auth_user_id)
    token = _make_token(auth_user_id)
    caplog.set_level(logging.INFO, logger="mercadoia.api.request")

    response = protected_client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    rendered_records = "\n".join(str(record.__dict__) for record in caplog.records)
    messages = "\n".join(record.getMessage() for record in caplog.records)

    assert token not in rendered_records
    assert token not in messages
    assert "Authorization" not in rendered_records
    assert "Authorization" not in messages
