from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("auth_user_id", name="uq_users_auth_user_id"),
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("id", "auth_user_id", name="uq_users_id_auth_user_id"),
    )

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    auth_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
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

    organization_links: Mapped[list["UserOrganization"]] = relationship(
        "UserOrganization",
        back_populates="user",
        cascade="all, delete-orphan",
    )
