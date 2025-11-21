"""Document knowledge graph queries - DEPRECATED.

DEPRECATED: This module is deprecated. Use kurt.db.graph_queries.get_document_knowledge_graph() instead.
"""

# Re-export for backward compatibility
from kurt.db.graph_queries import get_document_knowledge_graph  # noqa: F401

__all__ = ["get_document_knowledge_graph"]
