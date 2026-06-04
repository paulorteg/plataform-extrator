from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_page import DocumentPage


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    extraction_method: str


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class TextExtractionService:
    def extract(
        self,
        *,
        content: bytes,
        content_type: str,
        filename: str = "",
    ) -> list[ExtractedPage]:
        lower_filename = filename.lower()
        if content_type == "application/pdf" or lower_filename.endswith(".pdf"):
            return self._extract_pdf_text(content)
        if (
            content_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            or lower_filename.endswith(".docx")
        ):
            return [
                ExtractedPage(
                    page_number=1,
                    text=self._extract_docx_text(content),
                    extraction_method="digital",
                )
            ]
        return []

    def _extract_pdf_text(self, content: bytes) -> list[ExtractedPage]:
        text = content.decode("latin-1", errors="ignore")
        text = _clean_text(text)
        if not text:
            return []
        return [ExtractedPage(page_number=1, text=text, extraction_method="digital")]

    def _extract_docx_text(self, content: bytes) -> str:
        with ZipFile(BytesIO(content)) as docx:
            xml_content = docx.read("word/document.xml")
        root = ET.fromstring(xml_content)
        texts = [
            node.text or ""
            for node in root.iter()
            if node.tag.endswith("}t") or node.tag == "t"
        ]
        return _clean_text(" ".join(texts))


def persist_extracted_pages(
    db: Session,
    *,
    document: Document,
    pages: list[ExtractedPage],
) -> list[DocumentPage]:
    persisted_pages: list[DocumentPage] = []
    for page in pages:
        text_hash = sha256(page.text.encode("utf-8")).hexdigest() if page.text else None
        document_page = DocumentPage(
            organization_id=document.organization_id,
            document_id=document.id,
            page_number=page.page_number,
            extraction_method=page.extraction_method,
            text=page.text,
            text_hash=text_hash,
            confidence=100 if page.text else 0,
            status="extracted" if page.text else "empty",
            metadata_json={},
        )
        db.add(document_page)
        persisted_pages.append(document_page)
    db.flush()
    return persisted_pages
