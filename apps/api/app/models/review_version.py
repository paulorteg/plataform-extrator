from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ReviewVersion(Base):
    __tablename__ = "review_versions"
    __table_args__ = (
        UniqueConstraint(
            "occurrence_id",
            "version",
            name="uq_review_versions_occurrence_version",
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
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    approved_by_user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("users.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="approved")
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(
        "snapshot",
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
    occurrence: Mapped["Occurrence"] = relationship("Occurrence", back_populates="review_versions")
    approved_by: Mapped["User"] = relationship("User")
