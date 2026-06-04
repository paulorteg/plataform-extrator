from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit_log import service as audit_log
from app.auth.dependencies import get_database_session
from app.auth.errors import AuthError
from app.middleware.request_context import REQUEST_ID_STATE_KEY
from app.models.role import Role
from app.models.user import User
from app.models.user_organization import UserOrganization
from app.permissions.dependencies import AuthorizedPermissionContext, require_permission


router = APIRouter(prefix="/users", tags=["users"])


class UserInvitationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    name: str = Field(min_length=1, max_length=255)
    role_key: str = Field(min_length=1, max_length=64)


class UserRoleUpdateRequest(BaseModel):
    role_key: str = Field(min_length=1, max_length=64)


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    status: str
    organization_id: str
    organization_status: str
    role: Optional[dict[str, str]]


def _forbidden() -> AuthError:
    return AuthError(403, "user_access_denied", "User access denied.")


def _not_found() -> AuthError:
    return AuthError(404, "user_not_found", "User not found.")


def _role_not_found() -> AuthError:
    return AuthError(400, "role_not_found", "Role not found.")


def _user_response(link: UserOrganization) -> UserResponse:
    role = None
    if link.role is not None:
        role = {
            "id": link.role.id,
            "key": link.role.key,
            "scope": link.role.scope,
        }
    return UserResponse(
        id=link.user.id,
        name=link.user.name,
        email=link.user.email,
        status=link.user.status,
        organization_id=link.organization_id,
        organization_status=link.status,
        role=role,
    )


def _get_role_by_key(db: Session, role_key: str) -> Role:
    role = db.execute(
        select(Role).where(Role.key == role_key, Role.status == "active")
    ).scalar_one_or_none()
    if role is None:
        raise _role_not_found()
    return role


def _get_link_for_current_organization(
    db: Session,
    user_id: str,
    organization_id: str,
) -> UserOrganization:
    link = db.execute(
        select(UserOrganization).where(
            UserOrganization.user_id == user_id,
            UserOrganization.organization_id == organization_id,
        )
    ).scalar_one_or_none()
    if link is None:
        raise _forbidden()
    return link


@router.get("", response_model=list[UserResponse])
def list_users(
    context: AuthorizedPermissionContext = Depends(require_permission("user_invite")),
    db: Session = Depends(get_database_session),
):
    links = (
        db.execute(
            select(UserOrganization)
            .where(
                UserOrganization.organization_id
                == context.current_organization.organization_id
            )
            .order_by(UserOrganization.created_at, UserOrganization.id)
        )
        .unique()
        .scalars()
        .all()
    )
    return [_user_response(link) for link in links]


@router.post("/invitations", response_model=UserResponse, status_code=201)
def invite_user(
    payload: UserInvitationRequest,
    request: Request,
    context: AuthorizedPermissionContext = Depends(require_permission("user_invite")),
    db: Session = Depends(get_database_session),
):
    role = _get_role_by_key(db, payload.role_key)
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if user is None:
        user = User(
            auth_user_id=str(uuid4()),
            name=payload.name,
            email=payload.email,
            status="invited",
        )
        db.add(user)
        db.flush()

    existing_link = db.execute(
        select(UserOrganization).where(
            UserOrganization.user_id == user.id,
            UserOrganization.organization_id == context.current_organization.organization_id,
        )
    ).scalar_one_or_none()
    if existing_link is not None:
        raise AuthError(409, "user_already_linked", "User already linked.")

    link = UserOrganization(
        user_id=user.id,
        auth_user_id=user.auth_user_id,
        organization_id=context.current_organization.organization_id,
        role_id=role.id,
        role_key=role.key,
        status="invited",
    )
    db.add(link)
    db.flush()
    audit_log.record(
        db,
        "user.invited",
        organization_id=context.current_organization.organization_id,
        user_id=context.current_user.user.id,
        target_type="user",
        target_id=user.id,
        request_id=getattr(request.state, REQUEST_ID_STATE_KEY, None),
        metadata={"invited_user_id": user.id, "role_key": role.key},
    )
    db.commit()
    db.refresh(link)
    return _user_response(link)


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: str,
    payload: UserRoleUpdateRequest,
    request: Request,
    context: AuthorizedPermissionContext = Depends(require_permission("user_role_change")),
    db: Session = Depends(get_database_session),
):
    role = _get_role_by_key(db, payload.role_key)
    link = _get_link_for_current_organization(
        db,
        user_id,
        context.current_organization.organization_id,
    )
    old_role_key = link.role_key
    link.role_id = role.id
    link.role_key = role.key
    audit_log.record(
        db,
        "user.role_changed",
        organization_id=context.current_organization.organization_id,
        user_id=context.current_user.user.id,
        target_type="user",
        target_id=user_id,
        request_id=getattr(request.state, REQUEST_ID_STATE_KEY, None),
        metadata={"old_role_key": old_role_key, "new_role_key": role.key},
    )
    db.commit()
    db.refresh(link)
    return _user_response(link)


@router.post("/{user_id}/block", response_model=UserResponse)
def block_user(
    user_id: str,
    request: Request,
    context: AuthorizedPermissionContext = Depends(require_permission("user_role_change")),
    db: Session = Depends(get_database_session),
):
    link = _get_link_for_current_organization(
        db,
        user_id,
        context.current_organization.organization_id,
    )
    link.status = "blocked"
    audit_log.record(
        db,
        "user.blocked",
        organization_id=context.current_organization.organization_id,
        user_id=context.current_user.user.id,
        target_type="user",
        target_id=user_id,
        request_id=getattr(request.state, REQUEST_ID_STATE_KEY, None),
        metadata={"blocked_user_id": user_id},
    )
    db.commit()
    db.refresh(link)
    return _user_response(link)
