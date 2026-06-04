from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Package(Base):
    __tablename__ = "packages"
    __table_args__ = (UniqueConstraint("key", name="uq_packages_key"),)

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_id: Mapped[Optional[str]] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("plans.id"),
        nullable=True,
    )
    analysis_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entitlements: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
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

    plan: Mapped[Optional["Plan"]] = relationship("Plan", back_populates="packages")
    organization_packages: Mapped[list["OrganizationPackage"]] = relationship(
        "OrganizationPackage",
        back_populates="package",
    )
