from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Evidence(Base):
    __tablename__ = "evidences"

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
    document_page_id: Mapped[Optional[str]] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("document_pages.id"),
        nullable=True,
    )
    field_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="text")
    text_excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    start_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
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

    organization: Mapped["Organization"] = relationship("Organization")
    occurrence: Mapped["Occurrence"] = relationship("Occurrence", back_populates="evidences")
    document_page: Mapped[Optional["DocumentPage"]] = relationship("DocumentPage")
