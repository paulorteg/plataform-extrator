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
from app.models import (
    AuditLog,
    Document,
    Evidence,
    ExtractedField,
    Occurrence,
    Organization,
    Role,
    User,
    UserOrganization,
    ValidationIssue,
)
from app.organizations.dependencies import ORGANIZATION_ID_HEADER
from app.pipeline.field_catalog import FIELD_DEFINITIONS
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


def _create_user(session: Session) -> User:
    auth_user_id = str(uuid4())
    user = User(
        auth_user_id=auth_user_id,
        name="Reviewer",
        email=f"{auth_user_id}@example.test",
        status="active",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _create_organization(session: Session) -> Organization:
    organization = Organization(
        name=f"Organization {uuid4()}",
        legal_name="Organization LTDA",
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


def _link_user(session: Session, user: User, organization: Organization, role_key: str) -> None:
    role = _get_role(session, role_key)
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


def _headers(user: User, organization_id: str, request_id: str = "occurrence-review"):
    return {
        "Authorization": f"Bearer {_make_token(user.auth_user_id)}",
        ORGANIZATION_ID_HEADER: organization_id,
        REQUEST_ID_HEADER: request_id,
    }


def _create_occurrence_with_fields(session: Session, organization: Organization, user: User):
    document = Document(
        organization_id=organization.id,
        uploaded_by_user_id=user.id,
        original_filename="bo-anonimizado.pdf",
        content_type="application/pdf",
        size_bytes=123,
        sha256_hash="a" * 64,
        storage_bucket="documents",
        storage_path=f"organizations/{organization.id}/documents/{uuid4()}/original",
        storage_uri=f"supabase://documents/organizations/{organization.id}/documents/{uuid4()}/original",
        status="processed",
        metadata_json={},
    )
    session.add(document)
    session.flush()
    occurrence = Occurrence(
        organization_id=organization.id,
        document_id=document.id,
        sequence_number=1,
        document_family="boletim_ocorrencia",
        classification_confidence=91,
        status="validation_pending",
        text_excerpt="Resumo sem narrativa integral.",
        metadata_json={},
    )
    session.add(occurrence)
    session.flush()

    values = {
        "cnpj_vitima": "12.345.678/0001-90",
        "tipo_sinistro": "Roubo",
        "data_evento": "01/06/2026",
        "cidade_evento": "Campinas",
        "uf_evento": "SP",
        "evento_natureza": "Subtracao de carga",
        "mercadoria": "Eletronicos",
        "data_embarque": "31/05/2026",
        "cpf_motorista": "123.456.789-00",
        "placa_veiculo_sinistrado": "ABC1D23",
        "cidade_emplacamento": "Santos",
        "uf_emplacamento": "SP",
        "numero_bo": "2026-0001",
    }
    created_fields = {}
    for definition in FIELD_DEFINITIONS:
        evidence = Evidence(
            organization_id=organization.id,
            occurrence_id=occurrence.id,
            field_key=definition.field_key,
            source_type="text",
            text_excerpt=f"Evidencia anonima para {definition.field_key}",
            confidence=95,
            metadata_json={},
        )
        session.add(evidence)
        session.flush()
        field = ExtractedField(
            organization_id=organization.id,
            occurrence_id=occurrence.id,
            evidence_id=evidence.id,
            field_key=definition.field_key,
            group_key=definition.group_key,
            value=values.get(definition.field_key),
            status="extraido",
            confidence=95,
            extraction_method="deterministic_v1",
            metadata_json={},
        )
        session.add(field)
        created_fields[definition.field_key] = field
    session.commit()
    session.refresh(occurrence)
    return occurrence, created_fields


def test_list_occurrences_is_paginated_searchable_and_masks_sensitive_data(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, "viewer")
    _create_occurrence_with_fields(db_session, organization, user)

    response = client.get(
        "/api/v1/occurrences?q=Roubo&page=1&page_size=10",
        headers=_headers(user, organization.id),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    item = payload["items"][0]
    assert item["tipo_sinistro"] == "Roubo"
    assert item["cpf_motorista"] == "123*****00"
    assert item["cnpj_vitima"] == "12.***.***/****90"
    assert "Resumo sem narrativa integral" not in str(payload)


def test_occurrence_detail_and_fields_return_checklist_and_evidence(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, "viewer")
    occurrence, _fields = _create_occurrence_with_fields(db_session, organization, user)

    detail = client.get(
        f"/api/v1/occurrences/{occurrence.id}",
        headers=_headers(user, organization.id),
    )
    fields = client.get(
        f"/api/v1/occurrences/{occurrence.id}/fields",
        headers=_headers(user, organization.id),
    )

    assert detail.status_code == 200
    assert detail.json()["checklist"]["can_approve"] is True
    assert fields.status_code == 200
    cpf_field = next(item for item in fields.json() if item["field_key"] == "cpf_motorista")
    assert cpf_field["value"] == "123*****00"
    assert cpf_field["evidence"]["text_excerpt"].startswith("Evidencia anonima")


def test_update_field_requires_permission_and_records_audit_log(client, db_session):
    viewer = _create_user(db_session)
    admin = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, viewer, organization, "viewer")
    _link_user(db_session, admin, organization, "organization_admin")
    occurrence, fields = _create_occurrence_with_fields(db_session, organization, admin)
    field = fields["mercadoria"]

    denied = client.patch(
        f"/api/v1/occurrences/{occurrence.id}/fields/{field.id}",
        headers=_headers(viewer, organization.id, "denied-edit"),
        json={"value": "Medicamentos"},
    )
    allowed = client.patch(
        f"/api/v1/occurrences/{occurrence.id}/fields/{field.id}",
        headers=_headers(admin, organization.id, "allowed-edit"),
        json={"value": "Medicamentos", "justification": "corrigido em revisao"},
    )

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["value"] == "Medicamentos"
    audit_log = db_session.execute(
        select(AuditLog).where(AuditLog.event_type == "review.field_updated")
    ).scalar_one()
    assert audit_log.organization_id == organization.id
    assert audit_log.user_id == admin.id
    assert audit_log.request_id == "allowed-edit"
    assert "value" in audit_log.metadata_json["changed_fields"]


def test_approve_field_resolves_related_validation_issues(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, "organization_admin")
    occurrence, fields = _create_occurrence_with_fields(db_session, organization, user)
    field = fields["mercadoria"]
    issue = ValidationIssue(
        organization_id=organization.id,
        occurrence_id=occurrence.id,
        field_id=field.id,
        field_key=field.field_key,
        issue_type="low_confidence",
        severity="warning",
        message="Baixa confianca.",
        status="open",
        metadata_json={},
    )
    db_session.add(issue)
    db_session.commit()

    response = client.post(
        f"/api/v1/occurrences/{occurrence.id}/fields/{field.id}/approve",
        headers=_headers(user, organization.id, "approve-field"),
        json={"justification": "evidencia conferida"},
    )
    db_session.refresh(issue)

    assert response.status_code == 200
    assert response.json()["status"] == "aprovado"
    assert issue.status == "resolved"


def test_approve_occurrence_blocks_pending_required_and_creates_snapshot(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, "organization_admin")
    occurrence, fields = _create_occurrence_with_fields(db_session, organization, user)
    blocking_issue = ValidationIssue(
        organization_id=organization.id,
        occurrence_id=occurrence.id,
        field_id=fields["mercadoria"].id,
        field_key="mercadoria",
        issue_type="invalid_format",
        severity="blocking",
        message="Campo invalido.",
        status="open",
        metadata_json={},
    )
    db_session.add(blocking_issue)
    db_session.commit()

    blocked = client.post(
        f"/api/v1/occurrences/{occurrence.id}/approve",
        headers=_headers(user, organization.id, "blocked-approval"),
    )
    blocking_issue.status = "resolved"
    db_session.commit()
    approved = client.post(
        f"/api/v1/occurrences/{occurrence.id}/approve",
        headers=_headers(user, organization.id, "approved-occurrence"),
    )

    assert blocked.status_code == 400
    assert blocked.json()["code"] == "occurrence_not_approvable"
    assert approved.status_code == 200
    assert approved.json()["status"] == "aprovado"
    audit_log = db_session.execute(
        select(AuditLog).where(AuditLog.event_type == "review.occurrence_approved")
    ).scalar_one()
    assert audit_log.request_id == "approved-occurrence"


def test_occurrence_access_is_limited_to_active_organization(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    other_organization = _create_organization(db_session)
    _link_user(db_session, user, organization, "organization_admin")
    occurrence, _fields = _create_occurrence_with_fields(db_session, organization, user)

    response = client.get(
        f"/api/v1/occurrences/{occurrence.id}",
        headers=_headers(user, other_organization.id),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "organization_not_allowed"
