from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cnpj_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=180)
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

    user_links: Mapped[list["UserOrganization"]] = relationship(
        "UserOrganization",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
