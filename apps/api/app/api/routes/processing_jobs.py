from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_database_session
from app.auth.errors import AuthError
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.permissions.dependencies import AuthorizedPermissionContext, require_permission


router = APIRouter(tags=["processing-jobs"])


class ProcessingJobErrorResponse(BaseModel):
    code: str
    message: str


class ProcessingJobResponse(BaseModel):
    id: str
    organization_id: str
    document_id: str
    job_type: str
    status: str
    priority: int
    attempts: int
    max_attempts: int
    created_at: datetime
    updated_at: datetime
    locked_at: Optional[datetime]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error: Optional[ProcessingJobErrorResponse]


class ProcessingJobListResponse(BaseModel):
    items: list[ProcessingJobResponse]
    total: int


def _not_found() -> AuthError:
    return AuthError(404, "processing_job_not_found", "Processing job not found.")


def _document_not_found() -> AuthError:
    return AuthError(404, "document_not_found", "Document not found.")


def _sanitize_error(job: ProcessingJob) -> Optional[ProcessingJobErrorResponse]:
    if job.status != "failed" and not job.error_code:
        return None
    return ProcessingJobErrorResponse(
        code=job.error_code or "processing_job_failed",
        message="Processing job failed.",
    )


def _job_response(job: ProcessingJob) -> ProcessingJobResponse:
    return ProcessingJobResponse(
        id=job.id,
        organization_id=job.organization_id,
        document_id=job.document_id,
        job_type=job.job_type,
        status=job.status,
        priority=job.priority,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        created_at=job.created_at,
        updated_at=job.updated_at,
        locked_at=job.locked_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error=_sanitize_error(job),
    )


@router.get("/processing-jobs/{job_id}", response_model=ProcessingJobResponse)
def get_processing_job(
    job_id: str,
    context: AuthorizedPermissionContext = Depends(require_permission("document_view")),
    db: Session = Depends(get_database_session),
):
    job = db.execute(
        select(ProcessingJob).where(
            ProcessingJob.id == job_id,
            ProcessingJob.organization_id == context.current_organization.organization_id,
        )
    ).scalar_one_or_none()
    if job is None:
        raise _not_found()
    return _job_response(job)


@router.get("/documents/{document_id}/processing-jobs", response_model=ProcessingJobListResponse)
def list_document_processing_jobs(
    document_id: str,
    context: AuthorizedPermissionContext = Depends(require_permission("document_view")),
    db: Session = Depends(get_database_session),
):
    document_exists = db.execute(
        select(Document.id).where(
            Document.id == document_id,
            Document.organization_id == context.current_organization.organization_id,
        )
    ).scalar_one_or_none()
    if document_exists is None:
        raise _document_not_found()

    jobs = list(
        db.execute(
            select(ProcessingJob)
            .where(
                ProcessingJob.document_id == document_id,
                ProcessingJob.organization_id == context.current_organization.organization_id,
            )
            .order_by(ProcessingJob.created_at.desc(), ProcessingJob.id.desc())
        ).scalars()
    )
    return ProcessingJobListResponse(
        items=[_job_response(job) for job in jobs],
        total=len(jobs),
    )
