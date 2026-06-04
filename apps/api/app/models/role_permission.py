from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )

    id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    role_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("roles.id"),
        nullable=False,
    )
    permission_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("permissions.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    role: Mapped["Role"] = relationship("Role", back_populates="permission_links")
    permission: Mapped["Permission"] = relationship("Permission", back_populates="role_links")
