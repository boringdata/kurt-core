"""Add section-level tracking for entities and relationships

Revision ID: 012_add_section_tracking
Revises: 011_add_claims
Create Date: 2025-12-25

This migration adds section-level granularity to the knowledge graph:
- Adds section_id column to document_entities table
- Creates document_entity_relationships junction table to track which
  documents/sections provide evidence for each relationship

This enables retrieval to find the exact section that mentions an entity
or evidences a relationship, rather than just the document.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "012_add_section_tracking"
down_revision: Union[str, None] = "011_add_claims"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(idx["name"] == index_name for idx in indexes)


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = inspector.get_columns(table_name)
    return any(col["name"] == column_name for col in columns)


def _table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    """Add section tracking to knowledge graph."""

    # 1. Add section_id to document_entities (if not already present)
    if not _column_exists("document_entities", "section_id"):
        op.add_column(
            "document_entities",
            sa.Column("section_id", sa.String(), nullable=True),
        )
    if not _index_exists("document_entities", "ix_document_entities_section_id"):
        op.create_index(
            "ix_document_entities_section_id",
            "document_entities",
            ["section_id"],
        )

    # Drop the old unique constraint and create new one including section_id
    # This allows the same entity to appear in multiple sections of the same doc
    if _index_exists("document_entities", "ix_document_entities_document_entity_unique"):
        op.drop_index("ix_document_entities_document_entity_unique", "document_entities")
    if not _index_exists("document_entities", "ix_document_entities_doc_entity_section_unique"):
        op.create_index(
            "ix_document_entities_doc_entity_section_unique",
            "document_entities",
            ["document_id", "entity_id", "section_id"],
            unique=True,
        )

    # 2. Create document_entity_relationships junction table (if not exists)
    # Links EntityRelationship (deduplicated) to all documents/sections that evidence it
    if not _table_exists("document_entity_relationships"):
        op.create_table(
            "document_entity_relationships",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("relationship_id", sa.String(), nullable=False),
            sa.Column("document_id", sa.String(), nullable=False),
            sa.Column("section_id", sa.String(), nullable=True),
            sa.Column("context", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["relationship_id"], ["entity_relationships.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        )

    # Create indexes (if not exist)
    if not _index_exists("document_entity_relationships", "ix_doc_entity_rel_relationship_id"):
        op.create_index(
            "ix_doc_entity_rel_relationship_id",
            "document_entity_relationships",
            ["relationship_id"],
        )
    if not _index_exists("document_entity_relationships", "ix_doc_entity_rel_document_id"):
        op.create_index(
            "ix_doc_entity_rel_document_id",
            "document_entity_relationships",
            ["document_id"],
        )
    if not _index_exists("document_entity_relationships", "ix_doc_entity_rel_section_id"):
        op.create_index(
            "ix_doc_entity_rel_section_id",
            "document_entity_relationships",
            ["section_id"],
        )
    # Unique constraint to prevent duplicate entries
    if not _index_exists("document_entity_relationships", "ix_doc_entity_rel_unique"):
        op.create_index(
            "ix_doc_entity_rel_unique",
            "document_entity_relationships",
            ["relationship_id", "document_id", "section_id"],
            unique=True,
        )


def downgrade() -> None:
    """Remove section tracking from knowledge graph."""

    # Drop document_entity_relationships table
    op.drop_index("ix_doc_entity_rel_unique", "document_entity_relationships")
    op.drop_index("ix_doc_entity_rel_section_id", "document_entity_relationships")
    op.drop_index("ix_doc_entity_rel_document_id", "document_entity_relationships")
    op.drop_index("ix_doc_entity_rel_relationship_id", "document_entity_relationships")
    op.drop_table("document_entity_relationships")

    # Restore original unique constraint on document_entities
    op.drop_index("ix_document_entities_doc_entity_section_unique", "document_entities")
    op.create_index(
        "ix_document_entities_document_entity_unique",
        "document_entities",
        ["document_id", "entity_id"],
        unique=True,
    )

    # Drop section_id from document_entities
    op.drop_index("ix_document_entities_section_id", "document_entities")
    op.drop_column("document_entities", "section_id")
