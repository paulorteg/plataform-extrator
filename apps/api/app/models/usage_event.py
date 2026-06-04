from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UsageEvent(Base):
    __tablename__ = "usage_events"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_usage_events_idempotency_key"),
        UniqueConstraint(
            "organization_id",
            "occurrence_id",
            "event_type",
            name="uq_usage_events_organization_occurrence_type",
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
    occurrence_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
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
