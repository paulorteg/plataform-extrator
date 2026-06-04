from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit_log.service import sanitize_metadata
from app.models.document import Document
from app.models.document_page import DocumentPage
from app.models.occurrence import Occurrence
from app.models.processing_job import ProcessingJob
from app.pipeline.canonical import persist_canonical_model
from app.pipeline.classifier import DocumentClassifierV1
from app.pipeline.field_extraction import extract_and_persist_fields
from app.pipeline.file_analyzer import FileAnalyzer
from app.pipeline.mapping import persist_mercadoia_mapping
from app.pipeline.ocr import FakeOcrProvider
from app.pipeline.segmentation import OccurrenceSegmenterV1, persist_occurrences
from app.pipeline.sections import SectionDetectorV1
from app.pipeline.text_extraction import TextExtractionService, persist_extracted_pages
from app.pipeline.validation import validate_occurrence_fields
from app.storage.dependencies import get_storage_service
from app.storage.service import StorageError, StorageObjectNotFoundError, StorageService
from app.usage.service import UsageLimitExceededError, register_occurrence_usage


DEFAULT_JOB_TYPE = "document_processing"
JOB_TYPE_ANALYZE_FILE = "analyze_file"
JOB_TYPE_EXTRACT_TEXT = "extract_text"
JOB_TYPE_RUN_OCR = "run_ocr"
JOB_TYPE_CLASSIFY_DOCUMENT = "classify_document"
JOB_TYPE_SEGMENT_OCCURRENCES = "segment_occurrences"
JOB_TYPE_DETECT_SECTIONS = "detect_sections"
JOB_TYPE_EXTRACT_FIELDS = "extract_fields"
JOB_TYPE_VALIDATE_FIELDS = "validate_fields"
JOB_TYPE_BUILD_CANONICAL_MODEL = "build_canonical_model"
JOB_TYPE_APPLY_MAPPING = "apply_mapping"
JOB_TYPE_REGISTER_USAGE = "register_usage"


def enqueue_document_processing_job(
    db: Session,
    *,
    organization_id: str,
    document_id: str,
    priority: int = 100,
    metadata: Optional[dict[str, Any]] = None,
) -> ProcessingJob:
    job = ProcessingJob(
        organization_id=organization_id,
        document_id=document_id,
        job_type=DEFAULT_JOB_TYPE,
        status="pending",
        priority=priority,
        attempts=0,
        max_attempts=3,
        metadata_json=sanitize_metadata(metadata),
    )
    db.add(job)
    db.flush()
    return job


def claim_next_pending_job(db: Session) -> Optional[ProcessingJob]:
    job = (
        db.execute(
            select(ProcessingJob)
            .where(ProcessingJob.status == "pending")
            .order_by(ProcessingJob.priority, ProcessingJob.created_at, ProcessingJob.id)
            .limit(1)
        )
        .scalars()
        .first()
    )
    if job is None:
        return None

    now = datetime.now(timezone.utc)
    job.status = "running"
    job.attempts += 1
    job.locked_at = now
    job.started_at = now
    db.flush()
    return job


def mark_job_completed(db: Session, job: ProcessingJob) -> ProcessingJob:
    now = datetime.now(timezone.utc)
    job.status = "completed"
    job.finished_at = now
    job.error_code = None
    job.error_message = None
    db.flush()
    return job


def mark_job_failed(
    db: Session,
    job: ProcessingJob,
    *,
    error_code: str,
    error_message: str,
) -> ProcessingJob:
    now = datetime.now(timezone.utc)
    job.status = "failed"
    job.finished_at = now
    job.error_code = error_code
    job.error_message = error_message[:512]
    db.flush()
    return job


def _get_job_document(db: Session, job: ProcessingJob) -> Document:
    document = db.get(Document, job.document_id)
    if document is None:
        raise ValueError("document_not_found")
    if document.organization_id != job.organization_id:
        raise ValueError("document_organization_mismatch")
    return document


def _metadata_content(job: ProcessingJob) -> bytes:
    content = job.metadata_json.get("content_text", "")
    if isinstance(content, str):
        return content.encode("utf-8")
    return b""


def _resolve_job_content(job: ProcessingJob, content: Optional[bytes] = None) -> bytes:
    if content is not None:
        return content
    return _metadata_content(job)


def _metadata_content_type(job: ProcessingJob, document: Document) -> str:
    content_type = job.metadata_json.get("content_type")
    if isinstance(content_type, str) and content_type:
        return content_type
    return document.content_type


