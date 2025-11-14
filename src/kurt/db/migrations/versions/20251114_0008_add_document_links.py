"""Add document_links table

Revision ID: 008_add_document_links
Revises: 007_add_knowledge_graph
Create Date: 2025-11-14

This migration adds document link tracking:
- Creates document_links table to store internal document references
- Stores source_document_id, target_document_id, and anchor_text
- Claude interprets anchor_text to understand relationship types
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008_add_document_links"
down_revision: Union[str, None] = "007_add_knowledge_graph"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create document_links table."""
    op.create_table(
        "document_links",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_document_id", sa.String(), nullable=False),
        sa.Column("target_document_id", sa.String(), nullable=False),
        sa.Column("anchor_text", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["documents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["target_document_id"],
            ["documents.id"],
        ),
    )

    # Create indexes for efficient querying
    op.create_index(
        "ix_document_links_source_document_id",
        "document_links",
        ["source_document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_links_target_document_id",
        "document_links",
        ["target_document_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop document_links table."""
    op.drop_index("ix_document_links_target_document_id", table_name="document_links")
    op.drop_index("ix_document_links_source_document_id", table_name="document_links")
    op.drop_table("document_links")
