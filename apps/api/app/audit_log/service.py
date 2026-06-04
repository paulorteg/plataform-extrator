from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


SENSITIVE_METADATA_KEYS = {
    "authorization",
    "authorization_header",
    "access_token",
    "refresh_token",
    "token",
    "jwt",
    "password",
    "password_hash",
    "senha",
    "secret",
    "service_role",
    "ocr",
    "ocr_text",
    "prompt",
    "narrative",
    "narrativa",
    "document",
    "document_text",
}
MAX_METADATA_STRING_LENGTH = 256


def _sanitize_metadata_value(value: Any) -> Any:
    if isinstance(value, dict):
        return sanitize_metadata(value)
    if isinstance(value, list):
        return [_sanitize_metadata_value(item) for item in value]
    if isinstance(value, str) and len(value) > MAX_METADATA_STRING_LENGTH:
        return f"{value[:MAX_METADATA_STRING_LENGTH]}...[truncated]"
    return value


def sanitize_metadata(metadata: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not metadata:
        return {}

    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized_key = key.lower()
        if normalized_key in SENSITIVE_METADATA_KEYS:
            sanitized[key] = "[REDACTED]"
            continue
        sanitized[key] = _sanitize_metadata_value(value)
    return sanitized


def record(
    db: Session,
    event_type: str,
    *,
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    request_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> AuditLog:
    audit_log = AuditLog(
        event_type=event_type,
        organization_id=organization_id,
        user_id=user_id,
        target_type=target_type,
        target_id=target_id,
        request_id=request_id,
        metadata_json=sanitize_metadata(metadata),
    )
    db.add(audit_log)
    db.flush()
    return audit_log


def list_by_organization(db: Session, organization_id: str) -> list[AuditLog]:
    return list(
        db.execute(
            select(AuditLog)
            .where(AuditLog.organization_id == organization_id)
            .order_by(AuditLog.created_at, AuditLog.id)
        ).scalars()
    )
