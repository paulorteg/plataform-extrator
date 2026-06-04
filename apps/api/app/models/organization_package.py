from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrganizationPackage(Base):
    __tablename__ = "organization_packages"

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
    package_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("packages.id"),
        nullable=False,
    )
    assigned_analysis_quota: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    starts_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
    package: Mapped["Package"] = relationship(
        "Package",
        back_populates="organization_packages",
    )
