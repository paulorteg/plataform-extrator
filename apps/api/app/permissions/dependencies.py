from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, get_database_session
from app.auth.errors import AuthError
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.organizations.dependencies import (
    CurrentOrganizationContext,
    get_current_organization,
)


@dataclass(frozen=True)
class AuthorizedPermissionContext:
    current_user: CurrentUser
    current_organization: CurrentOrganizationContext
    permission_key: str


def _permission_denied() -> AuthError:
    return AuthError(
        403,
        "permission_denied",
        "Permission denied.",
    )


def _role_has_permission(
    db: Session,
    role_id: str,
    permission_key: str,
) -> bool:
    permission_id = db.execute(
        select(Permission.id)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .where(
            Role.id == role_id,
            Role.status == "active",
            Permission.key == permission_key,
            Permission.status == "active",
        )
    ).scalar_one_or_none()
    return permission_id is not None


def require_permission(permission_key: str):
    def dependency(
        current_user: CurrentUser = Depends(get_current_user),
        current_organization: CurrentOrganizationContext = Depends(
            get_current_organization
        ),
        db: Session = Depends(get_database_session),
    ) -> AuthorizedPermissionContext:
        role_id = current_organization.user_organization.role_id
        if role_id is None:
            raise _permission_denied()

        if not _role_has_permission(db, role_id, permission_key):
            raise _permission_denied()

        return AuthorizedPermissionContext(
            current_user=current_user,
            current_organization=current_organization,
            permission_key=permission_key,
        )

    return dependency
