"""Rename graph tables to follow layer naming convention

Revision ID: 013_rename_graph_tables
Revises: 012_add_section_tracking
Create Date: 2025-12-29

This migration renames graph layer tables to follow the {layer}_{object} convention:
- entities -> graph_entities
- document_entities -> graph_document_entities
- entity_relationships -> graph_entity_relationships
- document_entity_relationships -> graph_document_entity_relationships
- claims -> graph_claims
- claim_entities -> graph_claim_entities
- claim_relationships -> graph_claim_relationships
- topic_clusters -> graph_topic_clusters
- document_cluster_edges -> graph_document_topics
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013_rename_graph_tables"
down_revision: Union[str, None] = "012_add_section_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Table rename mapping: old_name -> new_name
TABLE_RENAMES = [
    ("entities", "graph_entities"),
    ("document_entities", "graph_document_entities"),
    ("entity_relationships", "graph_entity_relationships"),
    ("document_entity_relationships", "graph_document_entity_relationships"),
    ("claims", "graph_claims"),
    ("claim_entities", "graph_claim_entities"),
    ("claim_relationships", "graph_claim_relationships"),
    ("topic_clusters", "graph_topic_clusters"),
    ("document_cluster_edges", "graph_document_topics"),
]


def upgrade() -> None:
    """Rename graph tables to use graph_ prefix."""
    for old_name, new_name in TABLE_RENAMES:
        op.rename_table(old_name, new_name)


def downgrade() -> None:
    """Revert table names to original."""
    for old_name, new_name in TABLE_RENAMES:
        op.rename_table(new_name, old_name)
