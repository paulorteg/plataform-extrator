"""create document pages and occurrences

Revision ID: 0007_create_document_pages_and_occurrences
Revises: 0006_create_documents_and_processing_jobs
Create Date: 2026-06-04 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Optional, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0007_create_document_pages_and_occurrences"
down_revision: Optional[str] = "0006_create_documents_and_processing_jobs"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    uuid_type = sa.Uuid(as_uuid=False)

    op.create_table(
        "document_pages",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("document_id", uuid_type, nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("extraction_method", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.String(length=64), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
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
        sa.CheckConstraint("page_number > 0", name="ck_document_pages_page_number_positive"),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 100)",
            name="ck_document_pages_confidence_range",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "page_number",
            name="uq_document_pages_document_page_number",
        ),
    )
    op.create_index("ix_document_pages_document_id", "document_pages", ["document_id"])
    op.create_index("ix_document_pages_organization_id", "document_pages", ["organization_id"])
    op.create_index("ix_document_pages_status", "document_pages", ["status"])

    op.create_table(
        "occurrences",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("document_id", uuid_type, nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("document_family", sa.String(length=64), nullable=False),
        sa.Column("classification_confidence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("text_excerpt", sa.Text(), nullable=False),
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
        sa.CheckConstraint("sequence_number > 0", name="ck_occurrences_sequence_number_positive"),
        sa.CheckConstraint(
            "classification_confidence >= 0 AND classification_confidence <= 100",
            name="ck_occurrences_confidence_range",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "sequence_number",
            name="uq_occurrences_document_sequence",
        ),
    )
    op.create_index("ix_occurrences_document_id", "occurrences", ["document_id"])
    op.create_index("ix_occurrences_organization_id", "occurrences", ["organization_id"])
    op.create_index("ix_occurrences_status", "occurrences", ["status"])


def downgrade() -> None:
    op.drop_index("ix_occurrences_status", table_name="occurrences")
    op.drop_index("ix_occurrences_organization_id", table_name="occurrences")
    op.drop_index("ix_occurrences_document_id", table_name="occurrences")
    op.drop_table("occurrences")
    op.drop_index("ix_document_pages_status", table_name="document_pages")
    op.drop_index("ix_document_pages_organization_id", table_name="document_pages")
    op.drop_index("ix_document_pages_document_id", table_name="document_pages")
    op.drop_table("document_pages")
