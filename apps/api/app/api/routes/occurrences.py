from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.audit_log import service as audit_log
from app.auth.dependencies import get_database_session
from app.auth.errors import AuthError
from app.core.config import get_settings
from app.middleware.request_context import REQUEST_ID_STATE_KEY
from app.models.document import Document
from app.models.extracted_field import ExtractedField
from app.models.occurrence import Occurrence
from app.models.review_version import ReviewVersion
from app.models.validation_issue import ValidationIssue
from app.occurrences.service import (
    checklist_for_occurrence,
    evidences_for_occurrence,
    field_value,
    fields_for_occurrence,
    get_occurrence_for_organization,
    mask_field_value,
    validation_issues_for_occurrence,
)
from app.permissions.dependencies import AuthorizedPermissionContext, require_permission
from app.storage.dependencies import get_storage_service
from app.storage.service import StorageService
from app.templates.service import (
    build_template_preview,
    create_generated_report,
    get_generated_report_for_occurrence,
)


router = APIRouter(prefix="/occurrences", tags=["occurrences"])


class OccurrenceListItem(BaseModel):
    id: str
    organization_id: str
    document_id: str
    sequence_number: int
    document_family: str
    status: str
    confidence: int
    numero_bo: Optional[str]
    tipo_sinistro: Optional[str]
    data_evento: Optional[str]
    cidade_evento: Optional[str]
    uf_evento: Optional[str]
    placa_principal: Optional[str]
    cpf_motorista: Optional[str]
    cnpj_vitima: Optional[str]
    pending_required: int
    blocking_issues: int
    document_filename: str
    created_at: datetime


class OccurrenceListResponse(BaseModel):
    items: list[OccurrenceListItem]
    page: int
    page_size: int
    total: int


class OccurrenceChecklistResponse(BaseModel):
    required_total: int
    pending_required: int
    blocking_issues: int
    can_approve: bool


class OccurrenceDetailResponse(BaseModel):
    id: str
    organization_id: str
    document_id: str
    sequence_number: int
    document_family: str
    status: str
    confidence: int
    text_excerpt: str
    metadata: dict
    checklist: OccurrenceChecklistResponse
    created_at: datetime
    updated_at: datetime


class EvidenceResponse(BaseModel):
    id: str
    field_key: Optional[str]
    source_type: str
    text_excerpt: str
    confidence: int


class ValidationIssueResponse(BaseModel):
    id: str
    field_key: str
    issue_type: str
    severity: str
    message: str
    status: str


class FieldResponse(BaseModel):
    id: str
    field_key: str
    group_key: str
    value: Optional[str]
    status: str
    confidence: int
    extraction_method: str
    evidence: Optional[EvidenceResponse]
    validation_issues: list[ValidationIssueResponse]


class FieldUpdateRequest(BaseModel):
    value: Optional[str] = None
    status: Optional[str] = None
    justification: Optional[str] = None


class FieldApproveRequest(BaseModel):
    justification: Optional[str] = None


class OccurrenceApprovalResponse(BaseModel):
    occurrence_id: str
    status: str
    snapshot_version: int


class TemplateFieldResponse(BaseModel):
    template_field: str
    value: Optional[str]
    status: str
    validation_status: str
    requires_review: bool


class TemplatePreviewResponse(BaseModel):
    occurrence_id: str
    template_version: str
    fields: list[TemplateFieldResponse]
    content_preview: str


class TemplateGenerationResponse(BaseModel):
    report_id: str
    occurrence_id: str
    status: str
    template_version: str
    storage_bucket: str
    storage_path: str


class TemplateDownloadUrlResponse(BaseModel):
    report_id: str
    occurrence_id: str
    signed_url: str
    expires_in: int


def _request_id(request: Request) -> Optional[str]:
    return getattr(request.state, REQUEST_ID_STATE_KEY, None)


def _not_found() -> AuthError:
    return AuthError(404, "occurrence_not_found", "Occurrence not found.")


def _field_not_found() -> AuthError:
    return AuthError(404, "field_not_found", "Field not found.")


def _report_not_found() -> AuthError:
    return AuthError(404, "generated_report_not_found", "Generated report not found.")


