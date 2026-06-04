from uuid import uuid4
from typing import Optional

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Organization, Role, User, UserOrganization


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


def _create_organization(session: Session) -> Organization:
    organization = Organization(
        name="Organization Test",
        legal_name="Organization Test LTDA",
        cnpj_hash="hash_cnpj_test",
        status="active",
        retention_days=180,
    )
    session.add(organization)
    session.flush()
    return organization


def _create_user(session: Session, email: str = "user@example.test") -> User:
    user = User(
        auth_user_id=str(uuid4()),
        name="User Test",
        email=email,
        status="active",
    )
    session.add(user)
    session.flush()
    return user


def _link_user_to_organization(
    session: Session,
    user: User,
    organization: Organization,
    role: Optional[Role] = None,
) -> UserOrganization:
    link = UserOrganization(
        user_id=user.id,
        auth_user_id=user.auth_user_id,
        organization_id=organization.id,
        role_id=role.id if role else None,
        role_key="organization_admin",
        status="active",
    )
    session.add(link)
    session.flush()
    return link


def test_can_create_organization_user_and_user_organization(db_session):
    organization = _create_organization(db_session)
    user = _create_user(db_session)
    role = Role(key="organization_admin", name="Organization Admin", scope="organization", status="active")
    db_session.add(role)
    db_session.flush()
    link = _link_user_to_organization(db_session, user, organization, role)

    assert organization.id is not None
    assert user.id is not None
    assert user.auth_user_id is not None
    assert link.organization_id == organization.id
    assert link.user_id == user.id
    assert link.auth_user_id == user.auth_user_id
    assert link.role_id == role.id


def test_users_email_must_be_unique(db_session):
    _create_user(db_session, email="same@example.test")

    duplicate_user = User(
        auth_user_id=str(uuid4()),
        name="Duplicate Email",
        email="same@example.test",
        status="active",
    )
    db_session.add(duplicate_user)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_users_auth_user_id_must_be_unique(db_session):
    auth_user_id = str(uuid4())
    db_session.add(
        User(
            auth_user_id=auth_user_id,
            name="First User",
            email="first@example.test",
            status="active",
        )
    )
    db_session.flush()

    db_session.add(
        User(
            auth_user_id=auth_user_id,
            name="Second User",
            email="second@example.test",
            status="active",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_user_organization_duplicate_link_is_blocked(db_session):
    organization = _create_organization(db_session)
    user = _create_user(db_session)
    _link_user_to_organization(db_session, user, organization)

    duplicate_link = UserOrganization(
        user_id=user.id,
        auth_user_id=user.auth_user_id,
        organization_id=organization.id,
        role_key="manager",
        status="active",
    )
    db_session.add(duplicate_link)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_user_organization_requires_organization_id(db_session):
    user = _create_user(db_session)

    link_without_organization = UserOrganization(
        user_id=user.id,
        auth_user_id=user.auth_user_id,
        organization_id=None,
        role_key="viewer",
        status="active",
    )
    db_session.add(link_without_organization)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_password_fields_are_not_defined():
    forbidden_columns = {"password", "password_hash", "hashed_password"}

    for table_name in (
        "organizations",
        "permissions",
        "role_permissions",
        "roles",
        "users",
        "user_organizations",
    ):
        columns = set(Base.metadata.tables[table_name].columns.keys())
        assert columns.isdisjoint(forbidden_columns)
