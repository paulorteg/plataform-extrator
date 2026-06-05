import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jwt.utils import base64url_encode
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth import CurrentUser, get_current_user
from app.auth import jwt as auth_jwt
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


def _base64url_uint(value: int) -> str:
    byte_length = (value.bit_length() + 7) // 8
    return base64url_encode(value.to_bytes(byte_length, "big")).decode("ascii")


def _make_es256_key_context(kid: str = "test-es256-key") -> tuple[ec.EllipticCurvePrivateKey, dict]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": _base64url_uint(public_numbers.x),
        "y": _base64url_uint(public_numbers.y),
        "alg": "ES256",
        "use": "sig",
        "kid": kid,
    }
    return private_key, jwk


def _make_es256_token(
    private_key: ec.EllipticCurvePrivateKey,
    kid: str,
    auth_user_id: str,
    expires_delta: timedelta = timedelta(minutes=5),
    issuer: str = f"{TEST_SUPABASE_URL}/auth/v1",
    audience: str = "authenticated",
    include_subject: bool = True,
) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "aud": audience,
        "iss": issuer,
        "iat": now,
        "exp": now + expires_delta,
    }
    if include_subject:
        claims["sub"] = auth_user_id

    return jwt.encode(
        claims,
        private_key,
        algorithm="ES256",
        headers={"kid": kid},
    )


def _mock_jwks(monkeypatch, jwk: dict) -> None:
    auth_jwt.clear_jwks_cache()
    monkeypatch.setattr(auth_jwt, "_fetch_jwks", lambda url: {"keys": [jwk]})


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


def test_es256_jwks_token_is_accepted(monkeypatch):
    kid = "test-es256-key"
    private_key, jwk = _make_es256_key_context(kid)
    _mock_jwks(monkeypatch, jwk)
    auth_user_id = str(uuid4())
    token = _make_es256_token(private_key, kid, auth_user_id)

    claims = decode_supabase_jwt(token, TEST_JWT_SECRET, TEST_SUPABASE_URL)

    assert claims.auth_user_id == auth_user_id


def test_es256_jwks_token_with_unknown_kid_is_rejected(monkeypatch):
    private_key, jwk = _make_es256_key_context("known-key")
    _mock_jwks(monkeypatch, jwk)
    token = _make_es256_token(private_key, "unknown-key", str(uuid4()))

    with pytest.raises(AuthError) as exc_info:
        decode_supabase_jwt(token, TEST_JWT_SECRET, TEST_SUPABASE_URL)

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "invalid_token"


def test_es256_jwks_token_with_invalid_issuer_is_rejected(monkeypatch):
    kid = "test-es256-key"
    private_key, jwk = _make_es256_key_context(kid)
    _mock_jwks(monkeypatch, jwk)
    token = _make_es256_token(
        private_key,
        kid,
        str(uuid4()),
        issuer="https://wrong-project.supabase.co/auth/v1",
    )

    with pytest.raises(AuthError) as exc_info:
        decode_supabase_jwt(token, TEST_JWT_SECRET, TEST_SUPABASE_URL)

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "invalid_token"


def test_es256_jwks_token_with_invalid_audience_is_rejected(monkeypatch):
    kid = "test-es256-key"
    private_key, jwk = _make_es256_key_context(kid)
    _mock_jwks(monkeypatch, jwk)
    token = _make_es256_token(private_key, kid, str(uuid4()), audience="anon")

    with pytest.raises(AuthError) as exc_info:
        decode_supabase_jwt(token, TEST_JWT_SECRET, TEST_SUPABASE_URL)

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "invalid_token"


def test_es256_jwks_expired_token_returns_controlled_error(monkeypatch):
    kid = "test-es256-key"
    private_key, jwk = _make_es256_key_context(kid)
    _mock_jwks(monkeypatch, jwk)
    token = _make_es256_token(
        private_key,
        kid,
        str(uuid4()),
        expires_delta=timedelta(minutes=-1),
    )

    with pytest.raises(AuthError) as exc_info:
        decode_supabase_jwt(token, TEST_JWT_SECRET, TEST_SUPABASE_URL)

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "token_expired"


def test_es256_jwks_token_without_subject_is_rejected(monkeypatch):
    kid = "test-es256-key"
    private_key, jwk = _make_es256_key_context(kid)
    _mock_jwks(monkeypatch, jwk)
    token = _make_es256_token(
        private_key,
        kid,
        str(uuid4()),
        include_subject=False,
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
