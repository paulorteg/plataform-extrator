from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.evidence import Evidence
from app.models.extracted_field import ExtractedField
from app.models.occurrence import Occurrence
from app.models.validation_issue import ValidationIssue
from app.pipeline.field_catalog import REQUIRED_FIELD_KEYS


SENSITIVE_FIELD_KEYS = {"cpf_motorista", "cnpj_vitima"}


@dataclass(frozen=True)
class OccurrenceChecklist:
    required_total: int
    pending_required: int
    blocking_issues: int
    can_approve: bool


def mask_cpf(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    digits = "".join(char for char in value if char.isdigit())
    if len(digits) != 11:
        return "***"
    return f"{digits[:3]}*****{digits[-2:]}"


def mask_cnpj(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    digits = "".join(char for char in value if char.isdigit())
    if len(digits) != 14:
        return "**.***.***/****"
    return f"{digits[:2]}.***.***/****{digits[-2:]}"


def mask_field_value(field_key: str, value: Optional[str], *, can_view_sensitive: bool) -> Optional[str]:
    if can_view_sensitive or field_key not in SENSITIVE_FIELD_KEYS:
        return value
    if field_key == "cpf_motorista":
        return mask_cpf(value)
    if field_key == "cnpj_vitima":
        return mask_cnpj(value)
    return "***"


def field_value(
    fields_by_key: dict[str, ExtractedField],
    field_key: str,
    *,
    can_view_sensitive: bool = False,
) -> Optional[str]:
    field = fields_by_key.get(field_key)
    if field is None:
        return None
    return mask_field_value(field_key, field.value, can_view_sensitive=can_view_sensitive)


def fields_for_occurrence(db: Session, occurrence_id: str) -> list[ExtractedField]:
    return list(
        db.execute(
            select(ExtractedField)
            .where(ExtractedField.occurrence_id == occurrence_id)
            .order_by(ExtractedField.group_key, ExtractedField.field_key)
        ).scalars()
    )


def evidences_for_occurrence(db: Session, occurrence_id: str) -> dict[str, Evidence]:
    evidences = db.execute(
        select(Evidence).where(Evidence.occurrence_id == occurrence_id)
    ).scalars()
    return {evidence.id: evidence for evidence in evidences}


def validation_issues_for_occurrence(db: Session, occurrence_id: str) -> list[ValidationIssue]:
    return list(
        db.execute(
            select(ValidationIssue)
            .where(ValidationIssue.occurrence_id == occurrence_id)
            .order_by(ValidationIssue.created_at, ValidationIssue.id)
        ).scalars()
    )


def checklist_for_occurrence(db: Session, occurrence_id: str) -> OccurrenceChecklist:
    fields = fields_for_occurrence(db, occurrence_id)
    valid_required = {
        field.field_key
        for field in fields
        if field.field_key in REQUIRED_FIELD_KEYS
        and field.status in {"extraido", "manual", "aprovado", "justificado"}
    }
    pending_required = len(set(REQUIRED_FIELD_KEYS) - valid_required)
    blocking_issues = (
        db.execute(
            select(func.count(ValidationIssue.id)).where(
                ValidationIssue.occurrence_id == occurrence_id,
                ValidationIssue.status == "open",
                ValidationIssue.severity == "blocking",
            )
        ).scalar_one()
        or 0
    )
    return OccurrenceChecklist(
        required_total=len(REQUIRED_FIELD_KEYS),
        pending_required=pending_required,
        blocking_issues=int(blocking_issues),
        can_approve=pending_required == 0 and int(blocking_issues) == 0,
    )


def get_occurrence_for_organization(
    db: Session,
    *,
    organization_id: str,
    occurrence_id: str,
) -> Optional[Occurrence]:
    return db.execute(
        select(Occurrence).where(
            Occurrence.id == occurrence_id,
            Occurrence.organization_id == organization_id,
        )
    ).scalar_one_or_none()
