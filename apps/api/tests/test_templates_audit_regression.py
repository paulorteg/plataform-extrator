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
    ExtractedField,
    GeneratedReport,
    Occurrence,
    Organization,
    ReviewVersion,
    Role,
    User,
    UserOrganization,
)
from app.organizations.dependencies import ORGANIZATION_ID_HEADER
from app.pipeline.field_catalog import FIELD_DEFINITIONS
from app.seeds.roles_permissions import seed_roles_permissions
from app.storage.dependencies import get_storage_service


TEST_JWT_SECRET = "test-jwt-secret-with-at-least-32-bytes"
TEST_SUPABASE_URL = "https://example.supabase.co"


class FakeStorageService:
    def __init__(self):
        self.uploads = []
        self.signed_urls = []

    def upload(self, *, bucket: str, object_path: str, content: bytes, content_type: str) -> str:
        self.uploads.append(
            {
                "bucket": bucket,
                "object_path": object_path,
                "content": content,
                "content_type": content_type,
            }
        )
        return f"supabase://{bucket}/{object_path}"

    def create_signed_url(self, *, bucket: str, object_path: str, expires_in: int) -> str:
        self.signed_urls.append(
            {"bucket": bucket, "object_path": object_path, "expires_in": expires_in}
        )
        return f"https://signed.example.test/{bucket}/{object_path}?ttl={expires_in}"

    def delete(self, *, bucket: str, object_path: str) -> None:
        return None

    def exists(self, *, bucket: str, object_path: str) -> bool:
        return True


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
    monkeypatch.setenv("SUPABASE_SIGNED_URL_TTL_SECONDS", "120")

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
def fake_storage():
    return FakeStorageService()


@pytest.fixture
def client(db_session, fake_storage):
    app = create_app()

    def override_get_database_session():
        yield db_session

    def override_get_storage_service():
        return fake_storage

    app.dependency_overrides[get_database_session] = override_get_database_session
    app.dependency_overrides[get_storage_service] = override_get_storage_service
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
        name="Template Reviewer",
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


def _headers(user: User, organization_id: str, request_id: str = "template-request"):
    return {
        "Authorization": f"Bearer {_make_token(user.auth_user_id)}",
        ORGANIZATION_ID_HEADER: organization_id,
        REQUEST_ID_HEADER: request_id,
    }


def _create_occurrence_with_required_fields(
    session: Session,
    organization: Organization,
    user: User,
) -> Occurrence:
    document = Document(
        organization_id=organization.id,
        uploaded_by_user_id=user.id,
        original_filename="bo-sintetico.pdf",
        content_type="application/pdf",
        size_bytes=123,
        sha256_hash="b" * 64,
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
        classification_confidence=95,
        status="mapped",
        text_excerpt="Resumo sintetico sem narrativa integral.",
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
    }
    for definition in FIELD_DEFINITIONS:
        field = ExtractedField(
            organization_id=organization.id,
            occurrence_id=occurrence.id,
            field_key=definition.field_key,
            group_key=definition.group_key,
            value=values.get(definition.field_key),
            status="aprovado",
            confidence=96,
            extraction_method="deterministic_v1",
            metadata_json={},
        )
        session.add(field)
    session.commit()
    session.refresh(occurrence)
    return occurrence


def _approve_occurrence(client: TestClient, user: User, organization: Organization, occurrence: Occurrence):
    return client.post(
        f"/api/v1/occurrences/{occurrence.id}/approve",
        headers=_headers(user, organization.id, "approve-template-occurrence"),
    )


def test_approve_occurrence_creates_review_version_snapshot(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, "organization_admin")
    occurrence = _create_occurrence_with_required_fields(db_session, organization, user)

    response = _approve_occurrence(client, user, organization, occurrence)

    assert response.status_code == 200
    review_version = db_session.execute(select(ReviewVersion)).scalar_one()
    assert review_version.organization_id == organization.id
    assert review_version.occurrence_id == occurrence.id
    assert review_version.version == 1
    assert len(review_version.snapshot_json["fields"]) >= 12
    db_session.refresh(occurrence)
    assert occurrence.metadata_json["approved_snapshot"]["review_version_id"] == review_version.id


