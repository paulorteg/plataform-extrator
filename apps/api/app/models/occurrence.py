from datetime import datetime
from typing import Any
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


class Occurrence(Base):
    __tablename__ = "occurrences"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "sequence_number",
            name="uq_occurrences_document_sequence",
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
    document_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("documents.id"),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    document_family: Mapped[str] = mapped_column(String(64), nullable=False)
    classification_confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="segmented")
    text_excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")
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
    document: Mapped["Document"] = relationship("Document", back_populates="occurrences")
