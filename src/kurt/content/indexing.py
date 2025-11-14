"""Document indexing - Complete pipeline.

This is the main entry point for document indexing and knowledge graph extraction.

INDEXING WORKFLOW:
==================
1. Extract metadata + entities from documents
   → extract_document_metadata() - single document
   → batch_extract_document_metadata() - parallel batch processing

2. Finalize knowledge graph (link + resolve + create entities)
   → finalize_knowledge_graph_from_index_results()

3. Query document knowledge graph
   → get_document_knowledge_graph()

DSPy TRACES:
============
Trace #1: IndexDocument (in indexing_extract.py)
   - Extract document metadata (content_type, topics, tools, structure)
   - Extract entities with pre-resolution (EXISTING vs NEW)
   - Extract relationships between entities

Trace #2: ResolveEntityGroup (in entity_resolution.py, called by indexing_entity_resolution.py)
   - Cluster similar entities using DBSCAN
   - Resolve entity groups using LLM
   - Deduplicate and merge entities

FILE ORGANIZATION:
==================
- indexing_models.py: All Pydantic models and constants
- indexing_helpers.py: Shared utility functions (no DSPy)
- indexing_extract.py: DSPy Trace #1 - IndexDocument signature
- indexing_entity_resolution.py: Orchestration for stages 2-4 (delegates to entity_resolution.py)
- indexing_document_graph.py: Query functions (no DSPy)
- indexing.py (this file): Public API + high-level orchestration
"""

import asyncio
import logging

# Re-export document graph query
from kurt.content.indexing_document_graph import (
    get_document_knowledge_graph,
)

# Re-export entity resolution orchestration
from kurt.content.indexing_entity_resolution import (
    finalize_knowledge_graph_from_index_results,
)

# Re-export extract functions (DSPy Trace #1)
from kurt.content.indexing_extract import (
    batch_extract_document_metadata,
    extract_document_metadata,
)

# Re-export models and constants
from kurt.content.indexing_models import (
    ENTITY_TYPES,
    RELATIONSHIP_TYPES,
    DocumentMetadataOutput,
    EntityExtraction,
    EntityResolution,
    GroupResolution,
    RelationshipExtraction,
)

logger = logging.getLogger(__name__)

__all__ = [
    # Models
    "DocumentMetadataOutput",
    "EntityExtraction",
    "RelationshipExtraction",
    "EntityResolution",
    "GroupResolution",
    "ENTITY_TYPES",
    "RELATIONSHIP_TYPES",
    # Extract (Stage 1)
    "extract_document_metadata",
    "batch_extract_document_metadata",
    # Entity resolution (Stages 2-4)
    "finalize_knowledge_graph_from_index_results",
    # Query
    "get_document_knowledge_graph",
    # High-level orchestration
    "index_documents",
]


# ============================================================================
# High-Level Orchestration
# ============================================================================


def index_documents(
    document_ids: list[str],
    max_concurrent: int = 5,
    enable_kg: bool = True,
    force: bool = False,
    progress_callback: callable = None,
) -> dict:
    """
    Complete indexing pipeline orchestration.

    Runs the full 2-stage indexing workflow:
    1. Extract metadata + entities from documents (parallel)
    2. Finalize knowledge graph (link + resolve + create)

    Args:
        document_ids: List of document UUIDs to index
        max_concurrent: Max parallel extraction tasks
        enable_kg: If True, run knowledge graph finalization
        force: If True, re-index even if content unchanged
        progress_callback: Optional callback(doc_id, title, status, activity, skip_reason)

    Returns:
        {
            'extract_results': {results, errors, total, succeeded, failed, skipped},
            'kg_stats': {entities_created, entities_merged, entities_linked, relationships_created}
        }

    Example:
        >>> result = index_documents(["abc123", "def456"], max_concurrent=3)
        >>> print(f"Indexed: {result['extract_results']['succeeded']} documents")
        >>> print(f"Created: {result['kg_stats']['entities_created']} entities")
    """
    logger.info(f"Starting indexing pipeline for {len(document_ids)} documents")

    # Stage 1: Extract metadata + entities (parallel)
    logger.info("Stage 1: Extracting metadata and entities...")
    extract_results = asyncio.run(
        batch_extract_document_metadata(
            document_ids,
            max_concurrent=max_concurrent,
            force=force,
            progress_callback=progress_callback,
        )
    )

    logger.info(
        f"Stage 1 complete: {extract_results['succeeded']} succeeded, "
        f"{extract_results['failed']} failed, {extract_results['skipped']} skipped"
    )

    # Stage 2-4: Finalize knowledge graph
    kg_stats = None
    if enable_kg and extract_results["results"]:
        logger.info("Stages 2-4: Finalizing knowledge graph...")
        kg_stats = finalize_knowledge_graph_from_index_results(
            extract_results["results"], activity_callback=progress_callback
        )
        logger.info(
            f"Knowledge graph complete: {kg_stats.get('entities_created', 0)} created, "
            f"{kg_stats.get('entities_merged', 0)} merged"
        )

    return {
        "extract_results": extract_results,
        "kg_stats": kg_stats,
    }