def test_template_preview_and_generation_use_private_storage_and_audit(
    client,
    db_session,
    fake_storage,
):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, "organization_admin")
    occurrence = _create_occurrence_with_required_fields(db_session, organization, user)
    _approve_occurrence(client, user, organization, occurrence)

    preview = client.post(
        f"/api/v1/occurrences/{occurrence.id}/templates/preview",
        headers=_headers(user, organization.id, "template-preview"),
    )
    generated = client.post(
        f"/api/v1/occurrences/{occurrence.id}/templates/generate",
        headers=_headers(user, organization.id, "template-generate"),
    )

    assert preview.status_code == 200
    assert preview.json()["template_version"] == "mercadoia_v1"
    assert "MercadoIA - Template V1" in preview.json()["content_preview"]
    assert generated.status_code == 200
    generated_report = db_session.execute(select(GeneratedReport)).scalar_one()
    assert generated_report.organization_id == organization.id
    assert generated_report.storage_bucket == "templates"
    assert generated_report.storage_path.startswith(
        f"organizations/{organization.id}/occurrences/{occurrence.id}/templates/"
    )
    assert generated_report.storage_uri == f"supabase://templates/{generated_report.storage_path}"
    assert fake_storage.uploads[0]["bucket"] == "templates"
    assert b"MercadoIA - Template V1" in fake_storage.uploads[0]["content"]
    audit_log = db_session.execute(
        select(AuditLog).where(AuditLog.event_type == "template.generated")
    ).scalar_one()
    assert audit_log.request_id == "template-generate"
    assert "content" not in audit_log.metadata_json
    preview_audit_log = db_session.execute(
        select(AuditLog).where(AuditLog.event_type == "template.previewed")
    ).scalar_one()
    assert preview_audit_log.request_id == "template-preview"
    assert "content" not in preview_audit_log.metadata_json


def test_template_generation_requires_approved_occurrence(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, "organization_admin")
    occurrence = _create_occurrence_with_required_fields(db_session, organization, user)

    response = client.post(
        f"/api/v1/occurrences/{occurrence.id}/templates/generate",
        headers=_headers(user, organization.id, "template-not-approved"),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "occurrence_not_approved"
    assert response.json()["request_id"] == "template-not-approved"


def test_template_download_url_is_temporary_and_records_audit_log(
    client,
    db_session,
    fake_storage,
):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, "organization_admin")
    occurrence = _create_occurrence_with_required_fields(db_session, organization, user)
    _approve_occurrence(client, user, organization, occurrence)
    generated = client.post(
        f"/api/v1/occurrences/{occurrence.id}/templates/generate",
        headers=_headers(user, organization.id, "template-generate-before-download"),
    )
    report_id = generated.json()["report_id"]

    response = client.get(
        f"/api/v1/occurrences/{occurrence.id}/templates/{report_id}/download-url",
        headers=_headers(user, organization.id, "template-download"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["expires_in"] == 120
    assert payload["signed_url"].startswith("https://signed.example.test/")
    assert "supabase://" not in payload["signed_url"]
    assert fake_storage.signed_urls[0]["expires_in"] == 120
    audit_log = db_session.execute(
        select(AuditLog).where(AuditLog.event_type == "template.download_url_created")
    ).scalar_one()
    assert audit_log.request_id == "template-download"
    assert "signed_url" not in audit_log.metadata_json


def test_audit_api_filters_by_active_organization_and_requires_permission(client, db_session):
    auditor = _create_user(db_session)
    viewer = _create_user(db_session)
    organization = _create_organization(db_session)
    other_organization = _create_organization(db_session)
    _link_user(db_session, auditor, organization, "auditor")
    _link_user(db_session, viewer, organization, "viewer")
    db_session.add(
        AuditLog(
            event_type="template.generated",
            organization_id=organization.id,
            user_id=auditor.id,
            target_type="generated_report",
            target_id="report-1",
            request_id="audit-visible",
            metadata_json={"safe": "metadata"},
        )
    )
    db_session.add(
        AuditLog(
            event_type="template.generated",
            organization_id=other_organization.id,
            user_id=auditor.id,
            target_type="generated_report",
            target_id="report-2",
            request_id="audit-hidden",
            metadata_json={"safe": "metadata"},
        )
    )
    db_session.commit()

    denied = client.get(
        "/api/v1/audit-logs",
        headers=_headers(viewer, organization.id, "audit-denied"),
    )
    allowed = client.get(
        "/api/v1/audit-logs?event_type=template.generated",
        headers=_headers(auditor, organization.id, "audit-allowed"),
    )

    assert denied.status_code == 403
    assert allowed.status_code == 200
    payload = allowed.json()
    assert payload["total"] == 1
    assert payload["items"][0]["request_id"] == "audit-visible"
    assert "audit-hidden" not in str(payload)


def test_audit_export_requires_audit_export_and_records_export_event(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, "organization_admin")
    db_session.add(
        AuditLog(
            event_type="review.occurrence_approved",
            organization_id=organization.id,
            user_id=user.id,
            target_type="occurrence",
            target_id="occurrence-1",
            request_id="review-request",
            metadata_json={"safe": "metadata"},
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/audit-logs/export",
        headers=_headers(user, organization.id, "audit-export"),
    )

    assert response.status_code == 200
    assert response.json()["format"] == "json"
    export_log = db_session.execute(
        select(AuditLog).where(AuditLog.event_type == "audit.exported")
    ).scalar_one()
    assert export_log.request_id == "audit-export"
    assert export_log.metadata_json["row_count"] == 1