def _job_occurrences(db: Session, job: ProcessingJob) -> list[Occurrence]:
    document = _get_job_document(db, job)
    occurrence_id = job.metadata_json.get("occurrence_id")
    statement = select(Occurrence).where(
        Occurrence.organization_id == job.organization_id,
        Occurrence.document_id == document.id,
    )
    if isinstance(occurrence_id, str) and occurrence_id:
        statement = statement.where(Occurrence.id == occurrence_id)
    occurrences = list(
        db.execute(statement.order_by(Occurrence.sequence_number, Occurrence.id)).scalars()
    )
    if not occurrences:
        raise ValueError("occurrence_not_found")
    return occurrences


def _download_document_content(
    document: Document,
    storage_service: StorageService,
) -> bytes:
    if not document.storage_bucket or not document.storage_path:
        raise ValueError("storage_reference_missing")
    try:
        return storage_service.download(
            bucket=document.storage_bucket,
            object_path=document.storage_path,
        )
    except StorageObjectNotFoundError as exc:
        raise ValueError("storage_file_missing") from exc
    except StorageError as exc:
        raise ValueError("storage_download_failed") from exc


def _run_file_analysis(
    db: Session,
    job: ProcessingJob,
    *,
    content: Optional[bytes] = None,
) -> None:
    document = _get_job_document(db, job)
    result = FileAnalyzer().analyze(
        content=_resolve_job_content(job, content),
        content_type=_metadata_content_type(job, document),
        filename=document.original_filename,
    )
    metadata = dict(document.metadata_json)
    metadata["file_analysis"] = {
        "file_type": result.file_type,
        "page_count": result.page_count,
        "is_scanned": result.is_scanned,
        "ocr_required": result.ocr_required,
        "text_extractable": result.text_extractable,
    }
    document.metadata_json = metadata
    document.status = "analyzed"
    db.flush()


def _run_text_extraction(
    db: Session,
    job: ProcessingJob,
    *,
    content: Optional[bytes] = None,
) -> None:
    document = _get_job_document(db, job)
    pages = TextExtractionService().extract(
        content=_resolve_job_content(job, content),
        content_type=_metadata_content_type(job, document),
        filename=document.original_filename,
    )
    persist_extracted_pages(db, document=document, pages=pages)
    document.status = "text_extracted" if pages else "text_extraction_empty"
    db.flush()


def _run_ocr(
    db: Session,
    job: ProcessingJob,
    *,
    content: Optional[bytes] = None,
) -> None:
    document = _get_job_document(db, job)
    result = FakeOcrProvider().extract_text(
        content=_resolve_job_content(job, content),
        content_type=_metadata_content_type(job, document),
    )
    text_hash = sha256(result.text.encode("utf-8")).hexdigest() if result.text else None
    page = DocumentPage(
        organization_id=document.organization_id,
        document_id=document.id,
        page_number=int(job.metadata_json.get("page_number", 1)),
        extraction_method="ocr",
        text=result.text,
        text_hash=text_hash,
        confidence=result.confidence,
        status="extracted" if result.text else "empty",
        metadata_json={"provider": result.provider},
    )
    db.add(page)
    document.status = "ocr_completed"
    db.flush()


def _document_text(db: Session, document: Document) -> str:
    pages = list(
        db.execute(
            select(DocumentPage)
            .where(DocumentPage.document_id == document.id)
            .order_by(DocumentPage.page_number)
        ).scalars()
    )
    return "\n".join(page.text for page in pages if page.text)


def _document_has_pages(db: Session, document: Document) -> bool:
    page_id = db.execute(
        select(DocumentPage.id)
        .where(DocumentPage.document_id == document.id)
        .limit(1)
    ).scalar_one_or_none()
    return page_id is not None


def _run_classification(db: Session, job: ProcessingJob) -> None:
    document = _get_job_document(db, job)
    classification = DocumentClassifierV1().classify(_document_text(db, document))
    metadata = dict(document.metadata_json)
    metadata["classification"] = {
        "document_family": classification.document_family,
        "confidence": classification.confidence,
        "signals": list(classification.signals),
        "low_confidence": classification.low_confidence,
    }
    document.metadata_json = metadata
    document.status = "classified"
    db.flush()


def _run_segmentation(db: Session, job: ProcessingJob) -> None:
    document = _get_job_document(db, job)
    text = _document_text(db, document)
    classification = DocumentClassifierV1().classify(text)
    segments = OccurrenceSegmenterV1().segment(text)
    persist_occurrences(db, document=document, segments=segments, classification=classification)
    document.status = "segmented" if segments else "segmentation_empty"
    db.flush()


