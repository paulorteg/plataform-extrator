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
from app.models import AuditLog, Organization, Role, User, UserOrganization
from app.organizations.dependencies import ORGANIZATION_ID_HEADER
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


def _create_organization(
    session: Session,
    status: str = "active",
    name: str = "Organization Test",
) -> Organization:
    organization = Organization(
        name=name,
        legal_name=f"{name} LTDA",
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


def _auth_headers(
    user: User,
    organization_id: str,
    request_id: str = "organizations-request-id",
):
    return {
        "Authorization": f"Bearer {_make_token(user.auth_user_id)}",
        ORGANIZATION_ID_HEADER: organization_id,
        REQUEST_ID_HEADER: request_id,
    }


def test_platform_role_can_list_all_organizations(client, db_session):
    user = _create_user(db_session)
    current_organization = _create_organization(db_session, name="Current Org")
    other_organization = _create_organization(db_session, name="Other Org")
    role = _get_role(db_session, "platform_owner")
    _link_user(db_session, user, current_organization, role)

    response = client.get(
        "/api/v1/organizations",
        headers=_auth_headers(user, current_organization.id),
    )

    assert response.status_code == 200
    ids = {organization["id"] for organization in response.json()}
    assert {current_organization.id, other_organization.id}.issubset(ids)


def test_organization_user_lists_only_current_organization(client, db_session):
    user = _create_user(db_session)
    current_organization = _create_organization(db_session)
    other_organization = _create_organization(db_session)
    role = _get_role(db_session, "organization_admin")
    _link_user(db_session, user, current_organization, role)

    response = client.get(
        "/api/v1/organizations",
        headers=_auth_headers(user, current_organization.id),
    )

    assert response.status_code == 200
    ids = {organization["id"] for organization in response.json()}
    assert ids == {current_organization.id}
    assert other_organization.id not in ids


def test_create_organization_requires_platform_permission(client, db_session):
    user = _create_user(db_session)
    current_organization = _create_organization(db_session)
    role = _get_role(db_session, "organization_admin")
    _link_user(db_session, user, current_organization, role)

    response = client.post(
        "/api/v1/organizations",
        headers=_auth_headers(user, current_organization.id, "create-denied-request"),
        json={"name": "New Organization", "legal_name": "New Organization LTDA"},
    )

    assert response.status_code == 403
    assert response.json()["request_id"] == "create-denied-request"


def test_platform_role_can_create_organization_and_audit_log(client, db_session):
    user = _create_user(db_session)
    current_organization = _create_organization(db_session)
    role = _get_role(db_session, "platform_owner")
    _link_user(db_session, user, current_organization, role)

    response = client.post(
        "/api/v1/organizations",
        headers=_auth_headers(user, current_organization.id, "create-org-request"),
        json={
            "name": "Created Org",
            "legal_name": "Created Org LTDA",
            "cnpj_hash": "hashed-cnpj",
            "retention_days": 365,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Created Org"
    assert "cnpj_hash" not in payload
    audit_log = db_session.execute(
        select(AuditLog).where(AuditLog.event_type == "organization.created")
    ).scalar_one()
    assert audit_log.request_id == "create-org-request"
    assert audit_log.user_id == user.id


def test_get_organization_blocks_cross_access(client, db_session):
    user = _create_user(db_session)
    current_organization = _create_organization(db_session)
    other_organization = _create_organization(db_session)
    role = _get_role(db_session, "organization_admin")
    _link_user(db_session, user, current_organization, role)

    response = client.get(
        f"/api/v1/organizations/{other_organization.id}",
        headers=_auth_headers(user, current_organization.id, "cross-org-request"),
    )

    assert response.status_code == 403
    assert response.json()["request_id"] == "cross-org-request"


def test_user_without_permission_receives_403(client, db_session):
    user = _create_user(db_session)
    current_organization = _create_organization(db_session)
    role = _create_role_without_permissions(db_session)
    _link_user(db_session, user, current_organization, role)

    response = client.get(
        "/api/v1/organizations",
        headers=_auth_headers(user, current_organization.id, "no-permission-request"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert response.json()["request_id"] == "no-permission-request"


def test_update_organization_generates_audit_log(client, db_session):
    user = _create_user(db_session)
    current_organization = _create_organization(db_session)
    role = _get_role(db_session, "organization_admin")
    _link_user(db_session, user, current_organization, role)

    response = client.patch(
        f"/api/v1/organizations/{current_organization.id}",
        headers=_auth_headers(user, current_organization.id, "patch-org-request"),
        json={"name": "Updated Org", "retention_days": 365},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Org"
    assert "cnpj_hash" not in response.json()
    audit_log = db_session.execute(
        select(AuditLog).where(AuditLog.event_type == "organization.updated")
    ).scalar_one()
    assert audit_log.organization_id == current_organization.id
    assert audit_log.user_id == user.id
    assert audit_log.request_id == "patch-org-request"
    assert audit_log.metadata_json == {"changed_fields": ["name", "retention_days"]}


def test_response_never_returns_cnpj_hash(client, db_session):
    user = _create_user(db_session)
    current_organization = _create_organization(db_session)
    role = _get_role(db_session, "organization_admin")
    _link_user(db_session, user, current_organization, role)

    response = client.get(
        f"/api/v1/organizations/{current_organization.id}",
        headers=_auth_headers(user, current_organization.id),
    )

    assert response.status_code == 200
    rendered_payload = str(response.json()).lower()
    assert "cnpj" not in rendered_payload
    assert current_organization.cnpj_hash not in rendered_payload
