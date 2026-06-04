from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import jwt
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_database_session
from app.db.base import Base
from app.main import create_app
from app.middleware.request_context import REQUEST_ID_HEADER
from app.models import Organization, Role, User, UserOrganization
from app.organizations.dependencies import (
    ORGANIZATION_ID_HEADER,
    CurrentOrganizationContext,
    get_current_organization,
)
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

    @app.get("/api/v1/organization-context-test")
    def organization_context_test(
        context: CurrentOrganizationContext = Depends(get_current_organization),
    ):
        return {
            "organization_id": context.organization_id,
            "user_organization_id": context.user_organization.id,
        }

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
        cnpj_hash=f"hash_{uuid4()}",
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
    status: str = "active",
) -> UserOrganization:
    role = session.execute(select(Role).where(Role.key == "viewer")).scalar_one()
    link = UserOrganization(
        user_id=user.id,
        auth_user_id=user.auth_user_id,
        organization_id=organization.id,
        role_id=role.id,
        role_key=role.key,
        status=status,
    )
    session.add(link)
    session.commit()
    session.refresh(link)
    return link


def _auth_headers(
    user: User,
    organization_id: Optional[str],
    request_id: str = "organization-request-id",
):
    headers = {
        "Authorization": f"Bearer {_make_token(user.auth_user_id)}",
        REQUEST_ID_HEADER: request_id,
    }
    if organization_id is not None:
        headers[ORGANIZATION_ID_HEADER] = organization_id
    return headers


def test_current_organization_accepts_active_link_and_active_organization(
    client,
    db_session,
):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    link = _link_user(db_session, user, organization)

    response = client.get(
        "/api/v1/organization-context-test",
        headers=_auth_headers(user, organization.id),
    )

    assert response.status_code == 200
    assert response.json() == {
        "organization_id": organization.id,
        "user_organization_id": link.id,
    }
    assert response.headers[REQUEST_ID_HEADER] == "organization-request-id"


def test_current_organization_requires_header(client, db_session):
    user = _create_user(db_session)

    response = client.get(
        "/api/v1/organization-context-test",
        headers=_auth_headers(user, None, "missing-org-request"),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "missing_organization"
    assert response.json()["request_id"] == "missing-org-request"


def test_current_organization_rejects_invalid_uuid_header(client, db_session):
    user = _create_user(db_session)

    response = client.get(
        "/api/v1/organization-context-test",
        headers=_auth_headers(user, "not-a-uuid", "invalid-org-request"),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_organization"
    assert response.json()["request_id"] == "invalid-org-request"


def test_current_organization_rejects_unknown_organization(client, db_session):
    user = _create_user(db_session)

    response = client.get(
        "/api/v1/organization-context-test",
        headers=_auth_headers(user, str(uuid4()), "unknown-org-request"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "organization_not_allowed"
    assert response.json()["request_id"] == "unknown-org-request"


@pytest.mark.parametrize("status", ["inactive", "suspended", "blocked", "archived"])
def test_current_organization_rejects_inactive_organization(
    client,
    db_session,
    status,
):
    user = _create_user(db_session)
    organization = _create_organization(db_session, status=status)
    _link_user(db_session, user, organization)

    response = client.get(
        "/api/v1/organization-context-test",
        headers=_auth_headers(user, organization.id, "inactive-org-request"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "organization_not_allowed"
    assert response.json()["request_id"] == "inactive-org-request"


def test_current_organization_rejects_user_without_link(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)

    response = client.get(
        "/api/v1/organization-context-test",
        headers=_auth_headers(user, organization.id, "no-link-request"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "organization_not_allowed"
    assert response.json()["request_id"] == "no-link-request"


def test_current_organization_rejects_inactive_user_link(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, status="inactive")

    response = client.get(
        "/api/v1/organization-context-test",
        headers=_auth_headers(user, organization.id, "inactive-link-request"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "organization_not_allowed"
    assert response.json()["request_id"] == "inactive-link-request"


def test_current_organization_keeps_user_inactive_block_in_auth_dependency(
    client,
    db_session,
):
    user = _create_user(db_session, status="inactive")
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization)

    response = client.get(
        "/api/v1/organization-context-test",
        headers=_auth_headers(user, organization.id, "inactive-user-request"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "user_inactive"
    assert response.json()["request_id"] == "inactive-user-request"


def test_current_organization_prevents_cross_organization_access(client, db_session):
    user = _create_user(db_session)
    allowed_organization = _create_organization(db_session)
    other_organization = _create_organization(db_session)
    _link_user(db_session, user, allowed_organization)

    response = client.get(
        "/api/v1/organization-context-test",
        headers=_auth_headers(user, other_organization.id, "cross-org-request"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "organization_not_allowed"
    assert response.json()["request_id"] == "cross-org-request"


def test_current_organization_does_not_log_authorization_header(
    client,
    db_session,
    caplog,
):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization)
    token = _make_token(user.auth_user_id)

    with caplog.at_level("INFO", logger="mercadoia.api.request"):
        response = client.get(
            "/api/v1/organization-context-test",
            headers={
                "Authorization": f"Bearer {token}",
                ORGANIZATION_ID_HEADER: organization.id,
                REQUEST_ID_HEADER: "log-safety-request",
            },
        )

    rendered_logs = caplog.text.lower()
    assert response.status_code == 200
    assert "authorization" not in rendered_logs
    assert "bearer" not in rendered_logs
    assert token.lower() not in rendered_logs
