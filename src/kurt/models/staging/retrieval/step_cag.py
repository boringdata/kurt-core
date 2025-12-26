"""CAG (Cache-Augmented Generation) retrieval step.

Single-step retrieval optimized for agent session bootstrap:
1. Embed query once → find similar entities
2. Route to topics via entity matching
3. Load context via SQL (claims, relationships, sources)
4. Format as markdown

This replaces the full RAG pipeline when you need fast, deterministic retrieval.

Input: Query from PipelineContext.metadata["query"]
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
    get_topics_for_entities,
    load_context_for_documents,
    search_entities_by_embedding,
)
from kurt.utils.retrieval.context_loading import (
    get_document_ids_from_entities,
    get_document_ids_from_topics,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


class CAGConfig(ModelConfig):
    """Configuration for CAG retrieval step."""

    top_k_entities: int = ConfigParam(
        default=5,
        ge=1,
        le=50,
        description="Number of entities to match for routing",
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
        default=30,
        ge=1,
        le=100,
        description="Maximum relationships to include in context",
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
        config: CAGConfig with top_k_entities, min_similarity, etc.

    Returns:
        Dict with rows_written and telemetry
    """
    query = ctx.metadata.get("query", "")

    if not query:
        logger.warning("No query provided in context metadata")
        return {"rows_written": 0, "error": "no_query"}

    logger.info(f"CAG retrieval for: {query[:100]}...")

    # Step 1: Embed query (single API call)
    try:
        query_embedding = generate_embeddings([query])[0]
    except Exception as e:
        logger.error(f"Failed to embed query: {e}")
        return {"rows_written": 0, "error": str(e)}

    # Step 2: Find similar entities
    top_entities = search_entities_by_embedding(
        query_embedding,
        top_k=config.top_k_entities,
        min_similarity=config.min_similarity,
    )

    matched_entities = [e.name for e, _ in top_entities]
    matched_entity_ids = [e.id for e, _ in top_entities]

    # Step 3: Get topics for these entities
    topics = get_topics_for_entities(matched_entity_ids)

    logger.info(f"Matched {len(matched_entities)} entities, {len(topics)} topics")

    # Step 4: Get document IDs from topics + entities
    doc_ids = get_document_ids_from_topics(topics)
    doc_ids.update(get_document_ids_from_entities(matched_entity_ids))

    # Step 5: Load context (SQL only)
    context_data = load_context_for_documents(
        list(doc_ids),
        matched_entities,
        topics=topics,
        max_claims=config.max_claims,
        max_entities=config.max_entities,
        max_relationships=config.max_relationships,
    )

    # Step 6: Format as markdown
    context_md = format_agent_context(query, context_data)
    token_est = estimate_tokens(context_md)

    # Build telemetry
    telemetry = {
        "topics_matched": len(topics),
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
        topics=json.dumps(topics),
        context_markdown=context_md,
        token_estimate=token_est,
        sources=json.dumps(context_data.sources),
        telemetry=json.dumps(telemetry),
    )

    result = writer.write([row])
    result.update(telemetry)
    return result
