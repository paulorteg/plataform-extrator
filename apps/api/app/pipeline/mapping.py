import json
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.occurrence import Occurrence
from app.pipeline.canonical import build_canonical_model


MAPPING_PATH = Path(__file__).with_name("mapping_mercadoia_v1.json")


def load_mercadoia_mapping(path: Path = MAPPING_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as mapping_file:
        return json.load(mapping_file)


def _source_value(canonical_model: dict[str, Any], source: str) -> Optional[dict[str, Any]]:
    group_key, field_key = source.split(".", 1)
    return canonical_model.get("fields", {}).get(group_key, {}).get(field_key)


def apply_mercadoia_mapping(
    canonical_model: dict[str, Any],
    mapping: dict[str, Any],
) -> list[dict[str, Any]]:
    mapped_fields: list[dict[str, Any]] = []
    for item in mapping["fields"]:
        source = _source_value(canonical_model, item["source"])
        if source is None or not source.get("value"):
            mapped_fields.append(
                {
                    "template_field": item["template_field"],
                    "value": None,
                    "status": "nao_encontrado",
                    "source_status": "nao_encontrado",
                    "confidence": 0,
                    "evidence_id": None,
                    "validation_status": "missing_required" if item["required"] else "missing_optional",
                    "requires_review": bool(item["required"]),
                    "review_reason": "Campo obrigatorio ausente." if item["required"] else None,
                }
            )
            continue
        validation_status = "valid" if source["status"] != "invalido" else "invalid"
        mapped_fields.append(
            {
                "template_field": item["template_field"],
                "value": source["value"],
                "status": source["status"],
                "source_status": source["status"],
                "confidence": source["confidence"],
                "evidence_id": source["evidence_id"],
                "validation_status": validation_status,
                "requires_review": source["status"] != "extraido" or source["confidence"] < 70,
                "review_reason": None if validation_status == "valid" else "Campo invalido.",
            }
        )
    return mapped_fields


def persist_mercadoia_mapping(db: Session, occurrence: Occurrence) -> list[dict[str, Any]]:
    canonical_model = occurrence.metadata_json.get("canonical_model")
    if canonical_model is None:
        canonical_model = build_canonical_model(db, occurrence)
    mapped_fields = apply_mercadoia_mapping(canonical_model, load_mercadoia_mapping())
    metadata = dict(occurrence.metadata_json)
    metadata["mercadoia_mapping"] = {
        "version": "1.0",
        "fields": mapped_fields,
    }
    occurrence.metadata_json = metadata
    occurrence.status = "mapped"
    db.flush()
    return mapped_fields
