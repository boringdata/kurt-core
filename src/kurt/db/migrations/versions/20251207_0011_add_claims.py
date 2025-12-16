"""Add claims tables for claim extraction and tracking.

Revision ID: 0011
Revises: 0010
Create Date: 2024-12-07

This migration adds:
- claims table: Store extracted factual claims
- claim_entities table: Junction table for claim-entity relationships
- claim_relationships table: Track claim relationships (conflicts, support, etc.)
- in_conflict relationship type to RelationshipType enum
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "011_add_claims"
down_revision = "010_drop_metadata_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add claims tables."""

    # Create claims table
    op.create_table(
        "claims",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("statement", sa.String(), nullable=False),
        sa.Column("claim_type", sa.String(), nullable=False),
        sa.Column("subject_entity_id", sa.String(), nullable=False),
        sa.Column("source_document_id", sa.String(), nullable=False),
        sa.Column("source_quote", sa.String(), nullable=False),
        sa.Column("source_location_start", sa.Integer(), nullable=False),
        sa.Column("source_location_end", sa.Integer(), nullable=False),
        sa.Column("source_context", sa.String(), nullable=True),
        sa.Column("temporal_qualifier", sa.String(), nullable=True),
        sa.Column("extracted_date", sa.DateTime(), nullable=True),
        sa.Column("version_info", sa.String(), nullable=True),
        sa.Column("extraction_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("source_authority", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("corroboration_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("overall_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_superseded", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("superseded_by_id", sa.String(), nullable=True),
        sa.Column("embedding", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("indexed_with_git_commit", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["subject_entity_id"], ["entities.id"]),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["claims.id"]),
    )

    # Create indices for claims table
    op.create_index(op.f("ix_claims_statement"), "claims", ["statement"])
    op.create_index(op.f("ix_claims_claim_type"), "claims", ["claim_type"])
    op.create_index(op.f("ix_claims_subject_entity_id"), "claims", ["subject_entity_id"])
    op.create_index(op.f("ix_claims_source_document_id"), "claims", ["source_document_id"])

    # Create claim_entities junction table
    op.create_table(
        "claim_entities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("claim_id", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("entity_role", sa.String(), nullable=False, server_default="referenced"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"]),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"]),
    )

    # Create indices for claim_entities table
    op.create_index(op.f("ix_claim_entities_claim_id"), "claim_entities", ["claim_id"])
    op.create_index(op.f("ix_claim_entities_entity_id"), "claim_entities", ["entity_id"])

    # Create claim_relationships table
    op.create_table(
        "claim_relationships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_claim_id", sa.String(), nullable=False),
        sa.Column("target_claim_id", sa.String(), nullable=False),
        sa.Column("relationship_type", sa.String(), nullable=False),
        sa.Column("resolution_status", sa.String(), nullable=True),
        sa.Column("resolved_by_user", sa.String(), nullable=True),
        sa.Column("resolution_notes", sa.String(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_claim_id"], ["claims.id"]),
        sa.ForeignKeyConstraint(["target_claim_id"], ["claims.id"]),
    )

    # Create indices for claim_relationships table
    op.create_index(
        op.f("ix_claim_relationships_source_claim_id"), "claim_relationships", ["source_claim_id"]
    )
    op.create_index(
        op.f("ix_claim_relationships_target_claim_id"), "claim_relationships", ["target_claim_id"]
    )
    op.create_index(
        op.f("ix_claim_relationships_relationship_type"),
        "claim_relationships",
        ["relationship_type"],
    )


def downgrade() -> None:
    """Remove claims tables."""

    # Drop indices
    op.drop_index(
        op.f("ix_claim_relationships_relationship_type"), table_name="claim_relationships"
    )
    op.drop_index(op.f("ix_claim_relationships_target_claim_id"), table_name="claim_relationships")
    op.drop_index(op.f("ix_claim_relationships_source_claim_id"), table_name="claim_relationships")

    op.drop_index(op.f("ix_claim_entities_entity_id"), table_name="claim_entities")
    op.drop_index(op.f("ix_claim_entities_claim_id"), table_name="claim_entities")

    op.drop_index(op.f("ix_claims_source_document_id"), table_name="claims")
    op.drop_index(op.f("ix_claims_subject_entity_id"), table_name="claims")
    op.drop_index(op.f("ix_claims_claim_type"), table_name="claims")
    op.drop_index(op.f("ix_claims_statement"), table_name="claims")

    # Drop tables
    op.drop_table("claim_relationships")
    op.drop_table("claim_entities")
    op.drop_table("claims")
