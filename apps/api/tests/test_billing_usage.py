from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_database_session
from app.db.base import Base
from app.main import create_app
from app.middleware.request_context import REQUEST_ID_HEADER
from app.models import (
    AuditLog,
    Organization,
    OrganizationPackage,
    Package,
    Plan,
    Role,
    Subscription,
    UsageEvent,
    User,
    UserOrganization,
)
from app.organizations.dependencies import ORGANIZATION_ID_HEADER
from app.seeds.roles_permissions import seed_roles_permissions
from app.usage.service import (
    UsageIdempotencyConflictError,
    UsageLimitExceededError,
    get_usage_balance,
    register_occurrence_usage,
)


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


def _create_user(session: Session) -> User:
    auth_user_id = str(uuid4())
    user = User(
        auth_user_id=auth_user_id,
        name="User Test",
        email=f"{auth_user_id}@example.test",
        status="active",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _create_organization(session: Session, status: str = "active") -> Organization:
    organization = Organization(
        name=f"Organization {uuid4()}",
        legal_name="Organization LTDA",
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


def _link_user(
    session: Session,
    user: User,
    organization: Organization,
    role: Role,
) -> None:
    session.add(
        UserOrganization(
            user_id=user.id,
            auth_user_id=user.auth_user_id,
            organization_id=organization.id,
            role_id=role.id,
            role_key=role.key,
            status="active",
        )
    )
    session.commit()


def _auth_headers(user: User, organization_id: str, request_id: str = "billing-request"):
    return {
        "Authorization": f"Bearer {_make_token(user.auth_user_id)}",
        ORGANIZATION_ID_HEADER: organization_id,
        REQUEST_ID_HEADER: request_id,
    }


def _create_plan(
    session: Session,
    key: str = "basic",
    monthly_analysis_limit: int = 10,
    allow_overage: bool = False,
) -> Plan:
    plan = Plan(
        key=f"{key}_{uuid4()}",
        name="Basic Plan",
        monthly_analysis_limit=monthly_analysis_limit,
        allow_overage=allow_overage,
        status="active",
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def _create_package(session: Session, quota: int = 5) -> Package:
    package = Package(
        key=f"package_{uuid4()}",
        name="Usage Package",
        analysis_quota=quota,
        entitlements={"document_upload": True},
        status="active",
    )
    session.add(package)
    session.commit()
    session.refresh(package)
    return package


def test_billing_models_enforce_unique_plan_package_and_usage_keys(db_session):
    plan_key = f"plan_{uuid4()}"
    package_key = f"package_{uuid4()}"
    organization = _create_organization(db_session)
    plan = Plan(key=plan_key, name="Plan", status="active", allow_overage=False)
    package = Package(
        key=package_key,
        name="Package",
        status="active",
        analysis_quota=1,
        entitlements={},
    )
    db_session.add_all([plan, package])
    db_session.commit()

    db_session.add(Plan(key=plan_key, name="Plan Copy", status="active", allow_overage=False))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    db_session.add(
        Package(
            key=package_key,
            name="Package Copy",
            status="active",
            analysis_quota=1,
            entitlements={},
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()

    db_session.add(
        UsageEvent(
            organization_id=organization.id,
            occurrence_id="occ-1",
            event_type="occurrence_extracted",
            amount=1,
            idempotency_key="same-key",
            metadata_json={},
        )
    )
    db_session.flush()
    db_session.add(
        UsageEvent(
            organization_id=organization.id,
            occurrence_id="occ-2",
            event_type="occurrence_extracted",
            amount=1,
            idempotency_key="same-key",
            metadata_json={},
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_platform_role_can_create_plan_package_subscription_and_assignment(client, db_session):
    user = _create_user(db_session)
    current_organization = _create_organization(db_session)
    target_organization = _create_organization(db_session)
    _link_user(db_session, user, current_organization, _get_role(db_session, "platform_owner"))

    plan_response = client.post(
        "/api/v1/plans",
        headers=_auth_headers(user, current_organization.id, "create-plan-request"),
        json={
            "key": "starter",
            "name": "Starter",
            "monthly_analysis_limit": 10,
            "allow_overage": False,
        },
    )
    assert plan_response.status_code == 201
    plan_id = plan_response.json()["id"]

    package_response = client.post(
        "/api/v1/packages",
        headers=_auth_headers(user, current_organization.id, "create-package-request"),
        json={
            "key": "starter-extra",
            "name": "Starter Extra",
            "analysis_quota": 5,
            "plan_id": plan_id,
            "entitlements": {"document_upload": True},
        },
    )
    assert package_response.status_code == 201
    package_id = package_response.json()["id"]

    subscription_response = client.post(
        f"/api/v1/plans/{plan_id}/subscriptions",
        headers=_auth_headers(user, current_organization.id, "subscription-request"),
        json={"organization_id": target_organization.id},
    )
    assert subscription_response.status_code == 201
    assert subscription_response.json()["organization_id"] == target_organization.id

    assignment_response = client.post(
        f"/api/v1/packages/{package_id}/assignments",
        headers=_auth_headers(user, current_organization.id, "assignment-request"),
        json={"organization_id": target_organization.id},
    )
    assert assignment_response.status_code == 201
    assert assignment_response.json()["assigned_analysis_quota"] == 5

    event_types = set(db_session.execute(select(AuditLog.event_type)).scalars())
    assert {
        "plan.created",
        "package.created",
        "subscription.created",
        "package.assigned",
    }.issubset(event_types)


def test_organization_role_cannot_manage_billing(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, _get_role(db_session, "organization_admin"))

    response = client.post(
        "/api/v1/plans",
        headers=_auth_headers(user, organization.id, "plan-denied-request"),
        json={"key": "denied", "name": "Denied", "monthly_analysis_limit": 1},
    )

    assert response.status_code == 403
    assert response.json()["request_id"] == "plan-denied-request"


def test_usage_service_registers_consumption_once_and_sanitizes_metadata(db_session):
    organization = _create_organization(db_session)
    package = _create_package(db_session, quota=2)
    db_session.add(
        OrganizationPackage(
            organization_id=organization.id,
            package_id=package.id,
            assigned_analysis_quota=2,
            status="active",
        )
    )
    db_session.commit()

    first = register_occurrence_usage(
        db_session,
        organization_id=organization.id,
        occurrence_id="occ-1",
        request_id="usage-service-request",
        metadata={"token": "secret-token", "source": "pipeline"},
    )
    assert first.created is True

    second = register_occurrence_usage(
        db_session,
        organization_id=organization.id,
        occurrence_id="occ-1",
        request_id="usage-service-request",
        metadata={"token": "secret-token"},
    )
    assert second.created is False
    assert second.event.id == first.event.id

    event = db_session.execute(select(UsageEvent)).scalar_one()
    assert event.metadata_json["token"] == "[REDACTED]"
    assert event.metadata_json["source"] == "pipeline"
    balance = get_usage_balance(db_session, organization.id)
    assert balance.used == 1
    assert balance.available == 1


def test_usage_service_blocks_when_balance_is_insufficient(db_session):
    organization = _create_organization(db_session)

    with pytest.raises(UsageLimitExceededError):
        register_occurrence_usage(
            db_session,
            organization_id=organization.id,
            occurrence_id="occ-without-balance",
        )


def test_usage_service_blocks_cross_organization_idempotency_key_collision(db_session):
    organization = _create_organization(db_session)
    other_organization = _create_organization(db_session)
    package = _create_package(db_session, quota=2)
    db_session.add_all(
        [
            OrganizationPackage(
                organization_id=organization.id,
                package_id=package.id,
                assigned_analysis_quota=2,
                status="active",
            ),
            OrganizationPackage(
                organization_id=other_organization.id,
                package_id=package.id,
                assigned_analysis_quota=2,
                status="active",
            ),
        ]
    )
    db_session.commit()

    register_occurrence_usage(
        db_session,
        organization_id=organization.id,
        occurrence_id="occ-1",
        idempotency_key="shared-key",
    )

    with pytest.raises(UsageIdempotencyConflictError):
        register_occurrence_usage(
            db_session,
            organization_id=other_organization.id,
            occurrence_id="occ-2",
            idempotency_key="shared-key",
        )


def test_usage_api_returns_balance_events_and_availability_for_current_organization(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    other_organization = _create_organization(db_session)
    _link_user(db_session, user, organization, _get_role(db_session, "organization_admin"))
    package = _create_package(db_session, quota=2)
    db_session.add_all(
        [
            OrganizationPackage(
                organization_id=organization.id,
                package_id=package.id,
                assigned_analysis_quota=2,
                status="active",
            ),
            OrganizationPackage(
                organization_id=other_organization.id,
                package_id=package.id,
                assigned_analysis_quota=10,
                status="active",
            ),
            UsageEvent(
                organization_id=other_organization.id,
                occurrence_id="other-occurrence",
                event_type="occurrence_extracted",
                amount=1,
                idempotency_key="other-key",
                metadata_json={},
            ),
        ]
    )
    db_session.commit()

    result = register_occurrence_usage(
        db_session,
        organization_id=organization.id,
        occurrence_id="occ-1",
        request_id="usage-create-request",
        metadata={"prompt": "do not store"},
    )
    db_session.commit()
    assert result.created is True
    event = db_session.execute(
        select(UsageEvent).where(UsageEvent.organization_id == organization.id)
    ).scalar_one()
    assert event.metadata_json["prompt"] == "[REDACTED]"

    balance_response = client.get(
        "/api/v1/usage/balance",
        headers=_auth_headers(user, organization.id),
    )
    assert balance_response.status_code == 200
    assert balance_response.json()["used"] == 1
    assert balance_response.json()["available"] == 1

    events_response = client.get(
        "/api/v1/usage/events",
        headers=_auth_headers(user, organization.id),
    )
    assert events_response.status_code == 200
    assert [event["occurrence_id"] for event in events_response.json()] == ["occ-1"]

    availability_response = client.get(
        "/api/v1/usage/availability?amount=2",
        headers=_auth_headers(user, organization.id),
    )
    assert availability_response.status_code == 200
    assert availability_response.json()["available"] is False
