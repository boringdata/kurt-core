"""Add document_links table for internal document references

Revision ID: 007_document_links
Revises: 006_cms_platform_instance
Create Date: 2025-11-11

This migration adds:
1. document_links table for tracking internal document references
2. DocumentLinkType enum (outbound, related)
3. Indexes on source_document_id and target_document_id for fast lookups

This enables tracking which documents reference each other, finding prerequisites,
and discovering related content.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007_document_links"
down_revision: Union[str, None] = "006_cms_platform_instance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add document_links table."""

    # Create document_links table
    op.create_table(
        "document_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_document_id", sa.UUID(), nullable=False),
        sa.Column("target_document_id", sa.UUID(), nullable=False),
        sa.Column("link_type", sa.String(), nullable=False),
        sa.Column("anchor_text", sa.String(length=500), nullable=True),
        sa.Column("context", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["target_document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for fast lookups
    op.create_index(
        op.f("ix_document_links_source_document_id"),
        "document_links",
        ["source_document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_links_target_document_id"),
        "document_links",
        ["target_document_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove document_links table."""

    # Drop indexes
    op.drop_index(op.f("ix_document_links_target_document_id"), table_name="document_links")
    op.drop_index(op.f("ix_document_links_source_document_id"), table_name="document_links")

    # Drop table
    op.drop_table("document_links")