def _run_section_detection(db: Session, job: ProcessingJob) -> None:
    detector = SectionDetectorV1()
    for occurrence in _job_occurrences(db, job):
        metadata = dict(occurrence.metadata_json)
        metadata["sections"] = detector.detect(occurrence.text_excerpt)
        occurrence.metadata_json = metadata
        occurrence.status = "sections_detected"
    db.flush()


def _run_field_extraction(db: Session, job: ProcessingJob) -> None:
    for occurrence in _job_occurrences(db, job):
        extract_and_persist_fields(db, occurrence)
        occurrence.status = "fields_extracted"
    db.flush()


def _run_field_validation(db: Session, job: ProcessingJob) -> None:
    for occurrence in _job_occurrences(db, job):
        issues = validate_occurrence_fields(db, occurrence)
        occurrence.status = "validation_pending" if issues else "validated"
    db.flush()


def _run_canonical_model(db: Session, job: ProcessingJob) -> None:
    for occurrence in _job_occurrences(db, job):
        persist_canonical_model(db, occurrence)
    db.flush()


def _run_mapping(db: Session, job: ProcessingJob) -> None:
    for occurrence in _job_occurrences(db, job):
        persist_mercadoia_mapping(db, occurrence)
    db.flush()


def _run_usage_registration(db: Session, job: ProcessingJob) -> None:
    for occurrence in _job_occurrences(db, job):
        register_occurrence_usage(
            db,
            organization_id=occurrence.organization_id,
            occurrence_id=occurrence.id,
            request_id=job.metadata_json.get("request_id"),
            metadata={"job_id": job.id},
        )
        occurrence.status = "usage_registered"
    db.flush()


def _run_document_processing(
    db: Session,
    job: ProcessingJob,
    *,
    storage_service: StorageService,
) -> None:
    try:
        document = _get_job_document(db, job)
        content = _download_document_content(document, storage_service)

        _run_file_analysis(db, job, content=content)
        document = _get_job_document(db, job)
        file_analysis = document.metadata_json.get("file_analysis", {})

        if file_analysis.get("text_extractable"):
            _run_text_extraction(db, job, content=content)

        document = _get_job_document(db, job)
        if file_analysis.get("ocr_required") or not _document_has_pages(db, document):
            _run_ocr(db, job, content=content)

        _run_classification(db, job)
        _run_segmentation(db, job)
        _run_section_detection(db, job)
        _run_field_extraction(db, job)
        _run_field_validation(db, job)
        _run_canonical_model(db, job)
        _run_mapping(db, job)
        _run_usage_registration(db, job)
    except (UsageLimitExceededError, ValueError):
        raise
    except Exception as exc:
        raise ValueError("document_processing_failed") from exc


def process_job(
    db: Session,
    job: ProcessingJob,
    *,
    storage_service: Optional[StorageService] = None,
) -> ProcessingJob:
    if job.job_type == DEFAULT_JOB_TYPE:
        _run_document_processing(
            db,
            job,
            storage_service=storage_service or get_storage_service(),
        )
    elif job.job_type == JOB_TYPE_ANALYZE_FILE:
        _run_file_analysis(db, job)
    elif job.job_type == JOB_TYPE_EXTRACT_TEXT:
        _run_text_extraction(db, job)
    elif job.job_type == JOB_TYPE_RUN_OCR:
        _run_ocr(db, job)
    elif job.job_type == JOB_TYPE_CLASSIFY_DOCUMENT:
        _run_classification(db, job)
    elif job.job_type == JOB_TYPE_SEGMENT_OCCURRENCES:
        _run_segmentation(db, job)
    elif job.job_type == JOB_TYPE_DETECT_SECTIONS:
        _run_section_detection(db, job)
    elif job.job_type == JOB_TYPE_EXTRACT_FIELDS:
        _run_field_extraction(db, job)
    elif job.job_type == JOB_TYPE_VALIDATE_FIELDS:
        _run_field_validation(db, job)
    elif job.job_type == JOB_TYPE_BUILD_CANONICAL_MODEL:
        _run_canonical_model(db, job)
    elif job.job_type == JOB_TYPE_APPLY_MAPPING:
        _run_mapping(db, job)
    elif job.job_type == JOB_TYPE_REGISTER_USAGE:
        _run_usage_registration(db, job)
    return mark_job_completed(db, job)


def process_next_fake_job(
    db: Session,
    *,
    storage_service: Optional[StorageService] = None,
) -> Optional[ProcessingJob]:
    job = claim_next_pending_job(db)
    if job is None:
        return None
    try:
        return process_job(db, job, storage_service=storage_service)
    except (UsageLimitExceededError, ValueError) as exc:
        return mark_job_failed(
            db,
            job,
            error_code=str(exc),
            error_message="Pipeline job could not be processed.",
        )
