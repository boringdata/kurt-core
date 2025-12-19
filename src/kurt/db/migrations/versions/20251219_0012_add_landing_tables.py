"""Add landing_discovery and landing_fetch tables for dbt-style pipeline.

Revision ID: 0012
Revises: 0011
Create Date: 2024-12-19

This migration adds:
- landing_discovery table: Tracks URL/file discovery operations
- landing_fetch table: Tracks fetch operations (content download, embedding, links)

These tables support the new dbt-style pipeline architecture with models:
- landing.discovery → landing_discovery
- landing.fetch → landing_fetch
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "012_add_landing_tables"
down_revision = "011_add_claims"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add landing tables for pipeline tracking."""

    # Create landing_discovery table
    op.create_table(
        "landing_discovery",
        # Primary key
        sa.Column("document_id", sa.String(), nullable=False),
        # Source info
        sa.Column("source_url", sa.String(), nullable=False, server_default=""),
        sa.Column("source_type", sa.String(), nullable=False, server_default="url"),
        # Discovery info
        sa.Column("discovery_method", sa.String(), nullable=False, server_default=""),
        sa.Column("discovery_url", sa.String(), nullable=True),
        # Status
        sa.Column("status", sa.String(), nullable=False, server_default="DISCOVERED"),
        sa.Column("is_new", sa.Boolean(), nullable=False, server_default="1"),
        # Metadata
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        # PipelineModelBase fields
        sa.Column("workflow_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("document_id"),
    )

    # Create indices for landing_discovery
    op.create_index(op.f("ix_landing_discovery_workflow_id"), "landing_discovery", ["workflow_id"])
    op.create_index(op.f("ix_landing_discovery_status"), "landing_discovery", ["status"])
    op.create_index(
        op.f("ix_landing_discovery_discovery_method"),
        "landing_discovery",
        ["discovery_method"],
    )
    op.create_index(op.f("ix_landing_discovery_source_type"), "landing_discovery", ["source_type"])

    # Create landing_fetch table
    op.create_table(
        "landing_fetch",
        # Primary key
        sa.Column("document_id", sa.String(), nullable=False),
        # Status
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        # Content info
        sa.Column("content_length", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("content_path", sa.String(), nullable=True),
        # Embedding info
        sa.Column("embedding_dims", sa.Integer(), nullable=False, server_default="0"),
        # Links info
        sa.Column("links_extracted", sa.Integer(), nullable=False, server_default="0"),
        # Fetch info
        sa.Column("fetch_engine", sa.String(), nullable=True),
        sa.Column("public_url", sa.String(), nullable=True),
        # Metadata
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        # PipelineModelBase fields
        sa.Column("workflow_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("document_id"),
    )

    # Create indices for landing_fetch
    op.create_index(op.f("ix_landing_fetch_workflow_id"), "landing_fetch", ["workflow_id"])
    op.create_index(op.f("ix_landing_fetch_status"), "landing_fetch", ["status"])
    op.create_index(op.f("ix_landing_fetch_fetch_engine"), "landing_fetch", ["fetch_engine"])


def downgrade() -> None:
    """Remove landing tables."""

    # Drop indices for landing_fetch
    op.drop_index(op.f("ix_landing_fetch_fetch_engine"), table_name="landing_fetch")
    op.drop_index(op.f("ix_landing_fetch_status"), table_name="landing_fetch")
    op.drop_index(op.f("ix_landing_fetch_workflow_id"), table_name="landing_fetch")

    # Drop indices for landing_discovery
    op.drop_index(op.f("ix_landing_discovery_source_type"), table_name="landing_discovery")
    op.drop_index(op.f("ix_landing_discovery_discovery_method"), table_name="landing_discovery")
    op.drop_index(op.f("ix_landing_discovery_status"), table_name="landing_discovery")
    op.drop_index(op.f("ix_landing_discovery_workflow_id"), table_name="landing_discovery")

    # Drop tables
    op.drop_table("landing_fetch")
    op.drop_table("landing_discovery")
