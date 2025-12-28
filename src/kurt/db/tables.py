"""Centralized table name constants.

This module provides a single source of truth for all table names in Kurt.
Use these constants instead of hardcoding table names in:
- Model __tablename__ attributes
- Raw SQL queries
- Table existence checks

This enables safe table renaming via migrations without scatter changes.
"""


class TableNames:
    """Table name constants organized by layer."""

    # =========================================================================
    # Landing Layer - Raw data ingestion
    # =========================================================================
    LANDING_DISCOVERY = "landing_discovery"
    LANDING_FETCH = "landing_fetch"

    # =========================================================================
    # Staging Layer - Transformation & enrichment
    # =========================================================================

    # Indexing pipeline
    STAGING_DOCUMENT_SECTIONS = "staging_document_sections"
    STAGING_SECTION_EXTRACTIONS = "staging_section_extractions"
    STAGING_ENTITY_CLUSTERING = "staging_entity_clustering"
    STAGING_ENTITY_RESOLUTION = "staging_entity_resolution"
    STAGING_CLAIM_CLUSTERING = "staging_claim_clustering"
    STAGING_CLAIM_RESOLUTION = "staging_claim_resolution"

    # Clustering pipeline
    STAGING_TOPIC_CLUSTERING = "staging_topic_clustering"

    # =========================================================================
    # Graph Layer - Knowledge graph (future: models own these)
    # =========================================================================
    GRAPH_ENTITIES = "entities"  # TODO: rename to "graph_entities"
    GRAPH_DOCUMENT_ENTITIES = "document_entities"  # TODO: rename to "graph_document_entities"
    GRAPH_ENTITY_RELATIONSHIPS = "entity_relationships"  # TODO: rename
    GRAPH_DOCUMENT_ENTITY_RELATIONSHIPS = "document_entity_relationships"  # TODO: rename
    GRAPH_CLAIMS = "claims"  # TODO: rename to "graph_claims"
    GRAPH_CLAIM_ENTITIES = "claim_entities"  # TODO: rename
    GRAPH_CLAIM_RELATIONSHIPS = "claim_relationships"  # TODO: rename
    GRAPH_TOPIC_CLUSTERS = "topic_clusters"  # TODO: rename to "graph_topic_clusters"
    GRAPH_DOCUMENT_CLUSTER_EDGES = "document_cluster_edges"  # TODO: rename

    # =========================================================================
    # Retrieval Layer - Query-time computed data
    # =========================================================================
    RETRIEVAL_RAG_CONTEXT = "retrieval_rag_context"
    RETRIEVAL_CAG_CONTEXT = "retrieval_cag_context"

    # =========================================================================
    # Core Tables - Identity and metadata
    # =========================================================================
    DOCUMENTS = "documents"
    DOCUMENT_LINKS = "document_links"
    METADATA_SYNC_QUEUE = "metadata_sync_queue"
    PAGE_ANALYTICS = "page_analytics"
    ANALYTICS_DOMAINS = "analytics_domains"


# Convenience aliases for common access patterns
Tables = TableNames
