"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2025-10-29 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import JSON

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("content_path", sa.String(), nullable=True),
        sa.Column("ingestion_status", sa.String(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("author", JSON(), nullable=True),
        sa.Column("published_date", sa.DateTime(), nullable=True),
        sa.Column("is_chronological", sa.Boolean(), nullable=True),
        sa.Column("discovery_method", sa.String(), nullable=True),
        sa.Column("discovery_url", sa.String(), nullable=True),
        sa.Column("indexed_with_hash", sa.String(), nullable=True),
        sa.Column("indexed_with_git_commit", sa.String(), nullable=True),
        sa.Column("content_type", sa.String(), nullable=True),
        sa.Column("primary_topics", JSON(), nullable=True),
        sa.Column("tools_technologies", JSON(), nullable=True),
        sa.Column("has_code_examples", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("has_step_by_step_procedures", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("has_narrative_structure", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for documents
    op.create_index("ix_documents_source_url", "documents", ["source_url"], unique=True)
    op.create_index("ix_documents_indexed_with_hash", "documents", ["indexed_with_hash"])
    op.create_index(
        "ix_documents_indexed_with_git_commit", "documents", ["indexed_with_git_commit"]
    )
    op.create_index("ix_documents_content_type", "documents", ["content_type"])

    # Create topic_clusters table
    op.create_table(
        "topic_clusters",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create index for topic_clusters
    op.create_index("ix_topic_clusters_name", "topic_clusters", ["name"])

    # Create entities table
    op.create_table(
        "entities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for entities
    op.create_index("ix_entities_name", "entities", ["name"])
    op.create_index("ix_entities_entity_type", "entities", ["entity_type"])

    # Create document_cluster_edges table (junction table)
    op.create_table(
        "document_cluster_edges",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("cluster_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["cluster_id"],
            ["topic_clusters.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for document_cluster_edges
    op.create_index(
        "ix_document_cluster_edges_document_id", "document_cluster_edges", ["document_id"]
    )
    op.create_index(
        "ix_document_cluster_edges_cluster_id", "document_cluster_edges", ["cluster_id"]
    )


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_index("ix_document_cluster_edges_cluster_id", "document_cluster_edges")
    op.drop_index("ix_document_cluster_edges_document_id", "document_cluster_edges")
    op.drop_table("document_cluster_edges")

    op.drop_index("ix_entities_entity_type", "entities")
    op.drop_index("ix_entities_name", "entities")
    op.drop_table("entities")

    op.drop_index("ix_topic_clusters_name", "topic_clusters")
    op.drop_table("topic_clusters")

    op.drop_index("ix_documents_content_type", "documents")
    op.drop_index("ix_documents_indexed_with_git_commit", "documents")
    op.drop_index("ix_documents_indexed_with_hash", "documents")
    op.drop_index("ix_documents_source_url", "documents")
    op.drop_table("documents")
