from dataclasses import dataclass
from os import getenv

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Organization,
    OrganizationPackage,
    Package,
    Plan,
    Role,
    Subscription,
    User,
    UserOrganization,
)
from app.seeds.roles_permissions import seed_roles_permissions


REQUIRED_MVP_PERMISSION_KEYS = frozenset(
    {
        "auth_login",
        "organization_view",
        "usage_view",
        "document_upload",
        "document_view",
        "document_download",
        "occurrence_list",
        "occurrence_view",
        "review_field_edit",
        "review_field_approve",
        "review_approve_occurrence",
        "template_generate",
        "template_download",
        "audit_view",
    }
)


@dataclass(frozen=True)
class MvpTestSeedConfig:
    auth_user_id: str
    user_email: str = "mvp.tester@example.test"
    user_name: str = "MVP Tester"
    organization_name: str = "MercadoIA MVP Test Organization"
    organization_legal_name: str = "MercadoIA MVP Test Organization LTDA"
    organization_cnpj_hash: str = "mvp_test_cnpj_hash_not_real"
    role_key: str = "organization_admin"
    plan_key: str = "mvp_test"
    plan_name: str = "MVP Test Plan"
    monthly_analysis_limit: int = 100
    package_key: str = "mvp_test_package"
    package_name: str = "MVP Test Package"
    package_analysis_quota: int = 100


@dataclass(frozen=True)
class MvpTestSeedResult:
    organization_id: str
    user_id: str
    auth_user_id: str
    user_organization_id: str
    role_key: str
    plan_id: str
    package_id: str
    subscription_id: str
    organization_package_id: str


def config_from_env() -> MvpTestSeedConfig:
    auth_user_id = getenv("MERCADOIA_MVP_AUTH_USER_ID")
    if not auth_user_id:
        raise RuntimeError("Missing required environment variable: MERCADOIA_MVP_AUTH_USER_ID")

    default_user_email = f"mvp.{auth_user_id}@example.test"

    return MvpTestSeedConfig(
        auth_user_id=auth_user_id,
        user_email=getenv("MERCADOIA_MVP_USER_EMAIL", default_user_email),
        user_name=getenv("MERCADOIA_MVP_USER_NAME", MvpTestSeedConfig.user_name),
        organization_name=getenv(
            "MERCADOIA_MVP_ORGANIZATION_NAME",
            MvpTestSeedConfig.organization_name,
        ),
        organization_legal_name=getenv(
            "MERCADOIA_MVP_ORGANIZATION_LEGAL_NAME",
            MvpTestSeedConfig.organization_legal_name,
        ),
        organization_cnpj_hash=getenv(
            "MERCADOIA_MVP_ORGANIZATION_CNPJ_HASH",
            MvpTestSeedConfig.organization_cnpj_hash,
        ),
        role_key=getenv("MERCADOIA_MVP_ROLE_KEY", MvpTestSeedConfig.role_key),
        plan_key=getenv("MERCADOIA_MVP_PLAN_KEY", MvpTestSeedConfig.plan_key),
        plan_name=getenv("MERCADOIA_MVP_PLAN_NAME", MvpTestSeedConfig.plan_name),
        monthly_analysis_limit=int(
            getenv(
                "MERCADOIA_MVP_MONTHLY_ANALYSIS_LIMIT",
                str(MvpTestSeedConfig.monthly_analysis_limit),
            )
        ),
        package_key=getenv("MERCADOIA_MVP_PACKAGE_KEY", MvpTestSeedConfig.package_key),
        package_name=getenv("MERCADOIA_MVP_PACKAGE_NAME", MvpTestSeedConfig.package_name),
        package_analysis_quota=int(
            getenv(
                "MERCADOIA_MVP_PACKAGE_ANALYSIS_QUOTA",
                str(MvpTestSeedConfig.package_analysis_quota),
            )
        ),
    )


