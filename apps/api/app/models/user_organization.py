from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, String, Uuid
from sqlalchemy import UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserOrganization(Base):
    __tablename__ = "user_organizations"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_user_organizations_user_org"),
        ForeignKeyConstraint(
            ["user_id", "auth_user_id"],
            ["users.id", "users.auth_user_id"],
            name="fk_user_organizations_user_auth_pair",
        ),
    )

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    auth_user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    organization_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("organizations.id"),
        nullable=False,
    )
    role_id: Mapped[Optional[str]] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("roles.id"),
        nullable=True,
    )
    role_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
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

    user: Mapped["User"] = relationship(
        "User",
        back_populates="organization_links",
    )
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="user_links",
    )
    role: Mapped[Optional["Role"]] = relationship(
        "Role",
        back_populates="user_organization_links",
    )
