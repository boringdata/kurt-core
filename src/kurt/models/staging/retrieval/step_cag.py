"""CAG (Cache-Augmented Generation) retrieval step.

Single-step retrieval optimized for agent session bootstrap:
1. Parse comma-separated entity terms (e.g., "Parquet, CSV, data loading")
2. Embed all terms at once (single API call)
3. For each term, find similar entities and merge results
4. Get documents linked to matched entities
5. Load context via SQL (claims, relationships, sources)
6. Format as markdown

This replaces the full RAG pipeline when you need fast, deterministic retrieval.

Input: Query from PipelineContext.metadata["query"]
       - Comma-separated: "entity1, entity2, entity3" - searches each separately
       - Single string: "full query" - embeds entire query
Output table: retrieval_cag_context
"""

import json
import logging

from sqlmodel import Field

from kurt.config import ConfigParam, ModelConfig
from kurt.core import PipelineContext, PipelineModelBase, TableWriter, model, table
from kurt.utils.embeddings import generate_embeddings
from kurt.utils.retrieval import (
    estimate_tokens,
    format_agent_context,
    load_context_for_documents,
    search_entities_by_embedding,
)
from kurt.utils.retrieval.context_loading import (
    get_document_ids_from_entities,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


class CAGConfig(ModelConfig):
    """Configuration for CAG retrieval step."""

    top_k_per_term: int = ConfigParam(
        default=3,
        ge=1,
        le=10,
        description="Number of similar entities to match per search term",
    )
    min_similarity: float = ConfigParam(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold for entity matching",
    )
    max_claims: int = ConfigParam(
        default=50,
        ge=1,
        le=200,
        description="Maximum claims to include in context",
    )
    max_entities: int = ConfigParam(
        default=50,
        ge=1,
        le=200,
        description="Maximum entities to include in context",
    )
    max_relationships: int = ConfigParam(
        default=200,
        ge=1,
        le=500,
        description="Maximum relationships to include in context (relationships are compact)",
    )


# ============================================================================
# Output Schema
# ============================================================================


class CAGContextRow(PipelineModelBase, table=True):
    """Output schema for CAG retrieval step."""

    __tablename__ = "retrieval_cag_context"

    query_id: str = Field(primary_key=True)
    query: str

    # Routing results
    matched_entities: str  # JSON list
    topics: str  # JSON list

    # Context output
    context_markdown: str
    token_estimate: int

    # Sources
    sources: str  # JSON list of {doc_id, title, url}

    # Telemetry
    telemetry: str  # JSON dict


# ============================================================================
# Pipeline Step
# ============================================================================


@model(
    name="retrieval.cag",
    primary_key=["query_id"],
    description="CAG retrieval: entity routing + SQL context loading",
    config_schema=CAGConfig,
)
@table(CAGContextRow)
def cag_retrieve(
    ctx: PipelineContext,
    writer: TableWriter,
    config: CAGConfig = None,
):
    """CAG retrieval step for agent session bootstrap.

    Single-step retrieval that:
    1. Embeds query once
    2. Routes to topics via entity similarity
    3. Loads context via SQL (no LLM)
    4. Formats as markdown

    Args:
        ctx: Pipeline context with query in metadata["query"]
        writer: TableWriter for output
        config: CAGConfig with top_k_per_term, min_similarity, etc.

    Returns:
        Dict with rows_written and telemetry
    """
    query = ctx.metadata.get("query", "")

    if not query:
        logger.warning("No query provided in context metadata")
        return {"rows_written": 0, "error": "no_query"}

    logger.info(f"CAG retrieval for: {query[:100]}...")

    # Step 1: Parse comma-separated entity terms
    # If query contains commas, treat as list of entities to search
    if "," in query:
        search_terms = [t.strip() for t in query.split(",") if t.strip()]
    else:
        # Single term or space-separated (backwards compat)
        search_terms = [query]

    logger.info(f"Searching for {len(search_terms)} terms: {search_terms}")

    # Step 2: Embed all terms at once (single API call for efficiency)
    try:
        term_embeddings = generate_embeddings(search_terms)
    except Exception as e:
        logger.error(f"Failed to embed terms: {e}")
        return {"rows_written": 0, "error": str(e)}

    # Step 3: For each term, find similar entities and merge results
    entity_scores: dict[str, tuple] = {}  # entity_id -> (entity, max_similarity, term)

    for term, term_embedding in zip(search_terms, term_embeddings):
        term_matches = search_entities_by_embedding(
            term_embedding,
            top_k=config.top_k_per_term,
            min_similarity=config.min_similarity,
        )

        logger.debug(f"Term '{term}': {len(term_matches)} matches")

        # Merge: keep highest similarity per entity
        for entity, sim in term_matches:
            eid = str(entity.id)
            if eid not in entity_scores or sim > entity_scores[eid][1]:
                entity_scores[eid] = (entity, sim, term)

    # Sort by similarity and build final list
    sorted_entities = sorted(entity_scores.values(), key=lambda x: x[1], reverse=True)
    matched_entities = [e.name for e, _, _ in sorted_entities]
    matched_entity_ids = [e.id for e, _, _ in sorted_entities]

    logger.info(f"Merged: {len(matched_entities)} unique entities from {len(search_terms)} terms")

    # Step 4: Get document IDs from entities
    doc_ids = get_document_ids_from_entities(matched_entity_ids)

    logger.info(f"Found {len(doc_ids)} documents for {len(matched_entities)} entities")

    # Step 5: Load context (SQL only)
    context_data = load_context_for_documents(
        list(doc_ids),
        matched_entities,
        topics=[],
        max_claims=config.max_claims,
        max_entities=config.max_entities,
        max_relationships=config.max_relationships,
    )

    # Step 6: Format as markdown
    context_md = format_agent_context(query, context_data)
    token_est = estimate_tokens(context_md)

    # Build telemetry
    telemetry = {
        "search_terms": len(search_terms),
        "entities_matched": len(matched_entities),
        "entities_loaded": len(context_data.entities),
        "relationships_loaded": len(context_data.relationships),
        "claims_loaded": len(context_data.claims),
        "sources_loaded": len(context_data.sources),
        "token_estimate": token_est,
    }

    logger.info(f"CAG complete: {token_est} tokens, {len(context_data.claims)} claims")

    # Write result
    row = CAGContextRow(
        query_id=ctx.workflow_id,
        query=query,
        matched_entities=json.dumps(matched_entities),
        topics=json.dumps(search_terms),  # Store search terms instead of topics
        context_markdown=context_md,
        token_estimate=token_est,
        sources=json.dumps(context_data.sources),
        telemetry=json.dumps(telemetry),
    )

    result = writer.write([row])
    result.update(telemetry)
    return result
