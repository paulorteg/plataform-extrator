from dataclasses import dataclass
import re

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.occurrence import Occurrence
from app.pipeline.classifier import DocumentClassification


@dataclass(frozen=True)
class OccurrenceSegment:
    sequence_number: int
    text: str


class OccurrenceSegmenterV1:
    marker_pattern = re.compile(
        r"(?=\bBOLETIM\s+(?:DE\s+)?OCORR[ÊE]NCIA)"
        r"|(?=\bBO\s*(?:N[ºO.]|NUMERO|NÚMERO))"
        r"|(?<!DE )(?=\bOCORR[ÊE]NCIA\s+\d+)",
        re.IGNORECASE,
    )

    def segment(self, text: str) -> list[OccurrenceSegment]:
        stripped_text = text.strip()
        if not stripped_text:
            return []

        parts = [part.strip() for part in self.marker_pattern.split(stripped_text) if part.strip()]
        if not parts:
            parts = [stripped_text]
        return [
            OccurrenceSegment(sequence_number=index + 1, text=part)
            for index, part in enumerate(parts)
        ]


def persist_occurrences(
    db: Session,
    *,
    document: Document,
    segments: list[OccurrenceSegment],
    classification: DocumentClassification,
) -> list[Occurrence]:
    occurrences: list[Occurrence] = []
    for segment in segments:
        occurrence = Occurrence(
            organization_id=document.organization_id,
            document_id=document.id,
            sequence_number=segment.sequence_number,
            document_family=classification.document_family,
            classification_confidence=classification.confidence,
            status="segmented",
            text_excerpt=segment.text[:1024],
            metadata_json={
                "low_confidence": classification.low_confidence,
                "signals": list(classification.signals),
            },
        )
        db.add(occurrence)
        occurrences.append(occurrence)
    db.flush()
    return occurrences
