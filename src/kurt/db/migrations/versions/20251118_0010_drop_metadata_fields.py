"""Drop deprecated metadata fields from documents table

Revision ID: 010_drop_metadata_fields
Revises: 009_add_page_analytics
Create Date: 2025-11-18

This migration removes redundant fields that have been migrated to the knowledge graph:
- Drops Document.primary_topics (now Entity with type="Topic")
- Drops Document.tools_technologies (now Entity with type="Technology"|"Tool"|"Product")

NOTE: Embedding fields are KEPT as they are used for vector search in entity_embeddings table.

Related Issue: #16 - Data Model Simplification

IMPORTANT: Before running this migration:
1. Run the backfill script: python scripts/migrate_metadata_to_entities.py
2. Verify migration: python scripts/verify_metadata_migration.py
3. Ensure all systems are using knowledge graph APIs (not metadata fields)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import JSON

# revision identifiers, used by Alembic.
revision: str = "010_drop_metadata_fields"
down_revision: Union[str, None] = "009_add_page_analytics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Drop deprecated metadata fields from documents table.

    WARNING: This is a destructive operation. Ensure data has been migrated first!

    NOTE: Embedding fields are KEPT as they are used for vector search.
    """
    # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
    # Get the database dialect
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "sqlite":
        # SQLite: Recreate table without deprecated columns
        with op.batch_alter_table("documents", schema=None) as batch_op:
            batch_op.drop_column("primary_topics")
            batch_op.drop_column("tools_technologies")

    elif dialect == "postgresql":
        # PostgreSQL: Direct column drop
        op.drop_column("documents", "primary_topics")
        op.drop_column("documents", "tools_technologies")

    else:
        # For other databases, try direct drop (may need customization)
        op.drop_column("documents", "primary_topics")
        op.drop_column("documents", "tools_technologies")


def downgrade() -> None:
    """
    Restore deprecated metadata fields.

    NOTE: This only recreates the columns - it does NOT restore the data!
    You would need to manually backfill from the knowledge graph if needed.
    """
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "sqlite":
        # SQLite: Add columns back
        with op.batch_alter_table("documents", schema=None) as batch_op:
            batch_op.add_column(sa.Column("primary_topics", JSON, nullable=True))
            batch_op.add_column(sa.Column("tools_technologies", JSON, nullable=True))

    elif dialect == "postgresql":
        # PostgreSQL: Direct column add
        op.add_column("documents", sa.Column("primary_topics", JSON, nullable=True))
        op.add_column("documents", sa.Column("tools_technologies", JSON, nullable=True))

    else:
        # For other databases
        op.add_column("documents", sa.Column("primary_topics", JSON, nullable=True))
        op.add_column("documents", sa.Column("tools_technologies", JSON, nullable=True))
