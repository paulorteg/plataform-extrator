"""Import all SQLAlchemy models so metadata is registered."""

from app.models.organization import Organization
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_organization import UserOrganization

__all__ = [
    "Organization",
    "Permission",
    "Role",
    "RolePermission",
    "User",
    "UserOrganization",
]
