from uuid import uuid4
from typing import Optional

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Document, DocumentPage, Occurrence, Organization, ProcessingJob, User
from app.queue.service import (
    JOB_TYPE_ANALYZE_FILE,
    JOB_TYPE_CLASSIFY_DOCUMENT,
    JOB_TYPE_EXTRACT_TEXT,
    JOB_TYPE_RUN_OCR,
    JOB_TYPE_SEGMENT_OCCURRENCES,
    process_next_fake_job,
)


@pytest.fixture
def db_session():
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
        yield session


def _create_document(session: Session, *, content_type: str = "application/pdf") -> Document:
    organization = Organization(
        name=f"Organization {uuid4()}",
        legal_name="Organization LTDA",
        cnpj_hash=f"hash_{uuid4()}",
        status="active",
        retention_days=180,
    )
    user = User(
        auth_user_id=str(uuid4()),
        name="Pipeline User",
        email=f"{uuid4()}@example.test",
        status="active",
    )
    session.add_all([organization, user])
    session.flush()
    document = Document(
        organization_id=organization.id,
        uploaded_by_user_id=user.id,
        original_filename="bo.pdf",
        content_type=content_type,
        size_bytes=64,
        sha256_hash="d" * 64,
        storage_bucket="documents",
        storage_path=f"organizations/{organization.id}/documents/{uuid4()}/original",
        storage_uri=f"supabase://documents/organizations/{organization.id}/documents/{uuid4()}/original",
        status="uploaded",
        metadata_json={},
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def _enqueue(
    session: Session,
    *,
    document: Document,
    job_type: str,
    metadata: Optional[dict] = None,
) -> ProcessingJob:
    job = ProcessingJob(
        organization_id=document.organization_id,
        document_id=document.id,
        job_type=job_type,
        status="pending",
        priority=10,
        attempts=0,
        max_attempts=3,
        metadata_json=metadata or {},
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def test_analyze_file_job_updates_document_metadata_without_logging_text(db_session):
    document = _create_document(db_session)
    job = _enqueue(
        db_session,
        document=document,
        job_type=JOB_TYPE_ANALYZE_FILE,
        metadata={"content_text": "%PDF /Type /Page BT BOLETIM"},
    )

    processed = process_next_fake_job(db_session)
    db_session.commit()
    db_session.refresh(document)

    assert processed.id == job.id
    assert processed.status == "completed"
    assert document.status == "analyzed"
    assert document.metadata_json["file_analysis"]["file_type"] == "pdf"
    assert "content_text" not in document.metadata_json


def test_extract_text_job_creates_document_page(db_session):
    document = _create_document(db_session)
    _enqueue(
        db_session,
        document=document,
        job_type=JOB_TYPE_EXTRACT_TEXT,
        metadata={"content_text": "%PDF BT BOLETIM DE OCORRENCIA POLICIA"},
    )

    processed = process_next_fake_job(db_session)
    db_session.commit()
    page = db_session.execute(select(DocumentPage)).scalar_one()
    db_session.refresh(document)

    assert processed.status == "completed"
    assert document.status == "text_extracted"
    assert page.organization_id == document.organization_id
    assert page.extraction_method == "digital"
    assert "BOLETIM DE OCORRENCIA" in page.text


def test_run_ocr_job_uses_fake_provider_and_creates_page(db_session):
    document = _create_document(db_session, content_type="image/png")
    _enqueue(
        db_session,
        document=document,
        job_type=JOB_TYPE_RUN_OCR,
        metadata={
            "content_text": "BOLETIM DE OCORRENCIA OCR",
            "content_type": "image/png",
            "page_number": 1,
        },
    )

    processed = process_next_fake_job(db_session)
    db_session.commit()
    page = db_session.execute(select(DocumentPage)).scalar_one()
    db_session.refresh(document)

    assert processed.status == "completed"
    assert document.status == "ocr_completed"
    assert page.extraction_method == "ocr"
    assert page.metadata_json == {"provider": "fake"}
    assert page.confidence == 80


def test_classification_job_updates_document_without_creating_occurrences(db_session):
    document = _create_document(db_session)
    db_session.add(
        DocumentPage(
            organization_id=document.organization_id,
            document_id=document.id,
            page_number=1,
            extraction_method="digital",
            text="BOLETIM DE OCORRENCIA POLICIA",
            text_hash="e" * 64,
            confidence=100,
            status="extracted",
            metadata_json={},
        )
    )
    _enqueue(db_session, document=document, job_type=JOB_TYPE_CLASSIFY_DOCUMENT)

    processed = process_next_fake_job(db_session)
    db_session.commit()
    db_session.refresh(document)

    assert processed.status == "completed"
    assert document.status == "classified"
    assert document.metadata_json["classification"]["document_family"] == "boletim_ocorrencia"
    assert db_session.execute(select(Occurrence)).scalars().all() == []


def test_segmentation_job_creates_occurrences_from_document_pages(db_session):
    document = _create_document(db_session)
    db_session.add(
        DocumentPage(
            organization_id=document.organization_id,
            document_id=document.id,
            page_number=1,
            extraction_method="digital",
            text="BOLETIM DE OCORRENCIA 1 fato A BOLETIM DE OCORRENCIA 2 fato B",
            text_hash="f" * 64,
            confidence=100,
            status="extracted",
            metadata_json={},
        )
    )
    _enqueue(db_session, document=document, job_type=JOB_TYPE_SEGMENT_OCCURRENCES)

    processed = process_next_fake_job(db_session)
    db_session.commit()
    occurrences = db_session.execute(
        select(Occurrence).order_by(Occurrence.sequence_number)
    ).scalars().all()
    db_session.refresh(document)

    assert processed.status == "completed"
    assert document.status == "segmented"
    assert len(occurrences) == 2
    assert all(item.organization_id == document.organization_id for item in occurrences)
    assert occurrences[0].document_family == "boletim_ocorrencia"


def test_pipeline_job_fails_without_document_and_does_not_raise(db_session):
    document = _create_document(db_session)
    other_organization = Organization(
        name=f"Organization {uuid4()}",
        legal_name="Organization LTDA",
        cnpj_hash=f"hash_{uuid4()}",
        status="active",
        retention_days=180,
    )
    db_session.add(other_organization)
    db_session.commit()
    db_session.refresh(other_organization)

    job = ProcessingJob(
        organization_id=other_organization.id,
        document_id=document.id,
        job_type=JOB_TYPE_RUN_OCR,
        status="pending",
        priority=10,
        attempts=0,
        max_attempts=3,
        metadata_json={"content_text": "BOLETIM"},
    )
    db_session.add(job)
    db_session.commit()

    processed = process_next_fake_job(db_session)
    db_session.commit()

    assert processed.id == job.id
    assert processed.status == "failed"
    assert processed.error_code == "document_organization_mismatch"
    assert processed.error_message == "Pipeline job could not be processed."
