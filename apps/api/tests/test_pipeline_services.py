from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Document, DocumentPage, Occurrence, Organization, User
from app.pipeline.classifier import DocumentClassifierV1
from app.pipeline.file_analyzer import FileAnalyzer
from app.pipeline.ocr import FakeOcrProvider
from app.pipeline.segmentation import OccurrenceSegmenterV1, persist_occurrences
from app.pipeline.text_extraction import TextExtractionService, persist_extracted_pages


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _make_docx(text: str) -> bytes:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>"
        f"{text}"
        "</w:t></w:r></w:p></w:body></w:document>"
    )
    buffer = BytesIO()
    with ZipFile(buffer, "w") as docx:
        docx.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def _create_document(session: Session) -> Document:
    organization = Organization(
        name=f"Organization {uuid4()}",
        legal_name="Organization LTDA",
        cnpj_hash=f"hash_{uuid4()}",
        status="active",
        retention_days=180,
    )
    user = User(
        auth_user_id=str(uuid4()),
        name="Pipeline User",
        email=f"{uuid4()}@example.test",
        status="active",
    )
    session.add_all([organization, user])
    session.flush()
    document = Document(
        organization_id=organization.id,
        uploaded_by_user_id=user.id,
        original_filename="bo.pdf",
        content_type="application/pdf",
        size_bytes=32,
        sha256_hash="b" * 64,
        storage_bucket="documents",
        storage_path=f"organizations/{organization.id}/documents/{uuid4()}/original",
        storage_uri=f"supabase://documents/organizations/{organization.id}/documents/{uuid4()}/original",
        status="uploaded",
        metadata_json={},
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def test_file_analyzer_detects_digital_pdf_scanned_pdf_docx_and_image():
    analyzer = FileAnalyzer()

    digital_pdf = analyzer.analyze(
        content=b"%PDF /Type /Page BT BOLETIM",
        content_type="application/pdf",
        filename="bo.pdf",
    )
    scanned_pdf = analyzer.analyze(
        content=b"%PDF /Type /Page image-only",
        content_type="application/pdf",
        filename="scan.pdf",
    )
    docx = analyzer.analyze(
        content=_make_docx("BOLETIM DE OCORRENCIA"),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="bo.docx",
    )
    image = analyzer.analyze(content=b"image", content_type="image/png", filename="bo.png")

    assert digital_pdf.file_type == "pdf"
    assert digital_pdf.text_extractable is True
    assert digital_pdf.ocr_required is False
    assert scanned_pdf.is_scanned is True
    assert scanned_pdf.ocr_required is True
    assert docx.file_type == "docx"
    assert docx.text_extractable is True
    assert image.file_type == "image"
    assert image.ocr_required is True


def test_text_extraction_extracts_pdf_and_docx_text():
    service = TextExtractionService()

    pdf_pages = service.extract(
        content=b"%PDF BT BOLETIM DE OCORRENCIA POLICIA",
        content_type="application/pdf",
        filename="bo.pdf",
    )
    docx_pages = service.extract(
        content=_make_docx("BOLETIM DE OCORRENCIA DOCX"),
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="bo.docx",
    )

    assert pdf_pages[0].page_number == 1
    assert "BOLETIM DE OCORRENCIA" in pdf_pages[0].text
    assert docx_pages == [
        docx_pages[0].__class__(
            page_number=1,
            text="BOLETIM DE OCORRENCIA DOCX",
            extraction_method="digital",
        )
    ]


def test_persist_extracted_pages_creates_pages_and_blocks_duplicate_page(db_session):
    document = _create_document(db_session)
    pages = TextExtractionService().extract(
        content=b"%PDF BT BOLETIM DE OCORRENCIA",
        content_type="application/pdf",
        filename="bo.pdf",
    )

    persisted = persist_extracted_pages(db_session, document=document, pages=pages)
    db_session.commit()

    assert persisted[0].organization_id == document.organization_id
    assert persisted[0].extraction_method == "digital"
    assert persisted[0].text_hash is not None

    with pytest.raises(IntegrityError):
        persist_extracted_pages(db_session, document=document, pages=pages)


def test_fake_ocr_provider_returns_predictable_result_without_external_provider():
    result = FakeOcrProvider().extract_text(
        content=b"BOLETIM DE OCORRENCIA OCR TESTE",
        content_type="image/png",
    )

    assert result.provider == "fake"
    assert result.confidence == 80
    assert result.text == "BOLETIM DE OCORRENCIA OCR TESTE"


def test_classifier_marks_boletim_occurrence_and_low_confidence_unknown():
    classifier = DocumentClassifierV1()

    classified = classifier.classify("BOLETIM DE OCORRENCIA DA POLICIA")
    unknown = classifier.classify("texto sem sinais suficientes")

    assert classified.document_family == "boletim_ocorrencia"
    assert classified.low_confidence is False
    assert "boletim" in classified.signals
    assert unknown.document_family == "unknown"
    assert unknown.low_confidence is True


def test_segmenter_creates_occurrences_with_classification_metadata(db_session):
    document = _create_document(db_session)
    text = "BOLETIM DE OCORRENCIA 1 fato A BOLETIM DE OCORRENCIA 2 fato B"
    classification = DocumentClassifierV1().classify(text)
    segments = OccurrenceSegmenterV1().segment(text)

    occurrences = persist_occurrences(
        db_session,
        document=document,
        segments=segments,
        classification=classification,
    )
    db_session.commit()

    assert len(occurrences) == 2
    assert occurrences[0].organization_id == document.organization_id
    assert occurrences[0].document_family == "boletim_ocorrencia"
    assert occurrences[0].metadata_json["signals"] == list(classification.signals)

    db_occurrences = db_session.execute(select(Occurrence)).scalars().all()
    assert len(db_occurrences) == 2


def test_occurrences_block_duplicate_sequence_for_same_document(db_session):
    document = _create_document(db_session)
    classification = DocumentClassifierV1().classify("BOLETIM DE OCORRENCIA")
    segment = OccurrenceSegmenterV1().segment("BOLETIM DE OCORRENCIA")

    persist_occurrences(
        db_session,
        document=document,
        segments=segment,
        classification=classification,
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        persist_occurrences(
            db_session,
            document=document,
            segments=segment,
            classification=classification,
        )


def test_document_page_model_does_not_store_authorization_or_tokens(db_session):
    document = _create_document(db_session)
    page = DocumentPage(
        organization_id=document.organization_id,
        document_id=document.id,
        page_number=1,
        extraction_method="ocr",
        text="BOLETIM DE OCORRENCIA",
        text_hash="c" * 64,
        confidence=80,
        status="extracted",
        metadata_json={"provider": "fake"},
    )
    db_session.add(page)
    db_session.commit()

    assert "authorization" not in page.metadata_json
    assert "token" not in page.metadata_json
