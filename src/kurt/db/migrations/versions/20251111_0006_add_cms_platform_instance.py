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
    """Add cms_platform and cms_instance columns to documents table.

    Note: Columns may already exist if initial schema was updated.
    """
    conn = op.get_bind()

    # Check which columns already exist
    result = conn.execute(sa.text("PRAGMA table_info(documents)"))
    columns = {row[1] for row in result}

    # Add cms_platform column if not exists
    if "cms_platform" not in columns:
        op.add_column(
            "documents",
            sa.Column("cms_platform", sa.String(), nullable=True),
        )
        op.create_index(
            op.f("ix_documents_cms_platform"),
            "documents",
            ["cms_platform"],
            unique=False,
        )

    # Add cms_instance column if not exists
    if "cms_instance" not in columns:
        op.add_column(
            "documents",
            sa.Column("cms_instance", sa.String(), nullable=True),
        )
        op.create_index(
            op.f("ix_documents_cms_instance"),
            "documents",
            ["cms_instance"],
            unique=False,
        )


def downgrade() -> None:
    """Remove cms_platform and cms_instance columns from documents table."""
    conn = op.get_bind()

    # Check which columns exist
    result = conn.execute(sa.text("PRAGMA table_info(documents)"))
    columns = {row[1] for row in result}

    # Drop indexes and columns if they exist
    if "cms_instance" in columns:
        try:
            op.drop_index(op.f("ix_documents_cms_instance"), table_name="documents")
        except Exception:
            pass
        op.drop_column("documents", "cms_instance")

    if "cms_platform" in columns:
        try:
            op.drop_index(op.f("ix_documents_cms_platform"), table_name="documents")
        except Exception:
            pass
        op.drop_column("documents", "cms_platform")
