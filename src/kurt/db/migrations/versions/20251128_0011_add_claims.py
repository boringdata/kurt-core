"""Add claims knowledge graph schema

Revision ID: 011_add_claims
Revises: 010_drop_metadata_fields
Create Date: 2025-11-28

This migration adds claims support to the knowledge graph:
- Creates claims table for storing extracted claims
- Creates document_claims junction table for document-to-claim relationships
- Creates claim_entities junction table for claim-to-entity relationships
- Adds indexes for efficient querying

Claims are factual assertions, capabilities, comparisons, or other
statements that can be sourced and verified. They link to:
- Documents (where the claim was found)
- Entities (source: who made the claim, subject: what it's about, object: compared to)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import JSON

# revision identifiers, used by Alembic.
revision: str = "011_add_claims"
down_revision: Union[str, None] = "010_drop_metadata_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add claims knowledge graph schema."""

    # 1. Create claims table
    op.create_table(
        "claims",
        sa.Column("id", sa.String(), nullable=False),
        # Claim content
        sa.Column("claim_text", sa.String(), nullable=False),
        sa.Column("claim_type", sa.String(), nullable=False),
        sa.Column("canonical_text", sa.String(), nullable=True),
        # Source tracking
        sa.Column("source_entity_id", sa.String(), nullable=True),
        # Resolution and disambiguation
        sa.Column("aliases", JSON(), nullable=True),
        # Vector embedding for similarity search (512-dim float32 = 2048 bytes)
        sa.Column("embedding", sa.LargeBinary(), nullable=True),
        # Confidence and usage metrics
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("source_mentions", sa.Integer(), nullable=False, server_default="0"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_entity_id"], ["entities.id"], ondelete="SET NULL"),
    )

    # Create indexes for claims table
    op.create_index("ix_claims_claim_text", "claims", ["claim_text"])
    op.create_index("ix_claims_claim_type", "claims", ["claim_type"])
    op.create_index("ix_claims_canonical_text", "claims", ["canonical_text"])
    op.create_index("ix_claims_source_entity_id", "claims", ["source_entity_id"])
    op.create_index("ix_claims_confidence_score", "claims", ["confidence_score"])

    # 2. Create document_claims junction table
    # Links documents to claims they contain
    op.create_table(
        "document_claims",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("claim_id", sa.String(), nullable=False),
        # Context and confidence
        sa.Column("quote", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
    )

    # Create indexes for document_claims
    op.create_index("ix_document_claims_document_id", "document_claims", ["document_id"])
    op.create_index("ix_document_claims_claim_id", "document_claims", ["claim_id"])
    # Unique constraint to prevent duplicate document-claim pairs
    op.create_index(
        "ix_document_claims_document_claim_unique",
        "document_claims",
        ["document_id", "claim_id"],
        unique=True,
    )

    # 3. Create claim_entities junction table
    # Links claims to related entities with roles (source, subject, object)
    op.create_table(
        "claim_entities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("claim_id", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),  # source, subject, object
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="CASCADE"),
    )

    # Create indexes for claim_entities
    op.create_index("ix_claim_entities_claim_id", "claim_entities", ["claim_id"])
    op.create_index("ix_claim_entities_entity_id", "claim_entities", ["entity_id"])
    op.create_index("ix_claim_entities_role", "claim_entities", ["role"])
    # Composite index for querying specific claim-entity relationships
    op.create_index(
        "ix_claim_entities_claim_entity_role",
        "claim_entities",
        ["claim_id", "entity_id", "role"],
        unique=True,
    )

    # Note: sqlite-vec extension virtual tables for claims are NOT created here
    # They must be created at runtime when the extension is loaded
    # See src/kurt/db/sqlite.py for claim_embeddings vec0 table creation


def downgrade() -> None:
    """Remove claims knowledge graph schema."""

    # Drop claim_entities table and its indexes
    op.drop_index("ix_claim_entities_claim_entity_role", "claim_entities")
    op.drop_index("ix_claim_entities_role", "claim_entities")
    op.drop_index("ix_claim_entities_entity_id", "claim_entities")
    op.drop_index("ix_claim_entities_claim_id", "claim_entities")
    op.drop_table("claim_entities")

    # Drop document_claims table and its indexes
    op.drop_index("ix_document_claims_document_claim_unique", "document_claims")
    op.drop_index("ix_document_claims_claim_id", "document_claims")
    op.drop_index("ix_document_claims_document_id", "document_claims")
    op.drop_table("document_claims")

    # Drop claims table and its indexes
    op.drop_index("ix_claims_confidence_score", "claims")
    op.drop_index("ix_claims_source_entity_id", "claims")
    op.drop_index("ix_claims_canonical_text", "claims")
    op.drop_index("ix_claims_claim_type", "claims")
    op.drop_index("ix_claims_claim_text", "claims")
    op.drop_table("claims")
