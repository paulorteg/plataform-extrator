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
from app.models.organization_package import OrganizationPackage
from app.models.package import Package
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.permissions.dependencies import AuthorizedPermissionContext, require_permission


router = APIRouter(tags=["billing"])


class PlanCreateRequest(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    monthly_analysis_limit: Optional[int] = Field(default=None, ge=0)
    allow_overage: bool = False
    status: str = Field(default="active", max_length=32)


class PlanResponse(BaseModel):
    id: str
    key: str
    name: str
    monthly_analysis_limit: Optional[int]
    allow_overage: bool
    status: str


class PackageCreateRequest(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    analysis_quota: int = Field(ge=0)
    plan_id: Optional[str] = None
    entitlements: dict = Field(default_factory=dict)
    status: str = Field(default="active", max_length=32)


class PackageResponse(BaseModel):
    id: str
    key: str
    name: str
    analysis_quota: int
    plan_id: Optional[str]
    entitlements: dict
    status: str


class SubscriptionCreateRequest(BaseModel):
    organization_id: str
    status: str = Field(default="active", max_length=32)


class SubscriptionResponse(BaseModel):
    id: str
    organization_id: str
    plan_id: str
    status: str


class PackageAssignmentRequest(BaseModel):
    organization_id: str
    assigned_analysis_quota: Optional[int] = Field(default=None, ge=0)
    status: str = Field(default="active", max_length=32)


class PackageAssignmentResponse(BaseModel):
    id: str
    organization_id: str
    package_id: str
    assigned_analysis_quota: int
    status: str


def _bad_request(code: str, message: str) -> AuthError:
    return AuthError(400, code, message)


def _not_found(code: str, message: str) -> AuthError:
    return AuthError(404, code, message)


def _conflict(code: str, message: str) -> AuthError:
    return AuthError(409, code, message)


def _plan_response(plan: Plan) -> PlanResponse:
    return PlanResponse(
        id=plan.id,
        key=plan.key,
        name=plan.name,
        monthly_analysis_limit=plan.monthly_analysis_limit,
        allow_overage=plan.allow_overage,
        status=plan.status,
    )


def _package_response(package: Package) -> PackageResponse:
    return PackageResponse(
        id=package.id,
        key=package.key,
        name=package.name,
        analysis_quota=package.analysis_quota,
        plan_id=package.plan_id,
        entitlements=package.entitlements,
        status=package.status,
    )


def _subscription_response(subscription: Subscription) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=subscription.id,
        organization_id=subscription.organization_id,
        plan_id=subscription.plan_id,
        status=subscription.status,
    )


def _assignment_response(assignment: OrganizationPackage) -> PackageAssignmentResponse:
    return PackageAssignmentResponse(
        id=assignment.id,
        organization_id=assignment.organization_id,
        package_id=assignment.package_id,
        assigned_analysis_quota=assignment.assigned_analysis_quota,
        status=assignment.status,
    )


def _ensure_platform_context(context: AuthorizedPermissionContext) -> None:
    role = context.current_organization.user_organization.role
    if role is None or role.scope != "platform":
        raise AuthError(403, "platform_access_required", "Platform access required.")


def _get_plan_or_404(db: Session, plan_id: str) -> Plan:
    plan = db.execute(select(Plan).where(Plan.id == plan_id)).scalar_one_or_none()
    if plan is None:
        raise _not_found("plan_not_found", "Plan not found.")
    return plan


def _get_package_or_404(db: Session, package_id: str) -> Package:
    package = db.execute(select(Package).where(Package.id == package_id)).scalar_one_or_none()
    if package is None:
        raise _not_found("package_not_found", "Package not found.")
    return package


def _ensure_organization_exists(db: Session, organization_id: str) -> None:
    organization = db.execute(
        select(Organization).where(Organization.id == organization_id)
    ).scalar_one_or_none()
    if organization is None:
        raise _not_found("organization_not_found", "Organization not found.")
    if organization.status != "active":
        raise _bad_request("organization_inactive", "Organization is inactive.")


@router.get("/plans", response_model=list[PlanResponse])
def list_plans(
    context: AuthorizedPermissionContext = Depends(require_permission("plan_manage")),
    db: Session = Depends(get_database_session),
):
    _ensure_platform_context(context)
    plans = db.execute(select(Plan).order_by(Plan.key)).scalars().all()
    return [_plan_response(plan) for plan in plans]


@router.post("/plans", response_model=PlanResponse, status_code=201)
def create_plan(
    payload: PlanCreateRequest,
    request: Request,
    context: AuthorizedPermissionContext = Depends(require_permission("plan_manage")),
    db: Session = Depends(get_database_session),
):
    _ensure_platform_context(context)
    existing_plan = db.execute(select(Plan).where(Plan.key == payload.key)).scalar_one_or_none()
    if existing_plan is not None:
        raise _conflict("plan_key_exists", "Plan key already exists.")

    plan = Plan(
        key=payload.key,
        name=payload.name,
        monthly_analysis_limit=payload.monthly_analysis_limit,
        allow_overage=payload.allow_overage,
        status=payload.status,
    )
    db.add(plan)
    db.flush()
    audit_log.record(
        db,
        "plan.created",
        organization_id=context.current_organization.organization_id,
        user_id=context.current_user.user.id,
        target_type="plan",
        target_id=plan.id,
        request_id=getattr(request.state, REQUEST_ID_STATE_KEY, None),
        metadata={"plan_key": plan.key, "status": plan.status},
    )
    db.commit()
    db.refresh(plan)
    return _plan_response(plan)


@router.post("/plans/{plan_id}/subscriptions", response_model=SubscriptionResponse, status_code=201)
def create_subscription(
    plan_id: str,
    payload: SubscriptionCreateRequest,
    request: Request,
    context: AuthorizedPermissionContext = Depends(require_permission("plan_manage")),
    db: Session = Depends(get_database_session),
):
    _ensure_platform_context(context)
    plan = _get_plan_or_404(db, plan_id)
    _ensure_organization_exists(db, payload.organization_id)
    active_subscription = db.execute(
        select(Subscription).where(
            Subscription.organization_id == payload.organization_id,
            Subscription.status == "active",
        )
    ).scalar_one_or_none()
    if active_subscription is not None:
        raise _conflict("active_subscription_exists", "Organization already has an active subscription.")

    subscription = Subscription(
        organization_id=payload.organization_id,
        plan_id=plan.id,
        status=payload.status,
    )
    db.add(subscription)
    db.flush()
    audit_log.record(
        db,
        "subscription.created",
        organization_id=payload.organization_id,
        user_id=context.current_user.user.id,
        target_type="subscription",
        target_id=subscription.id,
        request_id=getattr(request.state, REQUEST_ID_STATE_KEY, None),
        metadata={"plan_key": plan.key, "status": subscription.status},
    )
    db.commit()
    db.refresh(subscription)
    return _subscription_response(subscription)


@router.get("/packages", response_model=list[PackageResponse])
def list_packages(
    context: AuthorizedPermissionContext = Depends(require_permission("package_assign")),
    db: Session = Depends(get_database_session),
):
    _ensure_platform_context(context)
    packages = db.execute(select(Package).order_by(Package.key)).scalars().all()
    return [_package_response(package) for package in packages]


@router.post("/packages", response_model=PackageResponse, status_code=201)
def create_package(
    payload: PackageCreateRequest,
    request: Request,
    context: AuthorizedPermissionContext = Depends(require_permission("plan_manage")),
    db: Session = Depends(get_database_session),
):
    _ensure_platform_context(context)
    existing_package = db.execute(
        select(Package).where(Package.key == payload.key)
    ).scalar_one_or_none()
    if existing_package is not None:
        raise _conflict("package_key_exists", "Package key already exists.")
    if payload.plan_id is not None:
        _get_plan_or_404(db, payload.plan_id)

    package = Package(
        key=payload.key,
        name=payload.name,
        plan_id=payload.plan_id,
        analysis_quota=payload.analysis_quota,
        entitlements=payload.entitlements,
        status=payload.status,
    )
    db.add(package)
    db.flush()
    audit_log.record(
        db,
        "package.created",
        organization_id=context.current_organization.organization_id,
        user_id=context.current_user.user.id,
        target_type="package",
        target_id=package.id,
        request_id=getattr(request.state, REQUEST_ID_STATE_KEY, None),
        metadata={"package_key": package.key, "status": package.status},
    )
    db.commit()
    db.refresh(package)
    return _package_response(package)


@router.post(
    "/packages/{package_id}/assignments",
    response_model=PackageAssignmentResponse,
    status_code=201,
)
def assign_package(
    package_id: str,
    payload: PackageAssignmentRequest,
    request: Request,
    context: AuthorizedPermissionContext = Depends(require_permission("package_assign")),
    db: Session = Depends(get_database_session),
):
    _ensure_platform_context(context)
    package = _get_package_or_404(db, package_id)
    _ensure_organization_exists(db, payload.organization_id)
    quota = (
        package.analysis_quota
        if payload.assigned_analysis_quota is None
        else payload.assigned_analysis_quota
    )
    assignment = OrganizationPackage(
        organization_id=payload.organization_id,
        package_id=package.id,
        assigned_analysis_quota=quota,
        status=payload.status,
    )
    db.add(assignment)
    db.flush()
    audit_log.record(
        db,
        "package.assigned",
        organization_id=payload.organization_id,
        user_id=context.current_user.user.id,
        target_type="organization_package",
        target_id=assignment.id,
        request_id=getattr(request.state, REQUEST_ID_STATE_KEY, None),
        metadata={"package_key": package.key, "assigned_analysis_quota": quota},
    )
    db.commit()
    db.refresh(assignment)
    return _assignment_response(assignment)
