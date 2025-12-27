"""Add cms_platform and cms_instance fields to documents table

Revision ID: 006_cms_platform_instance
Revises: 005_analytics_domain_uuid
Create Date: 2025-11-11

This migration adds:
1. cms_platform field to documents table (sanity, contentful, wordpress)
2. cms_instance field to documents table (prod, staging, default)
3. Indexes on both fields for fast CMS document lookups

These fields eliminate the need to parse source_url to detect CMS platform/instance
during fetch operations, enabling direct CMS adapter usage with field mappings.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_cms_platform_instance"
down_revision: Union[str, None] = "005_analytics_domain_uuid"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cms_platform and cms_instance columns to documents table."""

    # Add cms_platform column
    op.add_column(
        "documents",
        sa.Column("cms_platform", sa.String(), nullable=True),
    )

    # Add cms_instance column
    op.add_column(
        "documents",
        sa.Column("cms_instance", sa.String(), nullable=True),
    )

    # Create index on cms_platform for filtering CMS documents
    op.create_index(
        op.f("ix_documents_cms_platform"),
        "documents",
        ["cms_platform"],
        unique=False,
    )

    # Create index on cms_instance for filtering by instance
    op.create_index(
        op.f("ix_documents_cms_instance"),
        "documents",
        ["cms_instance"],
        unique=False,
    )


def downgrade() -> None:
    """Remove cms_platform and cms_instance columns from documents table."""

    # Drop indexes
    op.drop_index(op.f("ix_documents_cms_instance"), table_name="documents")
    op.drop_index(op.f("ix_documents_cms_platform"), table_name="documents")

    # Drop columns
    op.drop_column("documents", "cms_instance")
    op.drop_column("documents", "cms_platform")
