from hashlib import sha256
from typing import Optional

from fastapi import APIRouter, Depends, File, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit_log import service as audit_log
from app.auth.dependencies import get_database_session
from app.auth.errors import AuthError
from app.core.config import get_settings
from app.middleware.request_context import REQUEST_ID_STATE_KEY
from app.models.document import Document
from app.permissions.dependencies import AuthorizedPermissionContext, require_permission
from app.queue.service import enqueue_document_processing_job
from app.storage.dependencies import get_storage_service
from app.storage.paths import build_document_object_path
from app.storage.service import StorageError, StorageService, build_storage_uri


router = APIRouter(prefix="/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
}


class DocumentUploadResponse(BaseModel):
    document_id: str
    job_id: str
    organization_id: str
    status: str
    storage_uri: str
    sha256_hash: str
    size_bytes: int


def _safe_filename(filename: Optional[str]) -> str:
    if not filename:
        return "uploaded-document"
    return filename.replace("\\", "/").split("/")[-1][:255] or "uploaded-document"


def _validate_upload(content: bytes, content_type: str) -> None:
    if not content:
        raise AuthError(400, "empty_file", "Uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise AuthError(413, "file_too_large", "Uploaded file is too large.")
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise AuthError(400, "unsupported_file_type", "Unsupported file type.")


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    context: AuthorizedPermissionContext = Depends(require_permission("document_upload")),
    db: Session = Depends(get_database_session),
    storage_service: StorageService = Depends(get_storage_service),
):
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"
    _validate_upload(content, content_type)

    settings = get_settings()
    filename = _safe_filename(file.filename)
    document_hash = sha256(content).hexdigest()
    document = Document(
        organization_id=context.current_organization.organization_id,
        uploaded_by_user_id=context.current_user.user.id,
        original_filename=filename,
        content_type=content_type,
        size_bytes=len(content),
        sha256_hash=document_hash,
        storage_bucket=settings.supabase_storage_bucket_documents,
        storage_path="pending",
        storage_uri="pending",
        status="uploading",
        metadata_json={},
    )
    db.add(document)
    db.flush()

    object_path = build_document_object_path(
        context.current_organization.organization_id,
        document.id,
    )
    storage_uri = build_storage_uri(settings.supabase_storage_bucket_documents, object_path)

    try:
        storage_service.upload(
            bucket=settings.supabase_storage_bucket_documents,
            object_path=object_path,
            content=content,
            content_type=content_type,
        )
    except StorageError as exc:
        raise AuthError(502, "storage_upload_failed", "Storage upload failed.") from exc

    document.storage_path = object_path
    document.storage_uri = storage_uri
    document.status = "uploaded"
    job = enqueue_document_processing_job(
        db,
        organization_id=context.current_organization.organization_id,
        document_id=document.id,
        metadata={"document_id": document.id},
    )
    audit_log.record(
        db,
        "document.uploaded",
        organization_id=context.current_organization.organization_id,
        user_id=context.current_user.user.id,
        target_type="document",
        target_id=document.id,
        request_id=getattr(request.state, REQUEST_ID_STATE_KEY, None),
        metadata={
            "document_id": document.id,
            "content_type": content_type,
            "size_bytes": len(content),
            "sha256_hash": document_hash,
        },
    )
    db.commit()
    db.refresh(document)
    db.refresh(job)
    return DocumentUploadResponse(
        document_id=document.id,
        job_id=job.id,
        organization_id=document.organization_id,
        status=document.status,
        storage_uri=document.storage_uri,
        sha256_hash=document.sha256_hash,
        size_bytes=document.size_bytes,
    )
