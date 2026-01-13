"""Add unique constraint on map_documents.source_url.

Revision ID: 004_unique_source_url
Revises: 003_normalize_status
Create Date: 2026-01-13

This migration:
1. Removes duplicate rows (keeping the oldest by document_id)
2. Adds unique constraint on source_url column
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_unique_source_url"
down_revision: Union[str, None] = "003_normalize_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, remove duplicate source_urls (keep the row with MIN document_id - typically the oldest)
    # This handles cases where multiple documents have the same URL
    op.execute("""
        DELETE FROM map_documents
        WHERE document_id NOT IN (
            SELECT MIN(document_id)
            FROM map_documents
            GROUP BY source_url
        )
    """)

    # Also clean up any orphaned fetch_documents that reference deleted map_documents
    op.execute("""
        DELETE FROM fetch_documents
        WHERE document_id NOT IN (
            SELECT document_id FROM map_documents
        )
    """)

    # Add unique constraint on source_url
    # Note: SQLite doesn't support adding constraints directly, so we need to recreate the table
    # Using batch mode which handles this automatically
    with op.batch_alter_table("map_documents") as batch_op:
        batch_op.create_unique_constraint("uq_map_documents_source_url", ["source_url"])


def downgrade() -> None:
    # Remove the unique constraint
    with op.batch_alter_table("map_documents") as batch_op:
        batch_op.drop_constraint("uq_map_documents_source_url", type_="unique")
