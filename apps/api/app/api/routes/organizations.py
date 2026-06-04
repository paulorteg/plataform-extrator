from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit_log import service as audit_log
from app.auth.dependencies import get_database_session
from app.auth.errors import AuthError
from app.middleware.request_context import REQUEST_ID_STATE_KEY
from app.models.organization import Organization
from app.organizations.dependencies import CurrentOrganizationContext
from app.permissions.dependencies import AuthorizedPermissionContext, require_permission


router = APIRouter(prefix="/organizations", tags=["organizations"])


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    legal_name: Optional[str] = Field(default=None, max_length=255)
    cnpj_hash: Optional[str] = Field(default=None, max_length=128)
    status: str = Field(default="active", max_length=32)
    retention_days: int = Field(default=180, ge=1, le=3650)


class OrganizationUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    legal_name: Optional[str] = Field(default=None, max_length=255)
    status: Optional[str] = Field(default=None, max_length=32)
    retention_days: Optional[int] = Field(default=None, ge=1, le=3650)


class OrganizationResponse(BaseModel):
    id: str
    name: str
    legal_name: Optional[str]
    status: str
    retention_days: int


def _organization_response(organization: Organization) -> OrganizationResponse:
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        legal_name=organization.legal_name,
        status=organization.status,
        retention_days=organization.retention_days,
    )


def _is_platform_context(context: AuthorizedPermissionContext) -> bool:
    role = context.current_organization.user_organization.role
    return role is not None and role.scope == "platform"


def _forbidden() -> AuthError:
    return AuthError(403, "organization_access_denied", "Organization access denied.")


def _not_found() -> AuthError:
    return AuthError(404, "organization_not_found", "Organization not found.")


def _ensure_platform_context(context: AuthorizedPermissionContext) -> None:
    if not _is_platform_context(context):
        raise _forbidden()


def _ensure_organization_access(
    organization_id: str,
    context: AuthorizedPermissionContext,
) -> None:
    if _is_platform_context(context):
        return
    if organization_id != context.current_organization.organization_id:
        raise _forbidden()


def _get_organization_or_404(db: Session, organization_id: str) -> Organization:
    organization = db.execute(
        select(Organization).where(Organization.id == organization_id)
    ).scalar_one_or_none()
    if organization is None:
        raise _not_found()
    return organization


@router.get("", response_model=list[OrganizationResponse])
def list_organizations(
    context: AuthorizedPermissionContext = Depends(require_permission("organization_view")),
    db: Session = Depends(get_database_session),
):
    if _is_platform_context(context):
        organizations = db.execute(select(Organization).order_by(Organization.name)).scalars().all()
    else:
        organizations = [
            context.current_organization.organization,
        ]
    return [_organization_response(organization) for organization in organizations]


@router.post("", response_model=OrganizationResponse, status_code=201)
def create_organization(
    payload: OrganizationCreateRequest,
    request: Request,
    context: AuthorizedPermissionContext = Depends(require_permission("organization_view")),
    db: Session = Depends(get_database_session),
):
    _ensure_platform_context(context)

    organization = Organization(
        name=payload.name,
        legal_name=payload.legal_name,
        cnpj_hash=payload.cnpj_hash,
        status=payload.status,
        retention_days=payload.retention_days,
    )
    db.add(organization)
    db.flush()
    audit_log.record(
        db,
        "organization.created",
        organization_id=organization.id,
        user_id=context.current_user.user.id,
        target_type="organization",
        target_id=organization.id,
        request_id=getattr(request.state, REQUEST_ID_STATE_KEY, None),
        metadata={"name": organization.name, "status": organization.status},
    )
    db.commit()
    db.refresh(organization)
    return _organization_response(organization)


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: str,
    context: AuthorizedPermissionContext = Depends(require_permission("organization_view")),
    db: Session = Depends(get_database_session),
):
    _ensure_organization_access(organization_id, context)
    return _organization_response(_get_organization_or_404(db, organization_id))


@router.patch("/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    organization_id: str,
    payload: OrganizationUpdateRequest,
    request: Request,
    context: AuthorizedPermissionContext = Depends(require_permission("organization_view")),
    db: Session = Depends(get_database_session),
):
    _ensure_organization_access(organization_id, context)
    organization = _get_organization_or_404(db, organization_id)

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(organization, field, value)

    audit_log.record(
        db,
        "organization.updated",
        organization_id=organization.id,
        user_id=context.current_user.user.id,
        target_type="organization",
        target_id=organization.id,
        request_id=getattr(request.state, REQUEST_ID_STATE_KEY, None),
        metadata={"changed_fields": sorted(changes)},
    )
    db.commit()
    db.refresh(organization)
    return _organization_response(organization)
