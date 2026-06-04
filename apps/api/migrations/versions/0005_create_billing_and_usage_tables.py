"""create billing and usage tables

Revision ID: 0005_create_billing_and_usage_tables
Revises: 0004_create_audit_logs
Create Date: 2026-06-04 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Optional, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0005_create_billing_and_usage_tables"
down_revision: Optional[str] = "0004_create_audit_logs"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    uuid_type = sa.Uuid(as_uuid=False)

    op.create_table(
        "plans",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("monthly_analysis_limit", sa.Integer(), nullable=True),
        sa.Column("allow_overage", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("monthly_analysis_limit IS NULL OR monthly_analysis_limit >= 0", name="ck_plans_monthly_limit_non_negative"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_plans_key"),
    )
    op.create_index("ix_plans_status", "plans", ["status"])

    op.create_table(
        "entitlements",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_entitlements_key"),
    )
    op.create_index("ix_entitlements_status", "entitlements", ["status"])

    op.create_table(
        "packages",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("plan_id", uuid_type, nullable=True),
        sa.Column("analysis_quota", sa.Integer(), nullable=False),
        sa.Column("entitlements", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("analysis_quota >= 0", name="ck_packages_analysis_quota_non_negative"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_packages_key"),
    )
    op.create_index("ix_packages_plan_id", "packages", ["plan_id"])
    op.create_index("ix_packages_status", "packages", ["status"])

    op.create_table(
        "subscriptions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("plan_id", uuid_type, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_organization_id", "subscriptions", ["organization_id"])
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])

    op.create_table(
        "organization_packages",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("package_id", uuid_type, nullable=False),
        sa.Column("assigned_analysis_quota", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("assigned_analysis_quota >= 0", name="ck_organization_packages_quota_non_negative"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["package_id"], ["packages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organization_packages_organization_id", "organization_packages", ["organization_id"])
    op.create_index("ix_organization_packages_package_id", "organization_packages", ["package_id"])
    op.create_index("ix_organization_packages_status", "organization_packages", ["status"])

    op.create_table(
        "usage_events",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("occurrence_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_usage_events_amount_positive"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_usage_events_idempotency_key"),
        sa.UniqueConstraint(
            "organization_id",
            "occurrence_id",
            "event_type",
            name="uq_usage_events_organization_occurrence_type",
        ),
    )
    op.create_index("ix_usage_events_created_at", "usage_events", ["created_at"])
    op.create_index("ix_usage_events_organization_id", "usage_events", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_usage_events_organization_id", table_name="usage_events")
    op.drop_index("ix_usage_events_created_at", table_name="usage_events")
    op.drop_table("usage_events")
    op.drop_index("ix_organization_packages_status", table_name="organization_packages")
    op.drop_index("ix_organization_packages_package_id", table_name="organization_packages")
    op.drop_index("ix_organization_packages_organization_id", table_name="organization_packages")
    op.drop_table("organization_packages")
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_plan_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_organization_id", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index("ix_packages_status", table_name="packages")
    op.drop_index("ix_packages_plan_id", table_name="packages")
    op.drop_table("packages")
    op.drop_index("ix_entitlements_status", table_name="entitlements")
    op.drop_table("entitlements")
    op.drop_index("ix_plans_status", table_name="plans")
    op.drop_table("plans")
