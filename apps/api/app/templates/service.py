from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.errors import AuthError
from app.core.config import Settings, get_settings
from app.models.generated_report import GeneratedReport
from app.models.occurrence import Occurrence
from app.pipeline.canonical import build_canonical_model
from app.pipeline.mapping import apply_mercadoia_mapping, load_mercadoia_mapping
from app.storage.paths import build_template_object_path
from app.storage.service import StorageService


TEMPLATE_VERSION = "mercadoia_v1"
TEMPLATE_CONTENT_TYPE = "text/plain; charset=utf-8"


@dataclass(frozen=True)
class TemplatePreview:
    template_version: str
    fields: list[dict[str, Any]]
    content: str


def _approved_required(occurrence: Occurrence) -> None:
    if occurrence.status != "aprovado":
        raise AuthError(
            400,
            "occurrence_not_approved",
            "Occurrence must be approved before template generation.",
        )


def mapped_fields_for_occurrence(db: Session, occurrence: Occurrence) -> list[dict[str, Any]]:
    metadata = occurrence.metadata_json or {}
    existing_mapping = metadata.get("mercadoia_mapping")
    if isinstance(existing_mapping, dict) and isinstance(existing_mapping.get("fields"), list):
        return list(existing_mapping["fields"])

    canonical_model = metadata.get("canonical_model")
    if canonical_model is None:
        canonical_model = build_canonical_model(db, occurrence)
    return apply_mercadoia_mapping(canonical_model, load_mercadoia_mapping())


def render_template_content(fields: list[dict[str, Any]]) -> str:
    lines = [
        "MercadoIA - Template V1",
        "Formato: texto deterministico para MVP",
        "",
    ]
    for field in fields:
        value = field.get("value")
        rendered_value = "" if value is None else str(value)
        lines.append(f"{field['template_field']}: {rendered_value}")
    lines.append("")
    return "\n".join(lines)


def build_template_preview(db: Session, occurrence: Occurrence) -> TemplatePreview:
    _approved_required(occurrence)
    fields = mapped_fields_for_occurrence(db, occurrence)
    missing_required = [
        field["template_field"]
        for field in fields
        if field.get("validation_status") == "missing_required"
    ]
    if missing_required:
        raise AuthError(
            400,
            "template_missing_required_fields",
            "Template cannot be generated with missing required fields.",
            {"missing_required": missing_required},
        )
    return TemplatePreview(
        template_version=TEMPLATE_VERSION,
        fields=fields,
        content=render_template_content(fields),
    )


def create_generated_report(
    db: Session,
    *,
    occurrence: Occurrence,
    generated_by_user_id: str,
    storage_service: StorageService,
    settings: Optional[Settings] = None,
) -> tuple[GeneratedReport, TemplatePreview]:
    resolved_settings = settings or get_settings()
    preview = build_template_preview(db, occurrence)
    report = GeneratedReport(
        organization_id=occurrence.organization_id,
        occurrence_id=occurrence.id,
        generated_by_user_id=generated_by_user_id,
        report_type="mercadoia_template",
        template_version=preview.template_version,
        status="pending_upload",
        storage_bucket=resolved_settings.supabase_storage_bucket_templates,
        storage_path="pending",
        storage_uri="pending",
        metadata_json={
            "field_count": len(preview.fields),
        },
    )
    db.add(report)
    db.flush()

    object_path = build_template_object_path(
        occurrence.organization_id,
        occurrence.id,
        f"{report.id}.txt",
    )
    storage_uri = storage_service.upload(
        bucket=resolved_settings.supabase_storage_bucket_templates,
        object_path=object_path,
        content=preview.content.encode("utf-8"),
        content_type=TEMPLATE_CONTENT_TYPE,
    )
    report.storage_path = object_path
    report.storage_uri = storage_uri
    report.status = "generated"
    db.flush()
    return report, preview


def get_generated_report_for_occurrence(
    db: Session,
    *,
    organization_id: str,
    occurrence_id: str,
    report_id: str,
) -> Optional[GeneratedReport]:
    return db.execute(
        select(GeneratedReport).where(
            GeneratedReport.id == report_id,
            GeneratedReport.occurrence_id == occurrence_id,
            GeneratedReport.organization_id == organization_id,
        )
    ).scalar_one_or_none()
