from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (UniqueConstraint("key", name="uq_plans_key"),)

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    monthly_analysis_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    allow_overage: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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

    packages: Mapped[list["Package"]] = relationship("Package", back_populates="plan")
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription",
        back_populates="plan",
    )
