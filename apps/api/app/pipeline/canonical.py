from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import Evidence
from app.models.extracted_field import ExtractedField
from app.models.occurrence import Occurrence
from app.models.validation_issue import ValidationIssue


CANONICAL_SCHEMA_VERSION = "1.0"


def build_canonical_model(db: Session, occurrence: Occurrence) -> dict[str, Any]:
    fields = list(
        db.execute(
            select(ExtractedField)
            .where(ExtractedField.occurrence_id == occurrence.id)
            .order_by(ExtractedField.group_key, ExtractedField.field_key)
        ).scalars()
    )
    evidences = list(
        db.execute(
            select(Evidence)
            .where(Evidence.occurrence_id == occurrence.id)
            .order_by(Evidence.created_at, Evidence.id)
        ).scalars()
    )
    validation_issues = list(
        db.execute(
            select(ValidationIssue)
            .where(ValidationIssue.occurrence_id == occurrence.id)
            .order_by(ValidationIssue.created_at, ValidationIssue.id)
        ).scalars()
    )

    grouped_fields: dict[str, dict[str, Any]] = {}
    for field in fields:
        grouped_fields.setdefault(field.group_key, {})[field.field_key] = {
            "value": field.value,
            "status": field.status,
            "confidence": field.confidence,
            "evidence_id": field.evidence_id,
        }

    return {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "occurrence": {
            "id": occurrence.id,
            "document_id": occurrence.document_id,
            "document_family": occurrence.document_family,
            "status": occurrence.status,
        },
        "fields": grouped_fields,
        "evidences": [
            {
                "id": evidence.id,
                "field_key": evidence.field_key,
                "source_type": evidence.source_type,
                "confidence": evidence.confidence,
            }
            for evidence in evidences
        ],
        "validation": [
            {
                "field_key": issue.field_key,
                "issue_type": issue.issue_type,
                "severity": issue.severity,
                "status": issue.status,
            }
            for issue in validation_issues
        ],
    }


def persist_canonical_model(db: Session, occurrence: Occurrence) -> dict[str, Any]:
    canonical_model = build_canonical_model(db, occurrence)
    metadata = dict(occurrence.metadata_json)
    metadata["canonical_model"] = canonical_model
    occurrence.metadata_json = metadata
    occurrence.status = "canonical_built"
    db.flush()
    return canonical_model
