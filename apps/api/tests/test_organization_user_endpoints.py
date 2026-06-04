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


def _create_organization(session: Session) -> Organization:
    organization = Organization(
        name="Organization Test",
        legal_name="Organization Test LTDA",
        cnpj_hash=f"hash_{uuid4()}",
        status="active",
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
) -> UserOrganization:
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
    organization_id: str,
    request_id: str = "users-request-id",
):
    return {
        "Authorization": f"Bearer {_make_token(user.auth_user_id)}",
        ORGANIZATION_ID_HEADER: organization_id,
        REQUEST_ID_HEADER: request_id,
    }


def test_admin_lists_users_from_current_organization(client, db_session):
    admin = _create_user(db_session)
    organization = _create_organization(db_session)
    other_organization = _create_organization(db_session)
    member = _create_user(db_session)
    other_member = _create_user(db_session)
    role = _get_role(db_session, "organization_admin")
    viewer = _get_role(db_session, "viewer")
    _link_user(db_session, admin, organization, role)
    _link_user(db_session, member, organization, viewer)
    _link_user(db_session, other_member, other_organization, viewer)

    response = client.get(
        "/api/v1/users",
        headers=_auth_headers(admin, organization.id),
    )

    assert response.status_code == 200
    ids = {user["id"] for user in response.json()}
    assert ids == {admin.id, member.id}
    assert other_member.id not in ids


def test_user_without_permission_receives_403(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    role = _create_role_without_permissions(db_session)
    _link_user(db_session, user, organization, role)

    response = client.get(
        "/api/v1/users",
        headers=_auth_headers(user, organization.id, "users-no-permission"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert response.json()["request_id"] == "users-no-permission"


def test_invitation_creates_pending_internal_user_without_password(client, db_session):
    admin = _create_user(db_session)
    organization = _create_organization(db_session)
    role = _get_role(db_session, "organization_admin")
    _link_user(db_session, admin, organization, role)

    response = client.post(
        "/api/v1/users/invitations",
        headers=_auth_headers(admin, organization.id, "invite-request"),
        json={
            "email": "new.user@example.test",
            "name": "New User",
            "role_key": "viewer",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["email"] == "new.user@example.test"
    assert payload["status"] == "invited"
    assert payload["organization_status"] == "invited"
    rendered_payload = str(payload).lower()
    assert "password" not in rendered_payload
    audit_log = db_session.execute(
        select(AuditLog).where(AuditLog.event_type == "user.invited")
    ).scalar_one()
    assert audit_log.request_id == "invite-request"


def test_role_change_requires_permission(client, db_session):
    user = _create_user(db_session)
    target = _create_user(db_session)
    organization = _create_organization(db_session)
    role = _get_role(db_session, "viewer")
    _link_user(db_session, user, organization, role)
    _link_user(db_session, target, organization, role)

    response = client.patch(
        f"/api/v1/users/{target.id}/role",
        headers=_auth_headers(user, organization.id, "role-denied-request"),
        json={"role_key": "manager"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert response.json()["request_id"] == "role-denied-request"


def test_role_change_generates_audit_log(client, db_session):
    admin = _create_user(db_session)
    target = _create_user(db_session)
    organization = _create_organization(db_session)
    role = _get_role(db_session, "organization_admin")
    viewer = _get_role(db_session, "viewer")
    _link_user(db_session, admin, organization, role)
    _link_user(db_session, target, organization, viewer)

    response = client.patch(
        f"/api/v1/users/{target.id}/role",
        headers=_auth_headers(admin, organization.id, "role-change-request"),
        json={"role_key": "manager"},
    )

    assert response.status_code == 200
    assert response.json()["role"]["key"] == "manager"
    audit_log = db_session.execute(
        select(AuditLog).where(AuditLog.event_type == "user.role_changed")
    ).scalar_one()
    assert audit_log.user_id == admin.id
    assert audit_log.target_id == target.id
    assert audit_log.request_id == "role-change-request"


def test_block_requires_permission(client, db_session):
    user = _create_user(db_session)
    target = _create_user(db_session)
    organization = _create_organization(db_session)
    role = _get_role(db_session, "viewer")
    _link_user(db_session, user, organization, role)
    _link_user(db_session, target, organization, role)

    response = client.post(
        f"/api/v1/users/{target.id}/block",
        headers=_auth_headers(user, organization.id, "block-denied-request"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert response.json()["request_id"] == "block-denied-request"


def test_block_generates_audit_log(client, db_session):
    admin = _create_user(db_session)
    target = _create_user(db_session)
    organization = _create_organization(db_session)
    role = _get_role(db_session, "organization_admin")
    viewer = _get_role(db_session, "viewer")
    _link_user(db_session, admin, organization, role)
    _link_user(db_session, target, organization, viewer)

    response = client.post(
        f"/api/v1/users/{target.id}/block",
        headers=_auth_headers(admin, organization.id, "block-request"),
    )

    assert response.status_code == 200
    assert response.json()["organization_status"] == "blocked"
    audit_log = db_session.execute(
        select(AuditLog).where(AuditLog.event_type == "user.blocked")
    ).scalar_one()
    assert audit_log.user_id == admin.id
    assert audit_log.target_id == target.id
    assert audit_log.request_id == "block-request"


def test_cross_organization_user_access_is_blocked(client, db_session):
    admin = _create_user(db_session)
    target = _create_user(db_session)
    organization = _create_organization(db_session)
    other_organization = _create_organization(db_session)
    role = _get_role(db_session, "organization_admin")
    viewer = _get_role(db_session, "viewer")
    _link_user(db_session, admin, organization, role)
    _link_user(db_session, target, other_organization, viewer)

    response = client.patch(
        f"/api/v1/users/{target.id}/role",
        headers=_auth_headers(admin, organization.id, "cross-user-request"),
        json={"role_key": "manager"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "user_access_denied"
    assert response.json()["request_id"] == "cross-user-request"


def test_no_password_fields_are_stored_after_invitation(client, db_session):
    admin = _create_user(db_session)
    organization = _create_organization(db_session)
    role = _get_role(db_session, "organization_admin")
    _link_user(db_session, admin, organization, role)

    response = client.post(
        "/api/v1/users/invitations",
        headers=_auth_headers(admin, organization.id),
        json={
            "email": "safe.user@example.test",
            "name": "Safe User",
            "role_key": "viewer",
        },
    )

    assert response.status_code == 201
    users_table_columns = set(User.__table__.columns.keys())
    assert "password" not in users_table_columns
    assert "password_hash" not in users_table_columns
    assert "senha" not in users_table_columns
