from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit_log.service import sanitize_metadata
from app.models.processing_job import ProcessingJob


DEFAULT_JOB_TYPE = "document_processing"


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


def process_next_fake_job(db: Session) -> Optional[ProcessingJob]:
    job = claim_next_pending_job(db)
    if job is None:
        return None
    return mark_job_completed(db, job)
