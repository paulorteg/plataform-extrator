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
from app.models import AuditLog, Document, Organization, ProcessingJob, Role, User, UserOrganization
from app.organizations.dependencies import ORGANIZATION_ID_HEADER
from app.queue.service import claim_next_pending_job, process_next_fake_job
from app.seeds.roles_permissions import seed_roles_permissions
from app.storage.dependencies import get_storage_service


TEST_JWT_SECRET = "test-jwt-secret-with-at-least-32-bytes"
TEST_SUPABASE_URL = "https://example.supabase.co"


class FakeStorageService:
    def __init__(self):
        self.uploads = []

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
        name="User Test",
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


def _auth_headers(user: User, organization_id: str, request_id: str = "upload-request"):
    return {
        "Authorization": f"Bearer {_make_token(user.auth_user_id)}",
        ORGANIZATION_ID_HEADER: organization_id,
        REQUEST_ID_HEADER: request_id,
    }


def test_upload_document_creates_document_job_storage_object_and_audit_log(
    client,
    db_session,
    fake_storage,
):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, _get_role(db_session, "organization_admin"))

    response = client.post(
        "/api/v1/documents/upload",
        headers=_auth_headers(user, organization.id, "upload-audit-request"),
        files={"file": ("bo.pdf", b"%PDF-test-content", "application/pdf")},
    )

    assert response.status_code == 201
    payload = response.json()
    document = db_session.execute(select(Document)).scalar_one()
    job = db_session.execute(select(ProcessingJob)).scalar_one()
    audit_log = db_session.execute(
        select(AuditLog).where(AuditLog.event_type == "document.uploaded")
    ).scalar_one()

    assert payload["document_id"] == document.id
    assert payload["job_id"] == job.id
    assert document.organization_id == organization.id
    assert document.uploaded_by_user_id == user.id
    assert document.status == "uploaded"
    assert document.storage_bucket == "documents"
    assert document.storage_path.startswith(f"organizations/{organization.id}/documents/")
    assert document.storage_uri == f"supabase://documents/{document.storage_path}"
    assert job.organization_id == organization.id
    assert job.document_id == document.id
    assert job.status == "pending"
    assert audit_log.organization_id == organization.id
    assert audit_log.request_id == "upload-audit-request"
    assert "original_filename" not in audit_log.metadata_json
    assert fake_storage.uploads[0]["content"] == b"%PDF-test-content"


def test_upload_document_requires_document_upload_permission(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, _get_role(db_session, "viewer"))

    response = client.post(
        "/api/v1/documents/upload",
        headers=_auth_headers(user, organization.id, "upload-denied-request"),
        files={"file": ("bo.pdf", b"%PDF-test-content", "application/pdf")},
    )

    assert response.status_code == 403
    assert response.json()["request_id"] == "upload-denied-request"


def test_upload_document_rejects_unsupported_file_type(client, db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    _link_user(db_session, user, organization, _get_role(db_session, "organization_admin"))

    response = client.post(
        "/api/v1/documents/upload",
        headers=_auth_headers(user, organization.id, "bad-type-request"),
        files={"file": ("bo.txt", b"text", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "unsupported_file_type"
    assert response.json()["request_id"] == "bad-type-request"


def test_queue_service_claims_and_completes_fake_job(db_session):
    user = _create_user(db_session)
    organization = _create_organization(db_session)
    document = Document(
        organization_id=organization.id,
        uploaded_by_user_id=user.id,
        original_filename="bo.pdf",
        content_type="application/pdf",
        size_bytes=10,
        sha256_hash="a" * 64,
        storage_bucket="documents",
        storage_path=f"organizations/{organization.id}/documents/{uuid4()}/original",
        storage_uri=f"supabase://documents/organizations/{organization.id}/documents/{uuid4()}/original",
        status="uploaded",
        metadata_json={},
    )
    db_session.add(document)
    db_session.flush()
    job = ProcessingJob(
        organization_id=organization.id,
        document_id=document.id,
        status="pending",
        job_type="document_processing",
        priority=50,
        attempts=0,
        max_attempts=3,
        metadata_json={},
    )
    db_session.add(job)
    db_session.commit()

    claimed = claim_next_pending_job(db_session)
    assert claimed.id == job.id
    assert claimed.status == "running"
    assert claimed.attempts == 1
    db_session.commit()

    completed = process_next_fake_job(db_session)
    assert completed is None

    job.status = "pending"
    db_session.commit()
    completed = process_next_fake_job(db_session)
    assert completed.id == job.id
    assert completed.status == "completed"
