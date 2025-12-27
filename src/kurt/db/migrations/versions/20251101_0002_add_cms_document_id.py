"""Add cms_document_id field to documents table

Revision ID: 003_cms_document_id
Revises: 002_metadata_sync
Create Date: 2025-11-01

This migration adds:
1. cms_document_id field to documents table for storing external CMS identifiers
2. Index on cms_document_id for fast lookups during fetch operations
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_cms_document_id"
down_revision: Union[str, None] = "002_metadata_sync"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cms_document_id column to documents table."""

    # Add cms_document_id column
    op.add_column(
        "documents",
        sa.Column("cms_document_id", sa.String(), nullable=True),
    )

    # Create index on cms_document_id for fast lookups
    op.create_index(
        op.f("ix_documents_cms_document_id"),
        "documents",
        ["cms_document_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove cms_document_id column from documents table."""

    # Drop index
    op.drop_index(op.f("ix_documents_cms_document_id"), table_name="documents")

    # Drop column
    op.drop_column("documents", "cms_document_id")