def _field_response(
    field: ExtractedField,
    *,
    evidence_lookup: dict[str, object],
    validation_issues: list[ValidationIssue],
    can_view_sensitive: bool,
) -> FieldResponse:
    evidence = evidence_lookup.get(field.evidence_id) if field.evidence_id else None
    return FieldResponse(
        id=field.id,
        field_key=field.field_key,
        group_key=field.group_key,
        value=mask_field_value(field.field_key, field.value, can_view_sensitive=can_view_sensitive),
        status=field.status,
        confidence=field.confidence,
        extraction_method=field.extraction_method,
        evidence=EvidenceResponse(
            id=evidence.id,
            field_key=evidence.field_key,
            source_type=evidence.source_type,
            text_excerpt=evidence.text_excerpt,
            confidence=evidence.confidence,
        )
        if evidence
        else None,
        validation_issues=[
            ValidationIssueResponse(
                id=issue.id,
                field_key=issue.field_key,
                issue_type=issue.issue_type,
                severity=issue.severity,
                message=issue.message,
                status=issue.status,
            )
            for issue in validation_issues
            if issue.field_id == field.id or issue.field_key == field.field_key
        ],
    )


def _can_view_sensitive(context: AuthorizedPermissionContext) -> bool:
    return context.permission_key == "sensitive_data_view"


def _snapshot_for_occurrence(
    db: Session,
    occurrence: Occurrence,
    *,
    version: int,
    approved_by_user_id: str,
    checklist: object,
) -> dict:
    fields = fields_for_occurrence(db, occurrence.id)
    return {
        "version": version,
        "approved_by_user_id": approved_by_user_id,
        "checklist": checklist.__dict__,
        "fields": [
            {
                "field_key": field.field_key,
                "group_key": field.group_key,
                "value": field.value,
                "status": field.status,
                "confidence": field.confidence,
                "evidence_id": field.evidence_id,
                "extraction_method": field.extraction_method,
            }
            for field in fields
        ],
    }


@router.get("", response_model=OccurrenceListResponse)
def list_occurrences(
    status: Optional[str] = None,
    q: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    context: AuthorizedPermissionContext = Depends(require_permission("occurrence_list")),
    db: Session = Depends(get_database_session),
):
    organization_id = context.current_organization.organization_id
    statement = (
        select(Occurrence)
        .join(Document, Document.id == Occurrence.document_id)
        .where(Occurrence.organization_id == organization_id)
        .order_by(Occurrence.created_at.desc(), Occurrence.id)
    )
    if status:
        statement = statement.where(Occurrence.status == status)

    all_items = list(db.execute(statement).scalars())
    if q:
        normalized_query = q.lower()
        filtered_items: list[Occurrence] = []
        for occurrence in all_items:
            fields = fields_for_occurrence(db, occurrence.id)
            fields_by_key = {field.field_key: field for field in fields}
            document = db.get(Document, occurrence.document_id)
            searchable_values = [
                occurrence.document_family,
                occurrence.status,
                document.original_filename if document else "",
                field_value(fields_by_key, "numero_bo") or "",
                field_value(fields_by_key, "tipo_sinistro") or "",
                field_value(fields_by_key, "cidade_evento") or "",
                field_value(fields_by_key, "uf_evento") or "",
            ]
            if any(normalized_query in value.lower() for value in searchable_values):
                filtered_items.append(occurrence)
        all_items = filtered_items
    paged_items = all_items[(page - 1) * page_size : page * page_size]
    responses: list[OccurrenceListItem] = []
    for occurrence in paged_items:
        fields = fields_for_occurrence(db, occurrence.id)
        fields_by_key = {field.field_key: field for field in fields}
        checklist = checklist_for_occurrence(db, occurrence.id)
        document = db.get(Document, occurrence.document_id)
        responses.append(
            OccurrenceListItem(
                id=occurrence.id,
                organization_id=occurrence.organization_id,
                document_id=occurrence.document_id,
                sequence_number=occurrence.sequence_number,
                document_family=occurrence.document_family,
                status=occurrence.status,
                confidence=occurrence.classification_confidence,
                numero_bo=field_value(fields_by_key, "numero_bo"),
                tipo_sinistro=field_value(fields_by_key, "tipo_sinistro"),
                data_evento=field_value(fields_by_key, "data_evento"),
                cidade_evento=field_value(fields_by_key, "cidade_evento"),
                uf_evento=field_value(fields_by_key, "uf_evento"),
                placa_principal=field_value(fields_by_key, "placa_veiculo_sinistrado"),
                cpf_motorista=field_value(fields_by_key, "cpf_motorista"),
                cnpj_vitima=field_value(fields_by_key, "cnpj_vitima"),
                pending_required=checklist.pending_required,
                blocking_issues=checklist.blocking_issues,
                document_filename=document.original_filename if document else "",
                created_at=occurrence.created_at,
            )
        )
    return OccurrenceListResponse(
        items=responses,
        page=page,
        page_size=page_size,
        total=len(all_items),
    )


