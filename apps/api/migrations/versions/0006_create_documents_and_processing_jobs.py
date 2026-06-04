"""create documents and processing jobs

Revision ID: 0006_create_documents_and_processing_jobs
Revises: 0005_create_billing_and_usage_tables
Create Date: 2026-06-04 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Optional, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0006_create_documents_and_processing_jobs"
down_revision: Optional[str] = "0005_create_billing_and_usage_tables"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    uuid_type = sa.Uuid(as_uuid=False)

    op.create_table(
        "documents",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("uploaded_by_user_id", uuid_type, nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_bucket", sa.String(length=128), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("storage_uri", sa.String(length=1200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("size_bytes > 0", name="ck_documents_size_positive"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_uri", name="uq_documents_storage_uri"),
    )
    op.create_index("ix_documents_created_at", "documents", ["created_at"])
    op.create_index("ix_documents_organization_id", "documents", ["organization_id"])
    op.create_index("ix_documents_sha256_hash", "documents", ["sha256_hash"])
    op.create_index("ix_documents_status", "documents", ["status"])

    op.create_table(
        "processing_jobs",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("document_id", uuid_type, nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.String(length=512), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("attempts >= 0", name="ck_processing_jobs_attempts_non_negative"),
        sa.CheckConstraint("max_attempts > 0", name="ck_processing_jobs_max_attempts_positive"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_processing_jobs_created_at", "processing_jobs", ["created_at"])
    op.create_index("ix_processing_jobs_document_id", "processing_jobs", ["document_id"])
    op.create_index("ix_processing_jobs_organization_id", "processing_jobs", ["organization_id"])
    op.create_index("ix_processing_jobs_status_priority", "processing_jobs", ["status", "priority"])


def downgrade() -> None:
    op.drop_index("ix_processing_jobs_status_priority", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_organization_id", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_document_id", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_created_at", table_name="processing_jobs")
    op.drop_table("processing_jobs")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_sha256_hash", table_name="documents")
    op.drop_index("ix_documents_organization_id", table_name="documents")
    op.drop_index("ix_documents_created_at", table_name="documents")
    op.drop_table("documents")
