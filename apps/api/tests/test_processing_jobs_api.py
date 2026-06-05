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
from app.models import Document, Organization, ProcessingJob, Role, User, UserOrganization
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


def _create_user(session: Session) -> User:
    auth_user_id = str(uuid4())
    user = User(
        auth_user_id=auth_user_id,
        name="Job Viewer",
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


def _create_role_without_permissions(session: Session) -> Role:
    role = Role(
        key=f"no_job_permission_{uuid4()}",
        name="No Job Permission",
        scope="organization",
        status="active",
    )
    session.add(role)
    session.commit()
    session.refresh(role)
    return role


def _link_user(session: Session, user: User, organization: Organization, role: Role) -> None:
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


def _create_document(session: Session, organization: Organization, user: User) -> Document:
    document = Document(
        organization_id=organization.id,
        uploaded_by_user_id=user.id,
        original_filename="bo-sintetico.pdf",
        content_type="application/pdf",
        size_bytes=123,
        sha256_hash="a" * 64,
        storage_bucket="documents",
        storage_path=f"organizations/{organization.id}/documents/{uuid4()}/original",
        storage_uri=f"supabase://documents/organizations/{organization.id}/documents/{uuid4()}/original",
        status="uploaded",
        metadata_json={"internal_note": "must not leak"},
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def _create_job(
    session: Session,
    *,
    organization: Organization,
    document: Document,
    status: str = "pending",
) -> ProcessingJob:
    job = ProcessingJob(
        organization_id=organization.id,
        document_id=document.id,
        job_type="document_processing",
        status=status,
        priority=100,
        attempts=1,
        max_attempts=3,
        error_code="storage_download_failed" if status == "failed" else None,
        error_message="raw internal storage error with sensitive implementation detail"
        if status == "failed"
        else None,
        metadata_json={
            "content_text": "raw document text must not leak",
            "Authorization": "Bearer must-not-leak",
            "signed_url": "https://signed.example.test/must-not-leak",
        },
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def _auth_headers(
    user: User,
    organization_id: str,
    request_id: str = "jobs-api-request",
):
    return {
        "Authorization": f"Bearer {_make_token(user.auth_user_id)}",
        ORGANIZATION_ID_HEADER: organization_id,
        REQUEST_ID_HEADER: request_id,
    }


def test_get_processing_job_returns_sanitized_status(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, _get_role(db_session, "organization_admin"))
    document = _create_document(db_session, organization, user)
    job = _create_job(db_session, organization=organization, document=document, status="failed")

    response = client.get(
        f"/api/v1/processing-jobs/{job.id}",
        headers=_auth_headers(user, organization.id, "job-detail-request"),
    )

    assert response.status_code == 200
    payload = response.json()
    rendered_payload = str(payload)
    assert payload["id"] == job.id
    assert payload["organization_id"] == organization.id
    assert payload["document_id"] == document.id
    assert payload["job_type"] == "document_processing"
    assert payload["status"] == "failed"
    assert payload["error"] == {
        "code": "storage_download_failed",
        "message": "Processing job failed.",
    }
    assert "metadata" not in payload
    assert "raw document text" not in rendered_payload
    assert "raw internal storage error" not in rendered_payload
    assert "must-not-leak" not in rendered_payload


def test_list_document_processing_jobs_returns_jobs_for_document(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, _get_role(db_session, "organization_admin"))
    document = _create_document(db_session, organization, user)
    job = _create_job(db_session, organization=organization, document=document)

    response = client.get(
        f"/api/v1/documents/{document.id}/processing-jobs",
        headers=_auth_headers(user, organization.id, "job-list-request"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == job.id
    assert payload["items"][0]["error"] is None


def test_processing_job_requires_document_view_permission(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    role = _create_role_without_permissions(db_session)
    _link_user(db_session, user, organization, role)
    document = _create_document(db_session, organization, user)
    job = _create_job(db_session, organization=organization, document=document)

    response = client.get(
        f"/api/v1/processing-jobs/{job.id}",
        headers=_auth_headers(user, organization.id, "job-permission-denied"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert response.json()["request_id"] == "job-permission-denied"


def test_processing_job_blocks_cross_organization_access(client, db_session):
    user = _create_user(db_session)
    user_organization = _create_organization(db_session)
    other_organization = _create_organization(db_session)
    _link_user(db_session, user, user_organization, _get_role(db_session, "organization_admin"))
    other_user = _create_user(db_session)
    other_document = _create_document(db_session, other_organization, other_user)
    other_job = _create_job(
        db_session,
        organization=other_organization,
        document=other_document,
    )

    response = client.get(
        f"/api/v1/processing-jobs/{other_job.id}",
        headers=_auth_headers(user, user_organization.id, "job-cross-org"),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "processing_job_not_found"
    assert response.json()["request_id"] == "job-cross-org"


def test_processing_job_not_found_returns_controlled_error(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, _get_role(db_session, "organization_admin"))

    response = client.get(
        f"/api/v1/processing-jobs/{uuid4()}",
        headers=_auth_headers(user, organization.id, "job-not-found"),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "processing_job_not_found"
    assert response.json()["request_id"] == "job-not-found"


def test_document_processing_jobs_block_cross_organization_document(client, db_session):
    user = _create_user(db_session)
    user_organization = _create_organization(db_session)
    other_organization = _create_organization(db_session)
    _link_user(db_session, user, user_organization, _get_role(db_session, "organization_admin"))
    other_user = _create_user(db_session)
    other_document = _create_document(db_session, other_organization, other_user)
    _create_job(db_session, organization=other_organization, document=other_document)

    response = client.get(
        f"/api/v1/documents/{other_document.id}/processing-jobs",
        headers=_auth_headers(user, user_organization.id, "document-jobs-cross-org"),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "document_not_found"
    assert response.json()["request_id"] == "document-jobs-cross-org"
