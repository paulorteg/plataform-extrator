"""create users and organizations

Revision ID: 0002_create_users_and_organizations
Revises: 0001_initial_empty_schema
Create Date: 2026-06-04 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Optional, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002_create_users_and_organizations"
down_revision: Optional[str] = "0001_initial_empty_schema"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    uuid_type = sa.Uuid(as_uuid=False)

    op.create_table(
        "organizations",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=True),
        sa.Column("cnpj_hash", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizations_status", "organizations", ["status"])

    op.create_table(
        "users",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("auth_user_id", uuid_type, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("auth_user_id", name="uq_users_auth_user_id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("id", "auth_user_id", name="uq_users_id_auth_user_id"),
    )
    op.create_index("ix_users_status", "users", ["status"])

    op.create_table(
        "user_organizations",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("auth_user_id", uuid_type, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("role_key", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "auth_user_id"],
            ["users.id", "users.auth_user_id"],
            name="fk_user_organizations_user_auth_pair",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_user_organizations_user_org"),
    )
    op.create_index("ix_user_organizations_auth_user_id", "user_organizations", ["auth_user_id"])
    op.create_index("ix_user_organizations_organization_id", "user_organizations", ["organization_id"])
    op.create_index("ix_user_organizations_status", "user_organizations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_user_organizations_status", table_name="user_organizations")
    op.drop_index("ix_user_organizations_organization_id", table_name="user_organizations")
    op.drop_index("ix_user_organizations_auth_user_id", table_name="user_organizations")
    op.drop_table("user_organizations")
    op.drop_index("ix_users_status", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_organizations_status", table_name="organizations")
    op.drop_table("organizations")
