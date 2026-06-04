from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExtractedField(Base):
    __tablename__ = "extracted_fields"
    __table_args__ = (
        UniqueConstraint(
            "occurrence_id",
            "field_key",
            name="uq_extracted_fields_occurrence_field",
        ),
    )

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    organization_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("organizations.id"),
        nullable=False,
    )
    occurrence_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("occurrences.id"),
        nullable=False,
    )
    evidence_id: Mapped[Optional[str]] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("evidences.id"),
        nullable=True,
    )
    field_key: Mapped[str] = mapped_column(String(128), nullable=False)
    group_key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="extraido")
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    extraction_method: Mapped[str] = mapped_column(String(64), nullable=False, default="deterministic")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    organization: Mapped["Organization"] = relationship("Organization")
    occurrence: Mapped["Occurrence"] = relationship("Occurrence", back_populates="fields")
    evidence: Mapped[Optional["Evidence"]] = relationship("Evidence")
