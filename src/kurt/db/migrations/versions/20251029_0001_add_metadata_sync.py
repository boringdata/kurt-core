"""Add metadata sync queue and trigger

Revision ID: 002_metadata_sync
Revises: 001_initial
Create Date: 2025-10-29

This migration adds:
1. metadata_sync_queue table for tracking documents that need frontmatter sync
2. SQL trigger to automatically populate the queue when document metadata changes
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_metadata_sync"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add metadata_sync_queue table and trigger."""

    # Create metadata_sync_queue table
    op.create_table(
        "metadata_sync_queue",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_metadata_sync_queue_document_id"),
        "metadata_sync_queue",
        ["document_id"],
        unique=False,
    )

    # Create trigger to populate queue when document metadata changes
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS documents_metadata_sync_trigger
        AFTER UPDATE ON documents
        WHEN (
            NEW.content_type != OLD.content_type OR
            NEW.primary_topics != OLD.primary_topics OR
            NEW.tools_technologies != OLD.tools_technologies OR
            NEW.title != OLD.title OR
            NEW.description != OLD.description OR
            NEW.author != OLD.author OR
            NEW.published_date != OLD.published_date OR
            NEW.indexed_with_hash != OLD.indexed_with_hash
        )
        BEGIN
            INSERT INTO metadata_sync_queue (document_id, created_at)
            VALUES (NEW.id, datetime('now'));
        END;
    """)


def downgrade() -> None:
    """Remove metadata_sync_queue table and trigger."""

    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS documents_metadata_sync_trigger")

    # Drop table
    op.drop_index(op.f("ix_metadata_sync_queue_document_id"), table_name="metadata_sync_queue")
    op.drop_table("metadata_sync_queue")