@router.get("/{occurrence_id}", response_model=OccurrenceDetailResponse)
def get_occurrence(
    occurrence_id: str,
    context: AuthorizedPermissionContext = Depends(require_permission("occurrence_view")),
    db: Session = Depends(get_database_session),
):
    occurrence = get_occurrence_for_organization(
        db,
        organization_id=context.current_organization.organization_id,
        occurrence_id=occurrence_id,
    )
    if occurrence is None:
        raise _not_found()
    checklist = checklist_for_occurrence(db, occurrence.id)
    return OccurrenceDetailResponse(
        id=occurrence.id,
        organization_id=occurrence.organization_id,
        document_id=occurrence.document_id,
        sequence_number=occurrence.sequence_number,
        document_family=occurrence.document_family,
        status=occurrence.status,
        confidence=occurrence.classification_confidence,
        text_excerpt=occurrence.text_excerpt,
        metadata=occurrence.metadata_json,
        checklist=OccurrenceChecklistResponse(**checklist.__dict__),
        created_at=occurrence.created_at,
        updated_at=occurrence.updated_at,
    )


@router.get("/{occurrence_id}/fields", response_model=list[FieldResponse])
def list_occurrence_fields(
    occurrence_id: str,
    context: AuthorizedPermissionContext = Depends(require_permission("occurrence_view")),
    db: Session = Depends(get_database_session),
):
    occurrence = get_occurrence_for_organization(
        db,
        organization_id=context.current_organization.organization_id,
        occurrence_id=occurrence_id,
    )
    if occurrence is None:
        raise _not_found()
    evidence_lookup = evidences_for_occurrence(db, occurrence.id)
    issues = validation_issues_for_occurrence(db, occurrence.id)
    fields = fields_for_occurrence(db, occurrence.id)
    return [
        _field_response(
            field,
            evidence_lookup=evidence_lookup,
            validation_issues=issues,
            can_view_sensitive=False,
        )
        for field in fields
    ]


@router.patch("/{occurrence_id}/fields/{field_id}", response_model=FieldResponse)
def update_occurrence_field(
    occurrence_id: str,
    field_id: str,
    payload: FieldUpdateRequest,
    request: Request,
    context: AuthorizedPermissionContext = Depends(require_permission("review_field_edit")),
    db: Session = Depends(get_database_session),
):
    occurrence = get_occurrence_for_organization(
        db,
        organization_id=context.current_organization.organization_id,
        occurrence_id=occurrence_id,
    )
    if occurrence is None:
        raise _not_found()
    field = db.execute(
        select(ExtractedField).where(
            ExtractedField.id == field_id,
            ExtractedField.occurrence_id == occurrence.id,
            ExtractedField.organization_id == occurrence.organization_id,
        )
    ).scalar_one_or_none()
    if field is None:
        raise _field_not_found()

    changed: list[str] = []
    if payload.value is not None:
        field.value = payload.value
        field.status = "manual"
        field.confidence = 100
        changed.append("value")
    if payload.status is not None:
        field.status = payload.status
        changed.append("status")
    if payload.justification:
        metadata = dict(field.metadata_json)
        metadata["justification"] = payload.justification
        field.metadata_json = metadata
        changed.append("justification")

    audit_log.record(
        db,
        "review.field_updated",
        organization_id=occurrence.organization_id,
        user_id=context.current_user.user.id,
        target_type="extracted_field",
        target_id=field.id,
        request_id=_request_id(request),
        metadata={"field_key": field.field_key, "changed_fields": sorted(set(changed))},
    )
    db.commit()
    db.refresh(field)
    evidence_lookup = evidences_for_occurrence(db, occurrence.id)
    issues = validation_issues_for_occurrence(db, occurrence.id)
    return _field_response(
        field,
        evidence_lookup=evidence_lookup,
        validation_issues=issues,
        can_view_sensitive=False,
    )


