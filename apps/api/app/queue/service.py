from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit_log.service import sanitize_metadata
from app.models.document import Document
from app.models.document_page import DocumentPage
from app.models.processing_job import ProcessingJob
from app.pipeline.classifier import DocumentClassifierV1
from app.pipeline.file_analyzer import FileAnalyzer
from app.pipeline.ocr import FakeOcrProvider
from app.pipeline.segmentation import OccurrenceSegmenterV1, persist_occurrences
from app.pipeline.text_extraction import TextExtractionService, persist_extracted_pages


DEFAULT_JOB_TYPE = "document_processing"
JOB_TYPE_ANALYZE_FILE = "analyze_file"
JOB_TYPE_EXTRACT_TEXT = "extract_text"
JOB_TYPE_RUN_OCR = "run_ocr"
JOB_TYPE_CLASSIFY_DOCUMENT = "classify_document"
JOB_TYPE_SEGMENT_OCCURRENCES = "segment_occurrences"


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


def _metadata_content_type(job: ProcessingJob, document: Document) -> str:
    content_type = job.metadata_json.get("content_type")
    if isinstance(content_type, str) and content_type:
        return content_type
    return document.content_type


def _run_file_analysis(db: Session, job: ProcessingJob) -> None:
    document = _get_job_document(db, job)
    result = FileAnalyzer().analyze(
        content=_metadata_content(job),
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


def _run_text_extraction(db: Session, job: ProcessingJob) -> None:
    document = _get_job_document(db, job)
    pages = TextExtractionService().extract(
        content=_metadata_content(job),
        content_type=_metadata_content_type(job, document),
        filename=document.original_filename,
    )
    persist_extracted_pages(db, document=document, pages=pages)
    document.status = "text_extracted" if pages else "text_extraction_empty"
    db.flush()


def _run_ocr(db: Session, job: ProcessingJob) -> None:
    document = _get_job_document(db, job)
    result = FakeOcrProvider().extract_text(
        content=_metadata_content(job),
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


def process_job(db: Session, job: ProcessingJob) -> ProcessingJob:
    if job.job_type == JOB_TYPE_ANALYZE_FILE:
        _run_file_analysis(db, job)
    elif job.job_type == JOB_TYPE_EXTRACT_TEXT:
        _run_text_extraction(db, job)
    elif job.job_type == JOB_TYPE_RUN_OCR:
        _run_ocr(db, job)
    elif job.job_type == JOB_TYPE_CLASSIFY_DOCUMENT:
        _run_classification(db, job)
    elif job.job_type == JOB_TYPE_SEGMENT_OCCURRENCES:
        _run_segmentation(db, job)
    return mark_job_completed(db, job)


def process_next_fake_job(db: Session) -> Optional[ProcessingJob]:
    job = claim_next_pending_job(db)
    if job is None:
        return None
    try:
        return process_job(db, job)
    except ValueError as exc:
        return mark_job_failed(
            db,
            job,
            error_code=str(exc),
            error_message="Pipeline job could not be processed.",
        )
