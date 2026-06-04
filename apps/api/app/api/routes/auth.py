from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import CurrentUser, get_current_user
from app.auth.dependencies import get_database_session
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user_organization import UserOrganization

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def get_auth_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_database_session),
):
    links = db.execute(
        select(UserOrganization)
        .join(Organization, UserOrganization.organization_id == Organization.id)
        .options(
            joinedload(UserOrganization.organization),
            joinedload(UserOrganization.role)
            .joinedload(Role.permission_links)
            .joinedload(RolePermission.permission),
        )
        .where(UserOrganization.user_id == current_user.user.id)
        .where(UserOrganization.status == "active")
        .where(Organization.status == "active")
    ).unique().scalars().all()

    organizations = []
    for link in links:
        role = link.role
        permission_keys = []
        if role is not None:
            permission_keys = sorted(
                role_permission.permission.key
                for role_permission in role.permission_links
                if role_permission.permission.status == "active"
            )

        organizations.append(
            {
                "id": link.organization.id,
                "name": link.organization.name,
                "role": {
                    "id": role.id,
                    "key": role.key,
                    "scope": role.scope,
                }
                if role is not None
                else None,
                "permissions": permission_keys,
            }
        )

    return {
        "user": {
            "id": current_user.user.id,
            "auth_user_id": current_user.user.auth_user_id,
            "name": current_user.user.name,
            "email": current_user.user.email,
            "status": current_user.user.status,
        },
        "organizations": organizations,
    }
