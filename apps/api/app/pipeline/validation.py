import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.extracted_field import ExtractedField
from app.models.occurrence import Occurrence
from app.models.validation_issue import ValidationIssue
from app.pipeline.field_catalog import FIELD_DEFINITIONS, FIELD_DEFINITIONS_BY_KEY


CPF_PATTERN = re.compile(r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$")
CNPJ_PATTERN = re.compile(r"^\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}$")
DATE_PATTERN = re.compile(r"^\d{2}/\d{2}/\d{4}$")
UF_PATTERN = re.compile(r"^[A-Z]{2}$")
PLATE_PATTERN = re.compile(r"^[A-Z]{3}[- ]?\d[A-Z0-9]\d{2}$", re.IGNORECASE)


def _is_valid(field: ExtractedField) -> bool:
    validation = FIELD_DEFINITIONS_BY_KEY[field.field_key].validation
    value = (field.value or "").strip()
    if validation == "cpf":
        return bool(CPF_PATTERN.match(value))
    if validation == "cnpj":
        return bool(CNPJ_PATTERN.match(value))
    if validation == "date":
        return bool(DATE_PATTERN.match(value))
    if validation == "uf":
        return bool(UF_PATTERN.match(value.upper()))
    if validation == "placa_brasil":
        return bool(PLATE_PATTERN.match(value.upper()))
    return bool(value)


def validate_occurrence_fields(db: Session, occurrence: Occurrence) -> list[ValidationIssue]:
    fields = list(
        db.execute(
            select(ExtractedField).where(ExtractedField.occurrence_id == occurrence.id)
        ).scalars()
    )
    fields_by_key = {field.field_key: field for field in fields}
    issues: list[ValidationIssue] = []

    for definition in FIELD_DEFINITIONS:
        field = fields_by_key.get(definition.field_key)
        if field is None:
            if not definition.required:
                continue
            issue = ValidationIssue(
                organization_id=occurrence.organization_id,
                occurrence_id=occurrence.id,
                field_key=definition.field_key,
                issue_type="required_missing",
                severity="blocking",
                message="Campo obrigatorio ausente.",
                status="open",
                metadata_json={},
            )
            db.add(issue)
            issues.append(issue)
            continue
        if not _is_valid(field):
            field.status = "invalido"
            issue = ValidationIssue(
                organization_id=occurrence.organization_id,
                occurrence_id=occurrence.id,
                field_id=field.id,
                field_key=definition.field_key,
                issue_type="invalid_format",
                severity="blocking" if definition.required else "warning",
                message="Campo extraido nao atende ao formato esperado.",
                status="open",
                metadata_json={"validation": definition.validation},
            )
            db.add(issue)
            issues.append(issue)
        elif field.confidence < 70:
            field.status = "baixa_confianca"
            issue = ValidationIssue(
                organization_id=occurrence.organization_id,
                occurrence_id=occurrence.id,
                field_id=field.id,
                field_key=definition.field_key,
                issue_type="low_confidence",
                severity="warning",
                message="Campo extraido com baixa confianca.",
                status="open",
                metadata_json={},
            )
            db.add(issue)
            issues.append(issue)
    db.flush()
    return issues
