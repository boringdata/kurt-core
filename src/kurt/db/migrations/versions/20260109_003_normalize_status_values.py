"""Normalize legacy status values to new PENDING/SUCCESS/ERROR standard.

Revision ID: 003_normalize_status
Revises: 002_workflow_tables
Create Date: 2026-01-09

This migration updates legacy status values in existing database rows:
- fetch_documents: FETCHED -> SUCCESS
- map_documents: DISCOVERED -> SUCCESS, EXISTING -> SUCCESS
- research_documents: COMPLETED -> SUCCESS
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_normalize_status"
down_revision: Union[str, None] = "002_workflow_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Normalize fetch_documents status
    op.execute("UPDATE fetch_documents SET status = 'SUCCESS' WHERE status = 'FETCHED'")

    # Normalize map_documents status
    op.execute(
        "UPDATE map_documents SET status = 'SUCCESS' WHERE status IN ('DISCOVERED', 'EXISTING')"
    )

    # Normalize research_documents status
    op.execute("UPDATE research_documents SET status = 'SUCCESS' WHERE status = 'COMPLETED'")


def downgrade() -> None:
    # Revert to legacy values (best effort - we can't distinguish DISCOVERED vs EXISTING)
    op.execute("UPDATE fetch_documents SET status = 'FETCHED' WHERE status = 'SUCCESS'")

    op.execute("UPDATE map_documents SET status = 'DISCOVERED' WHERE status = 'SUCCESS'")

    op.execute("UPDATE research_documents SET status = 'COMPLETED' WHERE status = 'SUCCESS'")
