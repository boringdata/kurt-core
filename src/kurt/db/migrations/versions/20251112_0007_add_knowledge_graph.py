"""Add knowledge graph schema

Revision ID: 007_add_knowledge_graph
Revises: 006_cms_platform_instance
Create Date: 2025-11-12

This migration adds knowledge graph support:
- Adds embedding column to documents table for document-level embeddings
- Enhances entities table with aliases, descriptions, and entity resolution fields
- Creates entity_relationships table for entity-to-entity relationships
- Creates document_entities junction table for document-to-entity relationships
- Adds indexes for efficient querying

Note: sqlite-vec extension must be loaded separately for vector operations.
The extension provides vec0 virtual table for similarity search.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import JSON

# revision identifiers, used by Alembic.
revision: str = "007_add_knowledge_graph"
down_revision: Union[str, None] = "006_cms_platform_instance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add knowledge graph schema."""

    # 1. Add embedding column to documents table
    # Store as BLOB (bytes) - will be 512 float32 values = 2048 bytes
    op.add_column("documents", sa.Column("embedding", sa.LargeBinary(), nullable=True))

    # 2. Enhance entities table with new fields
    # canonical_name: The resolved/canonical name for this entity
    op.add_column("entities", sa.Column("canonical_name", sa.String(), nullable=True))
    # aliases: JSON array of alternative names/spellings
    op.add_column("entities", sa.Column("aliases", JSON(), nullable=True))
    # description: Brief description of the entity
    op.add_column("entities", sa.Column("description", sa.String(), nullable=True))
    # embedding: 512-dim vector for entity similarity search
    op.add_column("entities", sa.Column("embedding", sa.LargeBinary(), nullable=True))
    # confidence_score: How confident we are in this entity (0.0-1.0)
    op.add_column(
        "entities",
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
    )
    # source_mentions: How many times this entity has been mentioned across documents
    op.add_column(
        "entities",
        sa.Column("source_mentions", sa.Integer(), nullable=False, server_default="0"),
    )

    # 3. Create entity_relationships table
    # This stores relationships between entities (e.g., "React" integrates_with "Next.js")
    op.create_table(
        "entity_relationships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_entity_id", sa.String(), nullable=False),
        sa.Column("target_entity_id", sa.String(), nullable=False),
        sa.Column("relationship_type", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("context", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entities.id"], ondelete="CASCADE"),
    )

    # Create indexes for entity_relationships
    op.create_index(
        "ix_entity_relationships_source_entity_id",
        "entity_relationships",
        ["source_entity_id"],
    )
    op.create_index(
        "ix_entity_relationships_target_entity_id",
        "entity_relationships",
        ["target_entity_id"],
    )
    op.create_index(
        "ix_entity_relationships_type",
        "entity_relationships",
        ["relationship_type"],
    )
    # Composite index for querying specific relationships
    op.create_index(
        "ix_entity_relationships_source_target",
        "entity_relationships",
        ["source_entity_id", "target_entity_id", "relationship_type"],
    )

    # 4. Create document_entities junction table
    # This links documents to entities they mention
    op.create_table(
        "document_entities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("mention_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("context", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="CASCADE"),
    )

    # Create indexes for document_entities
    op.create_index(
        "ix_document_entities_document_id",
        "document_entities",
        ["document_id"],
    )
    op.create_index(
        "ix_document_entities_entity_id",
        "document_entities",
        ["entity_id"],
    )
    # Unique constraint to prevent duplicate document-entity pairs
    op.create_index(
        "ix_document_entities_document_entity_unique",
        "document_entities",
        ["document_id", "entity_id"],
        unique=True,
    )

    # 5. Create indexes on new entity fields for efficient queries
    op.create_index("ix_entities_canonical_name", "entities", ["canonical_name"])
    op.create_index("ix_entities_confidence_score", "entities", ["confidence_score"])

    # Note: sqlite-vec extension virtual tables are NOT created here
    # They must be created at runtime when the extension is loaded
    # See src/kurt/db/sqlite.py for vec0 table creation


def downgrade() -> None:
    """Remove knowledge graph schema."""

    # Drop indexes first
    op.drop_index("ix_entities_confidence_score", "entities")
    op.drop_index("ix_entities_canonical_name", "entities")

    # Drop document_entities table and its indexes
    op.drop_index("ix_document_entities_document_entity_unique", "document_entities")
    op.drop_index("ix_document_entities_entity_id", "document_entities")
    op.drop_index("ix_document_entities_document_id", "document_entities")
    op.drop_table("document_entities")

    # Drop entity_relationships table and its indexes
    op.drop_index("ix_entity_relationships_source_target", "entity_relationships")
    op.drop_index("ix_entity_relationships_type", "entity_relationships")
    op.drop_index("ix_entity_relationships_target_entity_id", "entity_relationships")
    op.drop_index("ix_entity_relationships_source_entity_id", "entity_relationships")
    op.drop_table("entity_relationships")

    # Drop new columns from entities table
    op.drop_column("entities", "source_mentions")
    op.drop_column("entities", "confidence_score")
    op.drop_column("entities", "embedding")
    op.drop_column("entities", "description")
    op.drop_column("entities", "aliases")
    op.drop_column("entities", "canonical_name")

    # Drop embedding column from documents table
    op.drop_column("documents", "embedding")
