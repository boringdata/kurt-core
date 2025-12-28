"""Graph layer models for the knowledge graph.

This layer contains models that materialize the knowledge graph from staging data.
Each model reads from staging tables and writes to graph_* tables.

Sublayers:
- entities: Entity and document-entity relationships
- claims: Claims and claim relationships
- topics: Topic clusters and document-topic relationships
"""

from kurt.models.graph.claims import (
    GraphClaimEntityRow,
    GraphClaimRow,
    claim_entities,
    claims,
)
from kurt.models.graph.entities import (
    GraphDocumentEntityRow,
    GraphEntityRow,
    document_entities,
    entities,
)
from kurt.models.graph.topics import (
    GraphDocumentTopicRow,
    GraphTopicClusterRow,
    document_topics,
    topic_clusters,
)

__all__ = [
    # Entities
    "GraphEntityRow",
    "entities",
    "GraphDocumentEntityRow",
    "document_entities",
    # Claims
    "GraphClaimRow",
    "claims",
    "GraphClaimEntityRow",
    "claim_entities",
    # Topics
    "GraphTopicClusterRow",
    "topic_clusters",
    "GraphDocumentTopicRow",
    "document_topics",
]
