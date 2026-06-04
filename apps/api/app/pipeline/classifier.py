from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentClassification:
    document_family: str
    confidence: int
    signals: tuple[str, ...]
    low_confidence: bool


class DocumentClassifierV1:
    def classify(self, text: str) -> DocumentClassification:
        normalized = text.upper()
        signals: list[str] = []
        if "BOLETIM" in normalized:
            signals.append("boletim")
        if "OCORRENCIA" in normalized or "OCORRÊNCIA" in normalized:
            signals.append("ocorrencia")
        if "POLICIA" in normalized or "POLÍCIA" in normalized:
            signals.append("policia")
        if "SINISTRO" in normalized:
            signals.append("sinistro")

        confidence = min(30 + len(signals) * 20, 95)
        document_family = "boletim_ocorrencia" if len(signals) >= 2 else "unknown"
        return DocumentClassification(
            document_family=document_family,
            confidence=confidence,
            signals=tuple(signals),
            low_confidence=confidence < 70,
        )
