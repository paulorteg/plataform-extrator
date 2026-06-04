from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit_log import service as audit_log_service
from app.auth.dependencies import get_database_session
from app.middleware.request_context import REQUEST_ID_STATE_KEY
from app.models.audit_log import AuditLog
from app.permissions.dependencies import AuthorizedPermissionContext, require_permission


router = APIRouter(prefix="/audit-logs", tags=["audit"])


class AuditLogItem(BaseModel):
    id: str
    event_type: str
    organization_id: Optional[str]
    user_id: Optional[str]
    target_type: Optional[str]
    target_id: Optional[str]
    request_id: Optional[str]
    metadata: dict
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogItem]
    page: int
    page_size: int
    total: int


class AuditLogExportResponse(BaseModel):
    format: str
    items: list[AuditLogItem]
    total: int


def _request_id(request: Request) -> Optional[str]:
    return getattr(request.state, REQUEST_ID_STATE_KEY, None)


def _audit_item(audit_log: AuditLog) -> AuditLogItem:
    return AuditLogItem(
        id=audit_log.id,
        event_type=audit_log.event_type,
        organization_id=audit_log.organization_id,
        user_id=audit_log.user_id,
        target_type=audit_log.target_type,
        target_id=audit_log.target_id,
        request_id=audit_log.request_id,
        metadata=audit_log.metadata_json,
        created_at=audit_log.created_at,
    )


def _audit_query(
    *,
    organization_id: str,
    event_type: Optional[str],
    target_type: Optional[str],
    request_id: Optional[str],
):
    statement = select(AuditLog).where(AuditLog.organization_id == organization_id)
    if event_type:
        statement = statement.where(AuditLog.event_type == event_type)
    if target_type:
        statement = statement.where(AuditLog.target_type == target_type)
    if request_id:
        statement = statement.where(AuditLog.request_id == request_id)
    return statement.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    event_type: Optional[str] = None,
    target_type: Optional[str] = None,
    request_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    context: AuthorizedPermissionContext = Depends(require_permission("audit_view")),
    db: Session = Depends(get_database_session),
):
    statement = _audit_query(
        organization_id=context.current_organization.organization_id,
        event_type=event_type,
        target_type=target_type,
        request_id=request_id,
    )
    all_items = list(db.execute(statement).scalars())
    paged_items = all_items[(page - 1) * page_size : page * page_size]
    return AuditLogListResponse(
        items=[_audit_item(item) for item in paged_items],
        page=page,
        page_size=page_size,
        total=len(all_items),
    )


@router.post("/export", response_model=AuditLogExportResponse)
def export_audit_logs(
    request: Request,
    event_type: Optional[str] = None,
    target_type: Optional[str] = None,
    context: AuthorizedPermissionContext = Depends(require_permission("audit_export")),
    db: Session = Depends(get_database_session),
):
    statement = _audit_query(
        organization_id=context.current_organization.organization_id,
        event_type=event_type,
        target_type=target_type,
        request_id=None,
    )
    all_items = list(db.execute(statement).scalars())
    audit_log_service.record(
        db,
        "audit.exported",
        organization_id=context.current_organization.organization_id,
        user_id=context.current_user.user.id,
        target_type="audit_logs",
        request_id=_request_id(request),
        metadata={"event_type": event_type, "target_type": target_type, "row_count": len(all_items)},
    )
    db.commit()
    return AuditLogExportResponse(
        format="json",
        items=[_audit_item(item) for item in all_items],
        total=len(all_items),
    )
