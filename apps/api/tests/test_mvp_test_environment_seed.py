from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import (
    Organization,
    OrganizationPackage,
    Package,
    Plan,
    Role,
    Subscription,
    User,
    UserOrganization,
)
from app.seeds.mvp_test_environment import (
    REQUIRED_MVP_PERMISSION_KEYS,
    MvpTestSeedConfig,
    config_from_env,
    seed_mvp_test_environment,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


def _config() -> MvpTestSeedConfig:
    return MvpTestSeedConfig(auth_user_id=str(uuid4()))


def test_mvp_test_seed_creates_minimal_environment(db_session):
    result = seed_mvp_test_environment(db_session, _config())

    organization = db_session.get(Organization, result.organization_id)
    user = db_session.get(User, result.user_id)
    user_organization = db_session.get(UserOrganization, result.user_organization_id)
    plan = db_session.get(Plan, result.plan_id)
    package = db_session.get(Package, result.package_id)
    subscription = db_session.get(Subscription, result.subscription_id)
    organization_package = db_session.get(
        OrganizationPackage,
        result.organization_package_id,
    )
    role = db_session.execute(select(Role).where(Role.key == result.role_key)).scalar_one()

    assert organization.status == "active"
    assert user.status == "active"
    assert user.auth_user_id == result.auth_user_id
    assert user_organization.status == "active"
    assert user_organization.organization_id == organization.id
    assert user_organization.user_id == user.id
    assert user_organization.auth_user_id == user.auth_user_id
    assert user_organization.role_id == role.id
    assert plan.status == "active"
    assert plan.monthly_analysis_limit == 100
    assert package.status == "active"
    assert package.plan_id == plan.id
    assert package.entitlements["document_upload"] is True
    assert subscription.status == "active"
    assert subscription.organization_id == organization.id
    assert subscription.plan_id == plan.id
    assert organization_package.status == "active"
    assert organization_package.assigned_analysis_quota == 100


def test_mvp_test_seed_is_idempotent(db_session):
    config = _config()

    first = seed_mvp_test_environment(db_session, config)
    second = seed_mvp_test_environment(db_session, config)

    assert second == first
    assert len(db_session.execute(select(Organization)).scalars().all()) == 1
    assert len(db_session.execute(select(User)).scalars().all()) == 1
    assert len(db_session.execute(select(UserOrganization)).scalars().all()) == 1
    assert len(db_session.execute(select(Plan)).scalars().all()) == 1
    assert len(db_session.execute(select(Package)).scalars().all()) == 1
    assert len(db_session.execute(select(Subscription)).scalars().all()) == 1
    assert len(db_session.execute(select(OrganizationPackage)).scalars().all()) == 1


def test_mvp_test_seed_role_has_required_permissions(db_session):
    result = seed_mvp_test_environment(db_session, _config())

    role = db_session.execute(select(Role).where(Role.key == result.role_key)).scalar_one()
    permission_keys = {link.permission.key for link in role.permission_links}

    assert REQUIRED_MVP_PERMISSION_KEYS.issubset(permission_keys)


def test_mvp_test_seed_requires_auth_user_id(monkeypatch):
    monkeypatch.delenv("MERCADOIA_MVP_AUTH_USER_ID", raising=False)

    with pytest.raises(RuntimeError, match="MERCADOIA_MVP_AUTH_USER_ID"):
        config_from_env()


def test_mvp_test_seed_config_reads_non_secret_environment(monkeypatch):
    auth_user_id = str(uuid4())
    monkeypatch.setenv("MERCADOIA_MVP_AUTH_USER_ID", auth_user_id)
    monkeypatch.setenv("MERCADOIA_MVP_USER_EMAIL", "tester@example.test")
    monkeypatch.setenv("MERCADOIA_MVP_ROLE_KEY", "analyst")

    config = config_from_env()

    assert config.auth_user_id == auth_user_id
    assert config.user_email == "tester@example.test"
    assert config.role_key == "analyst"


def test_mvp_test_seed_config_uses_auth_user_id_for_default_email(monkeypatch):
    auth_user_id = str(uuid4())
    monkeypatch.setenv("MERCADOIA_MVP_AUTH_USER_ID", auth_user_id)
    monkeypatch.delenv("MERCADOIA_MVP_USER_EMAIL", raising=False)

    config = config_from_env()

    assert config.user_email == f"mvp.{auth_user_id}@example.test"
