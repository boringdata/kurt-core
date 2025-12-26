"""Unified RAG (Retrieval-Augmented Generation) step.

Single-step retrieval that combines multiple search strategies:
1. Embed query once (shared across all searches)
2. Entity-based graph search
3. Semantic document search
4. Claim search with entity boost
5. Merge results with RRF
6. Format context

This replaces the 7-step RAG pipeline with a single unified step.

Input: Query from PipelineContext.metadata["query"]
Output table: retrieval_rag_context
"""

import json
import logging

from sqlmodel import Field

from kurt.config import ConfigParam, ModelConfig
from kurt.core import PipelineContext, PipelineModelBase, TableWriter, model, table
from kurt.utils.embeddings import generate_embeddings
from kurt.utils.retrieval import (
    claim_search_with_boost,
    extract_entities_from_query,
    format_rag_context,
    graph_search,
    reciprocal_rank_fusion,
    semantic_search,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


class RAGConfig(ModelConfig):
    """Configuration for unified RAG retrieval step."""

    # Search limits
    semantic_top_k: int = ConfigParam(
        default=10,
        ge=1,
        le=100,
        description="Top documents from semantic search",
    )
    graph_top_k: int = ConfigParam(
        default=20,
        ge=1,
        le=100,
        description="Top documents from graph search",
    )
    claim_top_k: int = ConfigParam(
        default=15,
        ge=1,
        le=100,
        description="Top claims to retrieve",
    )

    # Thresholds
    min_similarity: float = ConfigParam(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold",
    )

    # Limits
    max_documents: int = ConfigParam(
        default=500,
        ge=10,
        le=2000,
        description="Max documents to search",
    )
    max_claims: int = ConfigParam(
        default=500,
        ge=10,
        le=2000,
        description="Max claims to search",
    )


# ============================================================================
# Output Schema
# ============================================================================


class RAGContextRow(PipelineModelBase, table=True):
    """Output schema for unified RAG retrieval step."""

    __tablename__ = "retrieval_rag_context"

    query_id: str = Field(primary_key=True)
    query: str

    # Context output
    context_text: str

    # Ranked results
    doc_ids: str  # JSON list
    entities: str  # JSON list
    claims: str  # JSON list
    citations: str  # JSON list of {doc_id, title, url, score}

    # Telemetry
    telemetry: str  # JSON dict


# ============================================================================
# Pipeline Step
# ============================================================================


@model(
    name="retrieval.rag",
    primary_key=["query_id"],
    description="Unified RAG: multi-signal search with RRF fusion",
    config_schema=RAGConfig,
)
@table(RAGContextRow)
def rag_retrieve(
    ctx: PipelineContext,
    writer: TableWriter,
    config: RAGConfig = None,
):
    """Unified RAG retrieval step.

    Single-step retrieval that:
    1. Embeds query once (shared across all searches)
    2. Runs graph search (entity-based)
    3. Runs semantic search (embedding similarity)
    4. Runs claim search (semantic + entity boost)
    5. Merges results with RRF
    6. Formats context

    Args:
        ctx: Pipeline context with query in metadata["query"]
        writer: TableWriter for output
        config: RAGConfig with search limits and thresholds

    Returns:
        Dict with rows_written and telemetry
    """
    query = ctx.metadata.get("query", "")

    if not query:
        logger.warning("No query provided in context metadata")
        return {"rows_written": 0, "error": "no_query"}

    logger.info(f"RAG retrieval for: {query[:100]}...")

    # Step 1: Embed query ONCE (shared across all searches)
    try:
        query_embedding = generate_embeddings([query])[0]
    except Exception as e:
        logger.error(f"Failed to embed query: {e}")
        return {"rows_written": 0, "error": str(e)}

    # Step 2: Extract entities from query (using embedding similarity)
    entities = extract_entities_from_query(query, query_embedding)
    logger.info(f"Extracted {len(entities)} entities: {entities[:5]}")

    # Step 3: Run searches in sequence (could be parallelized)
    # Graph search
    graph_results = graph_search(entities, config.graph_top_k)
    graph_ranking = [doc_id for doc_id, _, _, _ in graph_results]

    # Semantic search
    semantic_results = semantic_search(
        query_embedding,
        config.semantic_top_k,
        config.min_similarity,
        config.max_documents,
    )
    semantic_ranking = [doc_id for doc_id, _, _, _ in semantic_results]

    # Claim search
    claims = claim_search_with_boost(
        query_embedding,
        entities,
        config.claim_top_k,
        config.max_claims,
    )
    claim_doc_ranking = list(dict.fromkeys([c["doc_id"] for c in claims]))

    logger.info(
        f"Search results: {len(graph_ranking)} graph, "
        f"{len(semantic_ranking)} semantic, {len(claims)} claims"
    )

    # Step 4: Merge with RRF
    rankings = [r for r in [graph_ranking, semantic_ranking, claim_doc_ranking] if r]
    ranked_docs = reciprocal_rank_fusion(rankings) if rankings else []

    # Collect all entities and relationships
    all_entities = list(entities)
    all_relationships = []
    for _, _, ents, rels in graph_results:
        all_entities.extend(ents)
        all_relationships.extend(rels)

    # Build document metadata
    doc_metadata = {}
    for doc_id, sim, title, url in semantic_results:
        doc_metadata[doc_id] = {"title": title, "url": url}
    for doc_id, _, ents, _ in graph_results:
        if doc_id not in doc_metadata:
            doc_metadata[doc_id] = {"title": "", "url": ""}

    # Step 5: Format context
    context_text = format_rag_context(
        query,
        ranked_docs,
        all_entities,
        all_relationships,
        claims,
        doc_metadata,
    )

    # Build citations
    citations = [
        {
            "doc_id": doc_id,
            "title": doc_metadata.get(doc_id, {}).get("title", ""),
            "url": doc_metadata.get(doc_id, {}).get("url", ""),
            "score": score,
        }
        for doc_id, score in ranked_docs[:20]
    ]

    # Telemetry
    telemetry = {
        "graph_results": len(graph_ranking),
        "semantic_results": len(semantic_ranking),
        "claims": len(claims),
        "merged_docs": len(ranked_docs),
        "entities": len(set(all_entities)),
        "relationships": len(all_relationships),
    }

    logger.info(f"RAG complete: {len(ranked_docs)} docs, {len(claims)} claims")

    # Write result
    row = RAGContextRow(
        query_id=ctx.workflow_id,
        query=query,
        context_text=context_text,
        doc_ids=json.dumps([doc_id for doc_id, _ in ranked_docs]),
        entities=json.dumps(list(set(all_entities))),
        claims=json.dumps(claims),
        citations=json.dumps(citations),
        telemetry=json.dumps(telemetry),
    )

    result = writer.write([row])
    result.update(telemetry)
    return result
