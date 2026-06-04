from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_database_session
from app.db.base import Base
from app.main import create_app
from app.middleware.request_context import REQUEST_ID_HEADER
from app.models import Organization, Role, User, UserOrganization
from app.seeds.roles_permissions import seed_roles_permissions


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
        seed_roles_permissions(session.connection())
        session.commit()
        yield session

    get_settings.cache_clear()


@pytest.fixture
def client(db_session):
    app = create_app()

    def override_get_database_session():
        yield db_session

    app.dependency_overrides[get_database_session] = override_get_database_session
    return TestClient(app)


def _make_token(auth_user_id: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": auth_user_id,
            "aud": "authenticated",
            "iss": f"{TEST_SUPABASE_URL}/auth/v1",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )


def _create_user(session: Session, status: str = "active") -> User:
    auth_user_id = str(uuid4())
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


def _create_organization(session: Session, status: str = "active") -> Organization:
    organization = Organization(
        name="Organization Test",
        legal_name="Organization Test LTDA",
        cnpj_hash="hash_cnpj_test",
        status=status,
        retention_days=180,
    )
    session.add(organization)
    session.commit()
    session.refresh(organization)
    return organization


def _link_user(
    session: Session,
    user: User,
    organization: Organization,
    role: Role,
    status: str = "active",
) -> None:
    session.add(
        UserOrganization(
            user_id=user.id,
            auth_user_id=user.auth_user_id,
            organization_id=organization.id,
            role_id=role.id,
            role_key=role.key,
            status=status,
        )
    )
    session.commit()


def test_auth_me_returns_user_organizations_role_and_permissions(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    role = db_session.execute(
        select(Role).where(Role.key == "organization_admin")
    ).scalar_one()
    _link_user(db_session, user, organization, role)
    token = _make_token(user.auth_user_id)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"] == {
        "id": user.id,
        "auth_user_id": user.auth_user_id,
        "name": user.name,
        "email": user.email,
        "status": "active",
    }
    assert payload["organizations"][0]["id"] == organization.id
    assert payload["organizations"][0]["name"] == organization.name
    assert payload["organizations"][0]["role"]["key"] == "organization_admin"
    assert "document_view" in payload["organizations"][0]["permissions"]
    assert "audit_view" in payload["organizations"][0]["permissions"]


def test_auth_me_filters_inactive_links_and_organizations(client, db_session):
    user = _create_user(db_session)
    role = db_session.execute(select(Role).where(Role.key == "viewer")).scalar_one()
    active_org = _create_organization(db_session)
    inactive_org = _create_organization(db_session, status="inactive")
    link_inactive_org = _create_organization(db_session)
    _link_user(db_session, user, active_org, role)
    _link_user(db_session, user, inactive_org, role)
    _link_user(db_session, user, link_inactive_org, role, status="inactive")
    token = _make_token(user.auth_user_id)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    organization_ids = {organization["id"] for organization in response.json()["organizations"]}
    assert organization_ids == {active_org.id}


def test_auth_me_without_token_returns_401(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={REQUEST_ID_HEADER: "auth-me-request-1"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "missing_token"
    assert response.json()["request_id"] == "auth-me-request-1"


def test_auth_me_inactive_user_returns_403(client, db_session):
    user = _create_user(db_session, status="inactive")
    token = _make_token(user.auth_user_id)

    response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
            REQUEST_ID_HEADER: "auth-me-request-2",
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "user_inactive"
    assert response.json()["request_id"] == "auth-me-request-2"


def test_auth_me_does_not_return_tokens_or_secrets(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    role = db_session.execute(select(Role).where(Role.key == "viewer")).scalar_one()
    _link_user(db_session, user, organization, role)
    token = _make_token(user.auth_user_id)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    rendered_payload = str(response.json()).lower()
    assert response.status_code == 200
    assert "password" not in rendered_payload
    assert "service_role" not in rendered_payload
    assert "jwt_secret" not in rendered_payload
    assert token.lower() not in rendered_payload
