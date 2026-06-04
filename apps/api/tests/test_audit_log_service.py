from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit_log.service import list_by_organization, record, sanitize_metadata
from app.db.base import Base
from app.models import Organization, User


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


def _create_user(session: Session) -> User:
    user = User(
        auth_user_id=str(uuid4()),
        name="User Test",
        email=f"{uuid4()}@example.test",
        status="active",
    )
    session.add(user)
    session.flush()
    return user


def test_record_creates_audit_log_with_context(db_session):
    organization = _create_organization(db_session)
    user = _create_user(db_session)

    audit_log = record(
        db_session,
        "organization.updated",
        organization_id=organization.id,
        user_id=user.id,
        target_type="organization",
        target_id=organization.id,
        request_id="request-123",
        metadata={"field": "status", "new_value": "active"},
    )
    db_session.commit()

    assert audit_log.id is not None
    assert audit_log.event_type == "organization.updated"
    assert audit_log.organization_id == organization.id
    assert audit_log.user_id == user.id
    assert audit_log.target_type == "organization"
    assert audit_log.target_id == organization.id
    assert audit_log.request_id == "request-123"
    assert audit_log.metadata_json == {"field": "status", "new_value": "active"}


def test_record_allows_system_level_event_without_optional_context(db_session):
    audit_log = record(db_session, "system.health_checked")
    db_session.commit()

    assert audit_log.organization_id is None
    assert audit_log.user_id is None
    assert audit_log.metadata_json == {}


def test_audit_logs_are_listable_by_organization(db_session):
    first_organization = _create_organization(db_session)
    second_organization = _create_organization(db_session)
    record(db_session, "organization.updated", organization_id=first_organization.id)
    record(db_session, "organization.updated", organization_id=second_organization.id)
    record(db_session, "organization.viewed", organization_id=first_organization.id)
    db_session.commit()

    audit_logs = list_by_organization(db_session, first_organization.id)

    assert len(audit_logs) == 2
    assert {audit_log.organization_id for audit_log in audit_logs} == {
        first_organization.id
    }


def test_metadata_redacts_sensitive_values(db_session):
    audit_log = record(
        db_session,
        "sensitive.action",
        metadata={
            "Authorization": "Bearer secret-token",
            "jwt": "jwt-value",
            "password": "plain-password",
            "prompt": "full prompt",
            "nested": {"token": "nested-token", "safe": "value"},
            "safe": "value",
        },
    )
    db_session.commit()

    assert audit_log.metadata_json == {
        "Authorization": "[REDACTED]",
        "jwt": "[REDACTED]",
        "password": "[REDACTED]",
        "prompt": "[REDACTED]",
        "nested": {"token": "[REDACTED]", "safe": "value"},
        "safe": "value",
    }


def test_metadata_truncates_long_strings():
    long_value = "x" * 300

    sanitized = sanitize_metadata({"safe": long_value})

    assert sanitized["safe"].endswith("...[truncated]")
    assert len(sanitized["safe"]) < len(long_value)


def test_event_type_is_required(db_session):
    audit_log = record(db_session, "")
    audit_log.event_type = None

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_service_exposes_only_additive_operations():
    import app.audit_log.service as audit_log_service

    assert hasattr(audit_log_service, "record")
    assert not hasattr(audit_log_service, "update")
    assert not hasattr(audit_log_service, "delete")
