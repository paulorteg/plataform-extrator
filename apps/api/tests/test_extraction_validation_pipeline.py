from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import (
    Document,
    DocumentPage,
    Evidence,
    ExtractedField,
    Occurrence,
    Organization,
    Plan,
    ProcessingJob,
    Subscription,
    UsageEvent,
    User,
    ValidationIssue,
)
from app.pipeline.canonical import build_canonical_model, persist_canonical_model
from app.pipeline.field_extraction import DeterministicFieldExtractorV1, extract_and_persist_fields
from app.pipeline.mapping import apply_mercadoia_mapping, load_mercadoia_mapping, persist_mercadoia_mapping
from app.pipeline.sections import SectionDetectorV1
from app.pipeline.validation import validate_occurrence_fields
from app.queue.service import (
    JOB_TYPE_APPLY_MAPPING,
    JOB_TYPE_BUILD_CANONICAL_MODEL,
    JOB_TYPE_DETECT_SECTIONS,
    JOB_TYPE_EXTRACT_FIELDS,
    JOB_TYPE_REGISTER_USAGE,
    JOB_TYPE_VALIDATE_FIELDS,
    process_next_fake_job,
)


SAMPLE_TEXT = """
BOLETIM N 2026-0001
Tipo Sinistro: Roubo
Data Evento: 01/06/2026
Cidade Evento: Campinas
UF Evento: SP
Evento: Subtracao de carga
Mercadoria: Eletronicos
Data Embarque: 31/05/2026
Motorista CPF 123.456.789-00
Vitima CNPJ 12.345.678/0001-90
Veiculo placa ABC1D23
Cidade Emplacamento: Santos
UF Emplacamento: SP
""".strip()


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


def _create_occurrence(session: Session, *, text: str = SAMPLE_TEXT) -> Occurrence:
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
        size_bytes=len(text),
        sha256_hash="a" * 64,
        storage_bucket="documents",
        storage_path=f"organizations/{organization.id}/documents/{uuid4()}/original",
        storage_uri=f"supabase://documents/organizations/{organization.id}/documents/{uuid4()}/original",
        status="segmented",
        metadata_json={},
    )
    session.add(document)
    session.flush()
    session.add(
        DocumentPage(
            organization_id=organization.id,
            document_id=document.id,
            page_number=1,
            extraction_method="digital",
            text=text,
            text_hash="b" * 64,
            confidence=100,
            status="extracted",
            metadata_json={},
        )
    )
    occurrence = Occurrence(
        organization_id=organization.id,
        document_id=document.id,
        sequence_number=1,
        document_family="boletim_ocorrencia",
        classification_confidence=90,
        status="segmented",
        text_excerpt=text[:1024],
        metadata_json={},
    )
    session.add(occurrence)
    session.commit()
    session.refresh(occurrence)
    return occurrence