def seed_mvp_test_environment(session: Session, config: MvpTestSeedConfig) -> MvpTestSeedResult:
    seed_roles_permissions(session.connection())

    role = session.execute(select(Role).where(Role.key == config.role_key)).scalar_one_or_none()
    if role is None or role.status != "active":
        raise RuntimeError(f"Active role not found for MVP test seed: {config.role_key}")

    missing_permissions = REQUIRED_MVP_PERMISSION_KEYS.difference(
        {link.permission.key for link in role.permission_links if link.permission.status == "active"}
    )
    if missing_permissions:
        missing = ", ".join(sorted(missing_permissions))
        raise RuntimeError(f"Role {config.role_key} is missing MVP permissions: {missing}")

    organization = session.execute(
        select(Organization).where(Organization.cnpj_hash == config.organization_cnpj_hash)
    ).scalar_one_or_none()
    if organization is None:
        organization = Organization(
            name=config.organization_name,
            legal_name=config.organization_legal_name,
            cnpj_hash=config.organization_cnpj_hash,
            status="active",
            retention_days=180,
        )
        session.add(organization)
        session.flush()
    else:
        organization.name = config.organization_name
        organization.legal_name = config.organization_legal_name
        organization.status = "active"

    user = session.execute(
        select(User).where(User.auth_user_id == config.auth_user_id)
    ).scalar_one_or_none()
    if user is None:
        user = User(
            auth_user_id=config.auth_user_id,
            name=config.user_name,
            email=config.user_email,
            status="active",
        )
        session.add(user)
        session.flush()
    else:
        user.name = config.user_name
        user.email = config.user_email
        user.status = "active"

    user_organization = session.execute(
        select(UserOrganization).where(
            UserOrganization.user_id == user.id,
            UserOrganization.organization_id == organization.id,
        )
    ).scalar_one_or_none()
    if user_organization is None:
        user_organization = UserOrganization(
            user_id=user.id,
            auth_user_id=user.auth_user_id,
            organization_id=organization.id,
            role_id=role.id,
            role_key=role.key,
            status="active",
        )
        session.add(user_organization)
        session.flush()
    else:
        user_organization.auth_user_id = user.auth_user_id
        user_organization.role_id = role.id
        user_organization.role_key = role.key
        user_organization.status = "active"

    plan = session.execute(select(Plan).where(Plan.key == config.plan_key)).scalar_one_or_none()
    if plan is None:
        plan = Plan(
            key=config.plan_key,
            name=config.plan_name,
            status="active",
            monthly_analysis_limit=config.monthly_analysis_limit,
            allow_overage=False,
        )
        session.add(plan)
        session.flush()
    else:
        plan.name = config.plan_name
        plan.status = "active"
        plan.monthly_analysis_limit = config.monthly_analysis_limit
        plan.allow_overage = False

    package = session.execute(
        select(Package).where(Package.key == config.package_key)
    ).scalar_one_or_none()
    if package is None:
        package = Package(
            key=config.package_key,
            name=config.package_name,
            plan_id=plan.id,
            analysis_quota=config.package_analysis_quota,
            entitlements={
                "document_upload": True,
                "document_processing": True,
                "occurrence_review": True,
                "template_generate": True,
            },
            status="active",
        )
        session.add(package)
        session.flush()
    else:
        package.name = config.package_name
        package.plan_id = plan.id
        package.analysis_quota = config.package_analysis_quota
        package.entitlements = {
            "document_upload": True,
            "document_processing": True,
            "occurrence_review": True,
            "template_generate": True,
        }
        package.status = "active"

    subscription = session.execute(
        select(Subscription).where(
            Subscription.organization_id == organization.id,
            Subscription.plan_id == plan.id,
        )
    ).scalar_one_or_none()
    if subscription is None:
        subscription = Subscription(
            organization_id=organization.id,
            plan_id=plan.id,
            status="active",
        )
        session.add(subscription)
        session.flush()
    else:
        subscription.status = "active"

    organization_package = session.execute(
        select(OrganizationPackage).where(
            OrganizationPackage.organization_id == organization.id,
            OrganizationPackage.package_id == package.id,
        )
    ).scalar_one_or_none()
    if organization_package is None:
        organization_package = OrganizationPackage(
            organization_id=organization.id,
            package_id=package.id,
            assigned_analysis_quota=config.package_analysis_quota,
            status="active",
        )
        session.add(organization_package)
        session.flush()
    else:
        organization_package.assigned_analysis_quota = config.package_analysis_quota
        organization_package.status = "active"

    session.commit()

    return MvpTestSeedResult(
        organization_id=organization.id,
        user_id=user.id,
        auth_user_id=user.auth_user_id,
        user_organization_id=user_organization.id,
        role_key=role.key,
        plan_id=plan.id,
        package_id=package.id,
        subscription_id=subscription.id,
        organization_package_id=organization_package.id,
    )
