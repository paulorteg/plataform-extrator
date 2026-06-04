from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: int
    provider: str


class OcrProvider(Protocol):
    def extract_text(self, *, content: bytes, content_type: str) -> OcrResult:
        ...


class FakeOcrProvider:
    provider_name = "fake"

    def extract_text(self, *, content: bytes, content_type: str) -> OcrResult:
        marker = content.decode("utf-8", errors="ignore").strip()
        text = marker if marker else "BOLETIM DE OCORRENCIA OCR FAKE"
        return OcrResult(text=text, confidence=80, provider=self.provider_name)