@router.post("/{occurrence_id}/fields/{field_id}/approve", response_model=FieldResponse)
def approve_occurrence_field(
    occurrence_id: str,
    field_id: str,
    payload: FieldApproveRequest,
    request: Request,
    context: AuthorizedPermissionContext = Depends(require_permission("review_field_approve")),
    db: Session = Depends(get_database_session),
):
    occurrence = get_occurrence_for_organization(
        db,
        organization_id=context.current_organization.organization_id,
        occurrence_id=occurrence_id,
    )
    if occurrence is None:
        raise _not_found()
    field = db.execute(
        select(ExtractedField).where(
            ExtractedField.id == field_id,
            ExtractedField.occurrence_id == occurrence.id,
            ExtractedField.organization_id == occurrence.organization_id,
        )
    ).scalar_one_or_none()
    if field is None:
        raise _field_not_found()

    field.status = "aprovado"
    metadata = dict(field.metadata_json)
    if payload.justification:
        metadata["approval_justification"] = payload.justification
    metadata["approved_by_user_id"] = context.current_user.user.id
    field.metadata_json = metadata
    for issue in validation_issues_for_occurrence(db, occurrence.id):
        if issue.field_id == field.id or issue.field_key == field.field_key:
            issue.status = "resolved"

    audit_log.record(
        db,
        "review.field_approved",
        organization_id=occurrence.organization_id,
        user_id=context.current_user.user.id,
        target_type="extracted_field",
        target_id=field.id,
        request_id=_request_id(request),
        metadata={"field_key": field.field_key},
    )
    db.commit()
    db.refresh(field)
    evidence_lookup = evidences_for_occurrence(db, occurrence.id)
    issues = validation_issues_for_occurrence(db, occurrence.id)
    return _field_response(
        field,
        evidence_lookup=evidence_lookup,
        validation_issues=issues,
        can_view_sensitive=False,
    )


@router.post("/{occurrence_id}/approve", response_model=OccurrenceApprovalResponse)
def approve_occurrence(
    occurrence_id: str,
    request: Request,
    context: AuthorizedPermissionContext = Depends(require_permission("review_approve_occurrence")),
    db: Session = Depends(get_database_session),
):
    occurrence = get_occurrence_for_organization(
        db,
        organization_id=context.current_organization.organization_id,
        occurrence_id=occurrence_id,
    )
    if occurrence is None:
        raise _not_found()
    checklist = checklist_for_occurrence(db, occurrence.id)
    if not checklist.can_approve:
        raise AuthError(400, "occurrence_not_approvable", "Occurrence has pending required fields.")

    metadata = dict(occurrence.metadata_json)
    current_version = int(metadata.get("approved_snapshot", {}).get("version", 0)) + 1
    snapshot = _snapshot_for_occurrence(
        db,
        occurrence,
        version=current_version,
        approved_by_user_id=context.current_user.user.id,
        checklist=checklist,
    )
    metadata["approved_snapshot"] = {
        "version": current_version,
        "approved_by_user_id": context.current_user.user.id,
        "review_version_id": None,
    }
    occurrence.metadata_json = metadata
    occurrence.status = "aprovado"
    review_version = ReviewVersion(
        organization_id=occurrence.organization_id,
        occurrence_id=occurrence.id,
        version=current_version,
        approved_by_user_id=context.current_user.user.id,
        status="approved",
        snapshot_json=snapshot,
    )
    db.add(review_version)
    db.flush()
    metadata = dict(occurrence.metadata_json)
    metadata["approved_snapshot"]["review_version_id"] = review_version.id
    occurrence.metadata_json = metadata
    flag_modified(occurrence, "metadata_json")
    audit_log.record(
        db,
        "review.occurrence_approved",
        organization_id=occurrence.organization_id,
        user_id=context.current_user.user.id,
        target_type="occurrence",
        target_id=occurrence.id,
        request_id=_request_id(request),
        metadata={"snapshot_version": current_version},
    )
    db.commit()
    db.refresh(occurrence)
    return OccurrenceApprovalResponse(
        occurrence_id=occurrence.id,
        status=occurrence.status,
        snapshot_version=current_version,
    )


