"""create review versions and generated reports

Revision ID: 0009_create_review_versions_and_generated_reports
Revises: 0008_create_extraction_validation_tables
Create Date: 2026-06-04 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Optional, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0009_create_review_versions_and_generated_reports"
down_revision: Optional[str] = "0008_create_extraction_validation_tables"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    uuid_type = sa.Uuid(as_uuid=False)

    op.create_table(
        "review_versions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("occurrence_id", uuid_type, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("approved_by_user_id", uuid_type, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["occurrence_id"], ["occurrences.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "occurrence_id",
            "version",
            name="uq_review_versions_occurrence_version",
        ),
    )
    op.create_index("ix_review_versions_organization_id", "review_versions", ["organization_id"])
    op.create_index("ix_review_versions_occurrence_id", "review_versions", ["occurrence_id"])

    op.create_table(
        "generated_reports",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("occurrence_id", uuid_type, nullable=False),
        sa.Column("generated_by_user_id", uuid_type, nullable=False),
        sa.Column("report_type", sa.String(length=64), nullable=False),
        sa.Column("template_version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("storage_bucket", sa.String(length=128), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("storage_uri", sa.String(length=1200), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["occurrence_id"], ["occurrences.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_uri", name="uq_generated_reports_storage_uri"),
    )
    op.create_index("ix_generated_reports_organization_id", "generated_reports", ["organization_id"])
    op.create_index("ix_generated_reports_occurrence_id", "generated_reports", ["occurrence_id"])
    op.create_index("ix_generated_reports_status", "generated_reports", ["status"])


def downgrade() -> None:
    op.drop_index("ix_generated_reports_status", table_name="generated_reports")
    op.drop_index("ix_generated_reports_occurrence_id", table_name="generated_reports")
    op.drop_index("ix_generated_reports_organization_id", table_name="generated_reports")
    op.drop_table("generated_reports")
    op.drop_index("ix_review_versions_occurrence_id", table_name="review_versions")
    op.drop_index("ix_review_versions_organization_id", table_name="review_versions")
    op.drop_table("review_versions")