def _enqueue(session: Session, *, occurrence: Occurrence, job_type: str) -> ProcessingJob:
    job = ProcessingJob(
        organization_id=occurrence.organization_id,
        document_id=occurrence.document_id,
        job_type=job_type,
        status="pending",
        priority=10,
        attempts=0,
        max_attempts=3,
        metadata_json={"occurrence_id": occurrence.id},
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def _create_usage_quota(session: Session, organization_id: str) -> None:
    plan = Plan(
        key=f"plan_{uuid4()}",
        name="Plano Teste",
        status="active",
        monthly_analysis_limit=10,
        allow_overage=False,
    )
    session.add(plan)
    session.flush()
    session.add(
        Subscription(
            organization_id=organization_id,
            plan_id=plan.id,
            status="active",
        )
    )
    session.commit()


def test_section_detector_marks_expected_sections():
    sections = SectionDetectorV1().detect(SAMPLE_TEXT)

    assert sections["boletim"] is True
    assert sections["motorista"] is True
    assert sections["veiculo"] is True
    assert sections["carga"] is True
    assert sections["empresa"] is True


def test_deterministic_extractor_finds_formal_and_labeled_fields():
    matches = DeterministicFieldExtractorV1().extract(SAMPLE_TEXT)
    values_by_key = {match.field_key: match.value for match in matches}

    assert values_by_key["cnpj_vitima"] == "12.345.678/0001-90"
    assert values_by_key["cpf_motorista"] == "123.456.789-00"
    assert values_by_key["placa_veiculo_sinistrado"].upper() == "ABC1D23"
    assert values_by_key["tipo_sinistro"] == "Roubo"
    assert values_by_key["uf_evento"] == "SP"


def test_extract_and_persist_fields_creates_evidence_with_organization_id(db_session):
    occurrence = _create_occurrence(db_session)

    fields = extract_and_persist_fields(db_session, occurrence)
    db_session.commit()

    assert len(fields) >= 8
    field = db_session.execute(
        select(ExtractedField).where(ExtractedField.field_key == "cnpj_vitima")
    ).scalar_one()
    evidence = db_session.get(Evidence, field.evidence_id)

    assert field.organization_id == occurrence.organization_id
    assert evidence.organization_id == occurrence.organization_id
    assert evidence.text_excerpt
    assert "authorization" not in evidence.metadata_json
    assert "token" not in evidence.metadata_json


def test_extracted_fields_block_duplicate_field_per_occurrence(db_session):
    occurrence = _create_occurrence(db_session)
    extract_and_persist_fields(db_session, occurrence)
    db_session.commit()

    with pytest.raises(IntegrityError):
        extract_and_persist_fields(db_session, occurrence)


def test_validate_occurrence_fields_creates_missing_required_issues(db_session):
    occurrence = _create_occurrence(db_session, text="BOLETIM N 1 CPF 123.456.789-00")
    extract_and_persist_fields(db_session, occurrence)
    db_session.commit()

    issues = validate_occurrence_fields(db_session, occurrence)
    db_session.commit()

    issue_types = {issue.issue_type for issue in issues}
    assert "required_missing" in issue_types
    assert all(issue.organization_id == occurrence.organization_id for issue in issues)


def test_canonical_model_contains_fields_evidences_and_validation(db_session):
    occurrence = _create_occurrence(db_session)
    extract_and_persist_fields(db_session, occurrence)
    validate_occurrence_fields(db_session, occurrence)
    db_session.commit()

    canonical = build_canonical_model(db_session, occurrence)

    assert canonical["schema_version"] == "1.0"
    assert canonical["occurrence"]["id"] == occurrence.id
    assert canonical["fields"]["dados_sinistro"]["cnpj_vitima"]["evidence_id"]
    assert canonical["evidences"]
    assert canonical["validation"] == []


def test_mapping_loader_and_application_generate_review_for_missing_required():
    mapping = load_mercadoia_mapping()
    canonical = {
        "fields": {
            "dados_sinistro": {
                "cnpj_vitima": {
                    "value": "12.345.678/0001-90",
                    "status": "extraido",
                    "confidence": 95,
                    "evidence_id": "evidence-id",
                }
            }
        }
    }

    mapped = apply_mercadoia_mapping(canonical, mapping)
    mapped_by_template = {item["template_field"]: item for item in mapped}

    assert mapped_by_template["CNPJ Vitima"]["value"] == "12.345.678/0001-90"
    assert mapped_by_template["Tipo Sinistro"]["requires_review"] is True
    assert mapped_by_template["Tipo Sinistro"]["validation_status"] == "missing_required"


def test_jobs_run_sections_fields_validation_canonical_mapping_and_usage(db_session):
    occurrence = _create_occurrence(db_session)
    _create_usage_quota(db_session, occurrence.organization_id)

    for job_type in (
        JOB_TYPE_DETECT_SECTIONS,
        JOB_TYPE_EXTRACT_FIELDS,
        JOB_TYPE_VALIDATE_FIELDS,
        JOB_TYPE_BUILD_CANONICAL_MODEL,
        JOB_TYPE_APPLY_MAPPING,
        JOB_TYPE_REGISTER_USAGE,
    ):
        _enqueue(db_session, occurrence=occurrence, job_type=job_type)
        processed = process_next_fake_job(db_session)
        assert processed.status == "completed"
        db_session.commit()

    db_session.refresh(occurrence)
    usage_event = db_session.execute(select(UsageEvent)).scalar_one()

    assert occurrence.status == "usage_registered"
    assert occurrence.metadata_json["sections"]["boletim"] is True
    assert occurrence.metadata_json["canonical_model"]["schema_version"] == "1.0"
    assert occurrence.metadata_json["mercadoia_mapping"]["fields"]
    assert usage_event.organization_id == occurrence.organization_id
    assert usage_event.occurrence_id == occurrence.id


def test_persist_canonical_and_mapping_update_occurrence_metadata(db_session):
    occurrence = _create_occurrence(db_session)
    extract_and_persist_fields(db_session, occurrence)
    validate_occurrence_fields(db_session, occurrence)
    persist_canonical_model(db_session, occurrence)
    persist_mercadoia_mapping(db_session, occurrence)
    db_session.commit()
    db_session.refresh(occurrence)

    assert occurrence.status == "mapped"
    assert "canonical_model" in occurrence.metadata_json
    assert "mercadoia_mapping" in occurrence.metadata_json