@router.post("/{occurrence_id}/templates/preview", response_model=TemplatePreviewResponse)
def preview_occurrence_template(
    occurrence_id: str,
    request: Request,
    context: AuthorizedPermissionContext = Depends(require_permission("template_generate")),
    db: Session = Depends(get_database_session),
):
    occurrence = get_occurrence_for_organization(
        db,
        organization_id=context.current_organization.organization_id,
        occurrence_id=occurrence_id,
    )
    if occurrence is None:
        raise _not_found()
    preview = build_template_preview(db, occurrence)
    audit_log.record(
        db,
        "template.previewed",
        organization_id=occurrence.organization_id,
        user_id=context.current_user.user.id,
        target_type="occurrence",
        target_id=occurrence.id,
        request_id=_request_id(request),
        metadata={
            "template_version": preview.template_version,
            "field_count": len(preview.fields),
        },
    )
    db.commit()
    return TemplatePreviewResponse(
        occurrence_id=occurrence.id,
        template_version=preview.template_version,
        fields=[
            TemplateFieldResponse(
                template_field=field["template_field"],
                value=field.get("value"),
                status=field["status"],
                validation_status=field["validation_status"],
                requires_review=field["requires_review"],
            )
            for field in preview.fields
        ],
        content_preview=preview.content,
    )


@router.post("/{occurrence_id}/templates/generate", response_model=TemplateGenerationResponse)
def generate_occurrence_template(
    occurrence_id: str,
    request: Request,
    context: AuthorizedPermissionContext = Depends(require_permission("template_generate")),
    db: Session = Depends(get_database_session),
    storage_service: StorageService = Depends(get_storage_service),
):
    occurrence = get_occurrence_for_organization(
        db,
        organization_id=context.current_organization.organization_id,
        occurrence_id=occurrence_id,
    )
    if occurrence is None:
        raise _not_found()
    report, preview = create_generated_report(
        db,
        occurrence=occurrence,
        generated_by_user_id=context.current_user.user.id,
        storage_service=storage_service,
    )
    audit_log.record(
        db,
        "template.generated",
        organization_id=occurrence.organization_id,
        user_id=context.current_user.user.id,
        target_type="generated_report",
        target_id=report.id,
        request_id=_request_id(request),
        metadata={
            "occurrence_id": occurrence.id,
            "template_version": preview.template_version,
            "field_count": len(preview.fields),
        },
    )
    db.commit()
    db.refresh(report)
    return TemplateGenerationResponse(
        report_id=report.id,
        occurrence_id=occurrence.id,
        status=report.status,
        template_version=report.template_version,
        storage_bucket=report.storage_bucket,
        storage_path=report.storage_path,
    )


@router.get(
    "/{occurrence_id}/templates/{report_id}/download-url",
    response_model=TemplateDownloadUrlResponse,
)
def create_occurrence_template_download_url(
    occurrence_id: str,
    report_id: str,
    request: Request,
    context: AuthorizedPermissionContext = Depends(require_permission("template_download")),
    db: Session = Depends(get_database_session),
    storage_service: StorageService = Depends(get_storage_service),
):
    report = get_generated_report_for_occurrence(
        db,
        organization_id=context.current_organization.organization_id,
        occurrence_id=occurrence_id,
        report_id=report_id,
    )
    if report is None:
        raise _report_not_found()
    settings = get_settings()
    signed_url = storage_service.create_signed_url(
        bucket=report.storage_bucket,
        object_path=report.storage_path,
        expires_in=settings.supabase_signed_url_ttl_seconds,
    )
    audit_log.record(
        db,
        "template.download_url_created",
        organization_id=report.organization_id,
        user_id=context.current_user.user.id,
        target_type="generated_report",
        target_id=report.id,
        request_id=_request_id(request),
        metadata={
            "occurrence_id": occurrence_id,
            "expires_in": settings.supabase_signed_url_ttl_seconds,
        },
    )
    db.commit()
    return TemplateDownloadUrlResponse(
        report_id=report.id,
        occurrence_id=occurrence_id,
        signed_url=signed_url,
        expires_in=settings.supabase_signed_url_ttl_seconds,
    )
