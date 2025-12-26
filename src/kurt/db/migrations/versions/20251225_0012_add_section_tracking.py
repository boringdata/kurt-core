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

# revision identifiers, used by Alembic.
revision: str = "012_add_section_tracking"
down_revision: Union[str, None] = "011_add_claims"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add section tracking to knowledge graph."""

    # 1. Add section_id to document_entities
    op.add_column(
        "document_entities",
        sa.Column("section_id", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_document_entities_section_id",
        "document_entities",
        ["section_id"],
    )

    # Drop the old unique constraint and create new one including section_id
    # This allows the same entity to appear in multiple sections of the same doc
    op.drop_index("ix_document_entities_document_entity_unique", "document_entities")
    op.create_index(
        "ix_document_entities_doc_entity_section_unique",
        "document_entities",
        ["document_id", "entity_id", "section_id"],
        unique=True,
    )

    # 2. Create document_entity_relationships junction table
    # Links EntityRelationship (deduplicated) to all documents/sections that evidence it
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

    # Create indexes
    op.create_index(
        "ix_doc_entity_rel_relationship_id",
        "document_entity_relationships",
        ["relationship_id"],
    )
    op.create_index(
        "ix_doc_entity_rel_document_id",
        "document_entity_relationships",
        ["document_id"],
    )
    op.create_index(
        "ix_doc_entity_rel_section_id",
        "document_entity_relationships",
        ["section_id"],
    )
    # Unique constraint to prevent duplicate entries
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
