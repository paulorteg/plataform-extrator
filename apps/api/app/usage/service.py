from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit_log.service import sanitize_metadata
from app.models.organization_package import OrganizationPackage
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.usage_event import UsageEvent


DEFAULT_USAGE_EVENT_TYPE = "occurrence_extracted"


class UsageLimitExceededError(Exception):
    pass


class UsageIdempotencyConflictError(Exception):
    pass


@dataclass(frozen=True)
class UsageBalance:
    organization_id: str
    plan_quota: int
    package_quota: int
    used: int
    available: int
    allow_overage: bool

    @property
    def total_quota(self) -> int:
        return self.plan_quota + self.package_quota

    @property
    def can_consume(self) -> bool:
        return self.allow_overage or self.available > 0


@dataclass(frozen=True)
class UsageRegistrationResult:
    event: UsageEvent
    created: bool
    balance: UsageBalance


def build_idempotency_key(
    organization_id: str,
    occurrence_id: str,
    event_type: str = DEFAULT_USAGE_EVENT_TYPE,
) -> str:
    return f"{organization_id}:{occurrence_id}:{event_type}"


def get_usage_balance(db: Session, organization_id: str) -> UsageBalance:
    plan_quota = (
        db.execute(
            select(func.coalesce(func.sum(Plan.monthly_analysis_limit), 0))
            .join(Subscription, Subscription.plan_id == Plan.id)
            .where(
                Subscription.organization_id == organization_id,
                Subscription.status == "active",
                Plan.status == "active",
                Plan.monthly_analysis_limit.is_not(None),
            )
        ).scalar_one()
        or 0
    )
    package_quota = (
        db.execute(
            select(func.coalesce(func.sum(OrganizationPackage.assigned_analysis_quota), 0))
            .where(
                OrganizationPackage.organization_id == organization_id,
                OrganizationPackage.status == "active",
            )
        ).scalar_one()
        or 0
    )
    used = (
        db.execute(
            select(func.coalesce(func.sum(UsageEvent.amount), 0)).where(
                UsageEvent.organization_id == organization_id
            )
        ).scalar_one()
        or 0
    )
    allow_overage = (
        db.execute(
            select(Plan.id)
            .join(Subscription, Subscription.plan_id == Plan.id)
            .where(
                Subscription.organization_id == organization_id,
                Subscription.status == "active",
                Plan.status == "active",
                Plan.allow_overage.is_(True),
            )
        ).first()
        is not None
    )
    total_quota = int(plan_quota) + int(package_quota)
    return UsageBalance(
        organization_id=organization_id,
        plan_quota=int(plan_quota),
        package_quota=int(package_quota),
        used=int(used),
        available=max(total_quota - int(used), 0),
        allow_overage=allow_overage,
    )


def check_usage_available(
    db: Session,
    organization_id: str,
    amount: int = 1,
) -> UsageBalance:
    balance = get_usage_balance(db, organization_id)
    if amount <= 0:
        raise ValueError("Usage amount must be positive.")
    if not balance.allow_overage and balance.available < amount:
        raise UsageLimitExceededError("Insufficient usage balance.")
    return balance


def register_occurrence_usage(
    db: Session,
    *,
    organization_id: str,
    occurrence_id: str,
    amount: int = 1,
    event_type: str = DEFAULT_USAGE_EVENT_TYPE,
    idempotency_key: Optional[str] = None,
    request_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> UsageRegistrationResult:
    if amount <= 0:
        raise ValueError("Usage amount must be positive.")

    normalized_idempotency_key = idempotency_key or build_idempotency_key(
        organization_id,
        occurrence_id,
        event_type,
    )
    existing_event = db.execute(
        select(UsageEvent).where(UsageEvent.idempotency_key == normalized_idempotency_key)
    ).scalar_one_or_none()
    if existing_event is not None:
        if existing_event.organization_id != organization_id:
            raise UsageIdempotencyConflictError("Idempotency key already exists.")
        return UsageRegistrationResult(
            event=existing_event,
            created=False,
            balance=get_usage_balance(db, organization_id),
        )

    existing_occurrence_event = db.execute(
        select(UsageEvent).where(
            UsageEvent.organization_id == organization_id,
            UsageEvent.occurrence_id == occurrence_id,
            UsageEvent.event_type == event_type,
        )
    ).scalar_one_or_none()
    if existing_occurrence_event is not None:
        return UsageRegistrationResult(
            event=existing_occurrence_event,
            created=False,
            balance=get_usage_balance(db, organization_id),
        )

    check_usage_available(db, organization_id, amount)
    event = UsageEvent(
        organization_id=organization_id,
        occurrence_id=occurrence_id,
        event_type=event_type,
        amount=amount,
        idempotency_key=normalized_idempotency_key,
        request_id=request_id,
        metadata_json=sanitize_metadata(metadata),
    )
    db.add(event)
    db.flush()
    return UsageRegistrationResult(
        event=event,
        created=True,
        balance=get_usage_balance(db, organization_id),
    )
