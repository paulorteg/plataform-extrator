from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_database_session
from app.models.usage_event import UsageEvent
from app.permissions.dependencies import AuthorizedPermissionContext, require_permission
from app.usage.service import (
    UsageLimitExceededError,
    check_usage_available,
    get_usage_balance,
)


router = APIRouter(prefix="/usage", tags=["usage"])


class UsageBalanceResponse(BaseModel):
    organization_id: str
    plan_quota: int
    package_quota: int
    total_quota: int
    used: int
    available: int
    allow_overage: bool
    can_consume: bool


class UsageEventResponse(BaseModel):
    id: str
    organization_id: str
    occurrence_id: str
    event_type: str
    amount: int
    request_id: Optional[str]
    created_at: datetime


class UsageAvailabilityResponse(BaseModel):
    organization_id: str
    amount: int
    available: bool
    balance: UsageBalanceResponse


def _balance_response(balance) -> UsageBalanceResponse:
    return UsageBalanceResponse(
        organization_id=balance.organization_id,
        plan_quota=balance.plan_quota,
        package_quota=balance.package_quota,
        total_quota=balance.total_quota,
        used=balance.used,
        available=balance.available,
        allow_overage=balance.allow_overage,
        can_consume=balance.can_consume,
    )


def _usage_event_response(event: UsageEvent) -> UsageEventResponse:
    return UsageEventResponse(
        id=event.id,
        organization_id=event.organization_id,
        occurrence_id=event.occurrence_id,
        event_type=event.event_type,
        amount=event.amount,
        request_id=event.request_id,
        created_at=event.created_at,
    )


@router.get("/balance", response_model=UsageBalanceResponse)
def get_balance(
    context: AuthorizedPermissionContext = Depends(require_permission("usage_view")),
    db: Session = Depends(get_database_session),
):
    balance = get_usage_balance(db, context.current_organization.organization_id)
    return _balance_response(balance)


@router.get("/events", response_model=list[UsageEventResponse])
def list_usage_events(
    context: AuthorizedPermissionContext = Depends(require_permission("usage_view")),
    db: Session = Depends(get_database_session),
):
    events = (
        db.execute(
            select(UsageEvent)
            .where(UsageEvent.organization_id == context.current_organization.organization_id)
            .order_by(UsageEvent.created_at, UsageEvent.id)
        )
        .scalars()
        .all()
    )
    return [_usage_event_response(event) for event in events]


@router.get("/availability", response_model=UsageAvailabilityResponse)
def check_availability(
    amount: int = 1,
    context: AuthorizedPermissionContext = Depends(require_permission("usage_view")),
    db: Session = Depends(get_database_session),
):
    try:
        balance = check_usage_available(
            db,
            context.current_organization.organization_id,
            amount,
        )
        available = True
    except UsageLimitExceededError:
        balance = get_usage_balance(db, context.current_organization.organization_id)
        available = False

    return UsageAvailabilityResponse(
        organization_id=context.current_organization.organization_id,
        amount=amount,
        available=available,
        balance=_balance_response(balance),
    )
