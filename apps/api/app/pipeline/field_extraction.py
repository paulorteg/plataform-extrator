from dataclasses import dataclass
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document_page import DocumentPage
from app.models.evidence import Evidence
from app.models.extracted_field import ExtractedField
from app.models.occurrence import Occurrence
from app.pipeline.field_catalog import FIELD_DEFINITIONS_BY_KEY


@dataclass(frozen=True)
class DeterministicMatch:
    field_key: str
    value: str
    start_offset: int
    end_offset: int
    confidence: int


FIELD_PATTERNS = (
    ("cnpj_vitima", re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")),
    ("cpf_motorista", re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")),
    ("placa_veiculo_sinistrado", re.compile(r"\b[A-Z]{3}[- ]?\d[A-Z0-9]\d{2}\b", re.IGNORECASE)),
    ("data_evento", re.compile(r"\b\d{2}/\d{2}/\d{4}\b")),
    ("numero_bo", re.compile(r"\b(?:BO|BOLETIM)\s*(?:N[ºO.]|NUMERO|NÚMERO)?\s*[:\-]?\s*([A-Z0-9./-]{4,})", re.IGNORECASE)),
)

LABEL_PATTERNS = (
    ("tipo_sinistro", re.compile(r"tipo\s+sinistro\s*[:\-]\s*([^\n;.]+)", re.IGNORECASE)),
    ("cidade_evento", re.compile(r"cidade\s+(?:do\s+)?evento\s*[:\-]\s*([A-Za-zÀ-ÿ ]+)", re.IGNORECASE)),
    ("uf_evento", re.compile(r"uf\s+(?:do\s+)?evento\s*[:\-]\s*([A-Z]{2})\b", re.IGNORECASE)),
    ("evento_natureza", re.compile(r"(?:evento|natureza)\s*[:\-]\s*([^\n;.]+)", re.IGNORECASE)),
    ("mercadoria", re.compile(r"mercadoria\s*[:\-]\s*([^\n;.]+)", re.IGNORECASE)),
    ("data_embarque", re.compile(r"data\s+embarque\s*[:\-]\s*(\d{2}/\d{2}/\d{4})", re.IGNORECASE)),
    ("cidade_emplacamento", re.compile(r"cidade\s+emplacamento\s*[:\-]\s*([A-Za-zÀ-ÿ ]+)", re.IGNORECASE)),
    ("uf_emplacamento", re.compile(r"uf\s+emplacamento\s*[:\-]\s*([A-Z]{2})\b", re.IGNORECASE)),
)


class DeterministicFieldExtractorV1:
    def extract(self, text: str) -> list[DeterministicMatch]:
        matches: list[DeterministicMatch] = []
        seen_fields: set[str] = set()
        for field_key, pattern in FIELD_PATTERNS:
            match = pattern.search(text)
            if match is None:
                continue
            value = match.group(1) if match.lastindex else match.group(0)
            matches.append(
                DeterministicMatch(
                    field_key=field_key,
                    value=value.strip(),
                    start_offset=match.start(),
                    end_offset=match.end(),
                    confidence=95,
                )
            )
            seen_fields.add(field_key)

        for field_key, pattern in LABEL_PATTERNS:
            if field_key in seen_fields:
                continue
            match = pattern.search(text)
            if match is None:
                continue
            matches.append(
                DeterministicMatch(
                    field_key=field_key,
                    value=match.group(1).strip(),
                    start_offset=match.start(1),
                    end_offset=match.end(1),
                    confidence=90,
                )
            )
        return matches


def _occurrence_document_text(db: Session, occurrence: Occurrence) -> str:
    pages = db.execute(
        select(DocumentPage)
        .where(DocumentPage.document_id == occurrence.document_id)
        .order_by(DocumentPage.page_number)
    ).scalars()
    return "\n".join(page.text for page in pages if page.text)


def _snippet(text: str, start: int, end: int) -> str:
    snippet_start = max(start - 40, 0)
    snippet_end = min(end + 40, len(text))
    return text[snippet_start:snippet_end].strip()


def persist_deterministic_fields(
    db: Session,
    *,
    occurrence: Occurrence,
    matches: list[DeterministicMatch],
    text: str,
) -> list[ExtractedField]:
    fields: list[ExtractedField] = []
    for match in matches:
        definition = FIELD_DEFINITIONS_BY_KEY[match.field_key]
        evidence = Evidence(
            organization_id=occurrence.organization_id,
            occurrence_id=occurrence.id,
            field_key=match.field_key,
            source_type="text",
            text_excerpt=_snippet(text, match.start_offset, match.end_offset),
            start_offset=match.start_offset,
            end_offset=match.end_offset,
            confidence=match.confidence,
            metadata_json={"extractor": "deterministic_v1"},
        )
        db.add(evidence)
        db.flush()
        field = ExtractedField(
            organization_id=occurrence.organization_id,
            occurrence_id=occurrence.id,
            evidence_id=evidence.id,
            field_key=match.field_key,
            group_key=definition.group_key,
            value=match.value,
            status="extraido",
            confidence=match.confidence,
            extraction_method="deterministic_v1",
            metadata_json={},
        )
        db.add(field)
        fields.append(field)
    db.flush()
    return fields


def extract_and_persist_fields(db: Session, occurrence: Occurrence) -> list[ExtractedField]:
    text = _occurrence_document_text(db, occurrence)
    matches = DeterministicFieldExtractorV1().extract(text)
    return persist_deterministic_fields(db, occurrence=occurrence, matches=matches, text=text)
