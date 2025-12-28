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
    # Graph Layer - Knowledge graph
    # Legacy tables (still used by existing models, will be migrated)
    # =========================================================================
    GRAPH_ENTITIES = "entities"  # Legacy: use GRAPH_ENTITIES_NEW for new models
    GRAPH_DOCUMENT_ENTITIES = "document_entities"  # Legacy
    GRAPH_ENTITY_RELATIONSHIPS = "entity_relationships"  # Legacy
    GRAPH_DOCUMENT_ENTITY_RELATIONSHIPS = "document_entity_relationships"  # Legacy
    GRAPH_CLAIMS = "claims"  # Legacy: use GRAPH_CLAIMS_NEW for new models
    GRAPH_CLAIM_ENTITIES = "claim_entities"  # Legacy
    GRAPH_CLAIM_RELATIONSHIPS = "claim_relationships"  # Legacy
    GRAPH_TOPIC_CLUSTERS = "topic_clusters"  # Legacy: use GRAPH_TOPIC_CLUSTERS_NEW
    GRAPH_DOCUMENT_CLUSTER_EDGES = "document_cluster_edges"  # Legacy

    # =========================================================================
    # Graph Layer - New model-based tables (will replace legacy tables)
    # =========================================================================
    GRAPH_ENTITIES_NEW = "graph_entities_new"
    GRAPH_DOCUMENT_ENTITIES_NEW = "graph_document_entities_new"
    GRAPH_CLAIMS_NEW = "graph_claims_new"
    GRAPH_CLAIM_ENTITIES_NEW = "graph_claim_entities_new"
    GRAPH_TOPIC_CLUSTERS_NEW = "graph_topic_clusters_new"
    GRAPH_DOCUMENT_TOPICS_NEW = "graph_document_topics_new"

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
