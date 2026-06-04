from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, get_database_session
from app.auth.errors import AuthError
from app.models.organization import Organization
from app.models.user_organization import UserOrganization


ORGANIZATION_ID_HEADER = "X-Organization-Id"


@dataclass(frozen=True)
class CurrentOrganizationContext:
    organization: Organization
    user_organization: UserOrganization
    organization_id: str


def _parse_organization_id(header_value: Optional[str]) -> str:
    if header_value is None or not header_value.strip():
        raise AuthError(
            400,
            "missing_organization",
            "Organization header is required.",
        )

    try:
        return str(UUID(header_value.strip()))
    except ValueError as exc:
        raise AuthError(
            400,
            "invalid_organization",
            "Organization header must be a valid UUID.",
        ) from exc


def _organization_not_allowed() -> AuthError:
    return AuthError(
        403,
        "organization_not_allowed",
        "Organization is not allowed.",
    )


def get_current_organization(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_database_session),
) -> CurrentOrganizationContext:
    organization_id = _parse_organization_id(request.headers.get(ORGANIZATION_ID_HEADER))

    organization = db.execute(
        select(Organization).where(Organization.id == organization_id)
    ).scalar_one_or_none()
    if organization is None or organization.status != "active":
        raise _organization_not_allowed()

    user_organization = db.execute(
        select(UserOrganization).where(
            UserOrganization.user_id == current_user.user.id,
            UserOrganization.auth_user_id == current_user.auth_user_id,
            UserOrganization.organization_id == organization_id,
            UserOrganization.status == "active",
        )
    ).scalar_one_or_none()
    if user_organization is None:
        raise _organization_not_allowed()

    context = CurrentOrganizationContext(
        organization=organization,
        user_organization=user_organization,
        organization_id=organization_id,
    )
    request.state.organization_id = organization_id
    request.state.current_organization = context
    request.state.user_organization = user_organization
    return context
