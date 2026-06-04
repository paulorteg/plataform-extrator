"""create extraction validation tables

Revision ID: 0008_create_extraction_validation_tables
Revises: 0007_create_document_pages_and_occurrences
Create Date: 2026-06-04 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Optional, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0008_create_extraction_validation_tables"
down_revision: Optional[str] = "0007_create_document_pages_and_occurrences"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    uuid_type = sa.Uuid(as_uuid=False)

    op.create_table(
        "evidences",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("occurrence_id", uuid_type, nullable=False),
        sa.Column("document_page_id", uuid_type, nullable=True),
        sa.Column("field_key", sa.String(length=128), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("text_excerpt", sa.Text(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=True),
        sa.Column("end_offset", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 100",
            name="ck_evidences_confidence_range",
        ),
        sa.ForeignKeyConstraint(["document_page_id"], ["document_pages.id"]),
        sa.ForeignKeyConstraint(["occurrence_id"], ["occurrences.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidences_organization_id", "evidences", ["organization_id"])
    op.create_index("ix_evidences_occurrence_id", "evidences", ["occurrence_id"])
    op.create_index("ix_evidences_field_key", "evidences", ["field_key"])

    op.create_table(
        "extracted_fields",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("occurrence_id", uuid_type, nullable=False),
        sa.Column("evidence_id", uuid_type, nullable=True),
        sa.Column("field_key", sa.String(length=128), nullable=False),
        sa.Column("group_key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("extraction_method", sa.String(length=64), nullable=False),
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
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 100",
            name="ck_extracted_fields_confidence_range",
        ),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidences.id"]),
        sa.ForeignKeyConstraint(["occurrence_id"], ["occurrences.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "occurrence_id",
            "field_key",
            name="uq_extracted_fields_occurrence_field",
        ),
    )
    op.create_index("ix_extracted_fields_organization_id", "extracted_fields", ["organization_id"])
    op.create_index("ix_extracted_fields_occurrence_id", "extracted_fields", ["occurrence_id"])
    op.create_index("ix_extracted_fields_field_key", "extracted_fields", ["field_key"])
    op.create_index("ix_extracted_fields_status", "extracted_fields", ["status"])

    op.create_table(
        "validation_issues",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("occurrence_id", uuid_type, nullable=False),
        sa.Column("field_id", uuid_type, nullable=True),
        sa.Column("field_key", sa.String(length=128), nullable=False),
        sa.Column("issue_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["field_id"], ["extracted_fields.id"]),
        sa.ForeignKeyConstraint(["occurrence_id"], ["occurrences.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_validation_issues_organization_id", "validation_issues", ["organization_id"])
    op.create_index("ix_validation_issues_occurrence_id", "validation_issues", ["occurrence_id"])
    op.create_index("ix_validation_issues_field_key", "validation_issues", ["field_key"])
    op.create_index("ix_validation_issues_status", "validation_issues", ["status"])


def downgrade() -> None:
    op.drop_index("ix_validation_issues_status", table_name="validation_issues")
    op.drop_index("ix_validation_issues_field_key", table_name="validation_issues")
    op.drop_index("ix_validation_issues_occurrence_id", table_name="validation_issues")
    op.drop_index("ix_validation_issues_organization_id", table_name="validation_issues")
    op.drop_table("validation_issues")
    op.drop_index("ix_extracted_fields_status", table_name="extracted_fields")
    op.drop_index("ix_extracted_fields_field_key", table_name="extracted_fields")
    op.drop_index("ix_extracted_fields_occurrence_id", table_name="extracted_fields")
    op.drop_index("ix_extracted_fields_organization_id", table_name="extracted_fields")
    op.drop_table("extracted_fields")
    op.drop_index("ix_evidences_field_key", table_name="evidences")
    op.drop_index("ix_evidences_occurrence_id", table_name="evidences")
    op.drop_index("ix_evidences_organization_id", table_name="evidences")
    op.drop_table("evidences")
