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
from app.organizations.dependencies import ORGANIZATION_ID_HEADER
from app.permissions.dependencies import AuthorizedPermissionContext, require_permission
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

    @app.get("/api/v1/permission-context-test")
    def permission_context_test(
        context: AuthorizedPermissionContext = Depends(
            require_permission("occurrence_view")
        ),
    ):
        return {
            "auth_user_id": context.current_user.auth_user_id,
            "organization_id": context.current_organization.organization_id,
            "permission_key": context.permission_key,
        }

    @app.get("/api/v1/missing-permission-context-test")
    def missing_permission_context_test(
        context: AuthorizedPermissionContext = Depends(
            require_permission("permission_that_does_not_exist")
        ),
    ):
        return {"permission_key": context.permission_key}

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


def _get_role(session: Session, role_key: str) -> Role:
    return session.execute(select(Role).where(Role.key == role_key)).scalar_one()


def _create_role_without_permissions(session: Session) -> Role:
    role = Role(
        key=f"empty_role_{uuid4()}",
        name="Empty Role",
        scope="organization",
        status="active",
    )
    session.add(role)
    session.commit()
    session.refresh(role)
    return role


def _link_user(
    session: Session,
    user: User,
    organization: Organization,
    role_id: Optional[str],
    role_key: Optional[str] = None,
    status: str = "active",
) -> UserOrganization:
    link = UserOrganization(
        user_id=user.id,
        auth_user_id=user.auth_user_id,
        organization_id=organization.id,
        role_id=role_id,
        role_key=role_key,
        status=status,
    )
    session.add(link)
    session.commit()
    session.refresh(link)
    return link


def _auth_headers(
    user: User,
    organization_id: str,
    request_id: str = "permission-request-id",
):
    return {
        "Authorization": f"Bearer {_make_token(user.auth_user_id)}",
        ORGANIZATION_ID_HEADER: organization_id,
        REQUEST_ID_HEADER: request_id,
    }


def test_permission_guard_allows_user_with_permission(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    role = _get_role(db_session, "viewer")
    _link_user(db_session, user, organization, role.id, role.key)

    response = client.get(
        "/api/v1/permission-context-test",
        headers=_auth_headers(user, organization.id),
    )

    assert response.status_code == 200
    assert response.json() == {
        "auth_user_id": user.auth_user_id,
        "organization_id": organization.id,
        "permission_key": "occurrence_view",
    }


def test_permission_guard_rejects_user_without_permission(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    role = _create_role_without_permissions(db_session)
    _link_user(db_session, user, organization, role.id, role.key)

    response = client.get(
        "/api/v1/permission-context-test",
        headers=_auth_headers(user, organization.id, "without-permission-request"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert response.json()["request_id"] == "without-permission-request"


def test_permission_guard_rejects_user_without_role_id(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, role_id=None)

    response = client.get(
        "/api/v1/permission-context-test",
        headers=_auth_headers(user, organization.id, "without-role-request"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert response.json()["request_id"] == "without-role-request"


def test_permission_guard_rejects_invalid_role_id(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    role = _get_role(db_session, "viewer")
    link = _link_user(db_session, user, organization, role.id, role.key)

    db_session.connection().exec_driver_sql("PRAGMA foreign_keys=OFF")
    link.role_id = str(uuid4())
    db_session.commit()
    db_session.connection().exec_driver_sql("PRAGMA foreign_keys=ON")

    response = client.get(
        "/api/v1/permission-context-test",
        headers=_auth_headers(user, organization.id, "invalid-role-request"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert response.json()["request_id"] == "invalid-role-request"


def test_permission_guard_rejects_missing_permission_key(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    role = _get_role(db_session, "organization_admin")
    _link_user(db_session, user, organization, role.id, role.key)

    response = client.get(
        "/api/v1/missing-permission-context-test",
        headers=_auth_headers(user, organization.id, "missing-permission-request"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert response.json()["request_id"] == "missing-permission-request"


def test_permission_guard_keeps_inactive_link_blocked_by_organization_dependency(
    client,
    db_session,
):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    role = _get_role(db_session, "viewer")
    _link_user(db_session, user, organization, role.id, role.key, status="inactive")

    response = client.get(
        "/api/v1/permission-context-test",
        headers=_auth_headers(user, organization.id, "inactive-link-request"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "organization_not_allowed"
    assert response.json()["request_id"] == "inactive-link-request"


def test_permission_guard_keeps_inactive_organization_blocked(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session, status="inactive")
    role = _get_role(db_session, "viewer")
    _link_user(db_session, user, organization, role.id, role.key)

    response = client.get(
        "/api/v1/permission-context-test",
        headers=_auth_headers(user, organization.id, "inactive-organization-request"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "organization_not_allowed"
    assert response.json()["request_id"] == "inactive-organization-request"


def test_permission_guard_keeps_inactive_user_blocked(client, db_session):
    user = _create_user(db_session, status="inactive")
    organization = _create_organization(db_session)
    role = _get_role(db_session, "viewer")
    _link_user(db_session, user, organization, role.id, role.key)

    response = client.get(
        "/api/v1/permission-context-test",
        headers=_auth_headers(user, organization.id, "inactive-user-request"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "user_inactive"
    assert response.json()["request_id"] == "inactive-user-request"


def test_permission_guard_preserves_request_id_on_errors(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    role = _create_role_without_permissions(db_session)
    _link_user(db_session, user, organization, role.id, role.key)

    response = client.get(
        "/api/v1/permission-context-test",
        headers=_auth_headers(user, organization.id, "permission-error-request"),
    )

    assert response.status_code == 403
    assert response.headers[REQUEST_ID_HEADER] == "permission-error-request"
    assert response.json()["request_id"] == "permission-error-request"


def test_permission_guard_does_not_log_authorization_header(
    client,
    db_session,
    caplog,
):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    role = _get_role(db_session, "viewer")
    _link_user(db_session, user, organization, role.id, role.key)
    token = _make_token(user.auth_user_id)

    with caplog.at_level("INFO", logger="mercadoia.api.request"):
        response = client.get(
            "/api/v1/permission-context-test",
            headers={
                "Authorization": f"Bearer {token}",
                ORGANIZATION_ID_HEADER: organization.id,
                REQUEST_ID_HEADER: "permission-log-request",
            },
        )

    rendered_logs = caplog.text.lower()
    assert response.status_code == 200
    assert "authorization" not in rendered_logs
    assert "bearer" not in rendered_logs
    assert token.lower() not in rendered_logs


def test_permission_guard_prevents_cross_organization_access(client, db_session):
    user = _create_user(db_session)
    allowed_organization = _create_organization(db_session)
    other_organization = _create_organization(db_session)
    role = _get_role(db_session, "viewer")
    _link_user(db_session, user, allowed_organization, role.id, role.key)

    response = client.get(
        "/api/v1/permission-context-test",
        headers=_auth_headers(user, other_organization.id, "cross-org-request"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "organization_not_allowed"
    assert response.json()["request_id"] == "cross-org-request"
