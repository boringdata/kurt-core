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

import numpy as np
from sqlmodel import Field

from kurt.config import ConfigParam, ModelConfig
from kurt.core import PipelineContext, PipelineModelBase, TableWriter, model, table
from kurt.db.claim_models import Claim
from kurt.db.database import get_session
from kurt.db.models import (
    Document,
    DocumentClusterEdge,
    DocumentEntity,
    Entity,
    EntityRelationship,
    TopicCluster,
)
from kurt.models.staging.clustering.step_topic_clustering import TopicClusteringRow
from kurt.utils.embeddings import bytes_to_embedding, generate_embeddings

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
# Helper Functions
# ============================================================================


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def route_to_topics(
    query_embedding: list[float],
    top_k: int,
    min_similarity: float,
) -> tuple[list[str], list[str], list]:
    """Route query to topics by finding similar entities.

    Returns:
        Tuple of (topic_names, matched_entity_names, matched_entity_ids)
    """
    session = get_session()
    query_vec = np.array(query_embedding, dtype=np.float32)

    # Load entities with embeddings
    entities = session.query(Entity).filter(Entity.embedding != b"").all()

    if not entities:
        return [], [], []

    # Compute similarities
    similarities = []
    for entity in entities:
        try:
            entity_vec = np.array(bytes_to_embedding(entity.embedding), dtype=np.float32)
            sim = cosine_similarity(query_vec, entity_vec)
            if sim >= min_similarity:
                similarities.append((entity, sim))
        except Exception:
            continue

    similarities.sort(key=lambda x: x[1], reverse=True)
    top_entities = similarities[:top_k]

    if not top_entities:
        return [], [], []

    matched_names = [e.name for e, _ in top_entities]
    matched_ids = [e.id for e, _ in top_entities]

    # Get document IDs linked to these entities
    doc_ids = (
        session.query(DocumentEntity.document_id)
        .filter(DocumentEntity.entity_id.in_(matched_ids))
        .distinct()
        .all()
    )
    doc_id_strs = [str(d.document_id) for d in doc_ids]

    # Get topics from staging table
    topics = []
    if doc_id_strs:
        topic_rows = (
            session.query(TopicClusteringRow.cluster_name)
            .filter(TopicClusteringRow.document_id.in_(doc_id_strs))
            .filter(TopicClusteringRow.cluster_name.isnot(None))
            .distinct()
            .all()
        )
        topics = [t.cluster_name for t in topic_rows if t.cluster_name]

    # Fallback to TopicCluster table
    if not topics and matched_ids:
        topic_rows = (
            session.query(TopicCluster.name)
            .distinct()
            .join(DocumentClusterEdge, TopicCluster.id == DocumentClusterEdge.cluster_id)
            .join(Document, DocumentClusterEdge.document_id == Document.id)
            .join(DocumentEntity, Document.id == DocumentEntity.document_id)
            .filter(DocumentEntity.entity_id.in_(matched_ids))
            .all()
        )
        topics = [t.name for t in topic_rows]

    return topics, matched_names, matched_ids


def load_context(
    topics: list[str],
    matched_entity_names: list[str],
    config: CAGConfig,
) -> dict:
    """Load all context for given topics from database.

    Returns dict with entities, relationships, claims, sources.
    """
    session = get_session()

    if not topics:
        return {"entities": [], "relationships": [], "claims": [], "sources": []}

    # Get document IDs in these topics
    doc_id_rows = (
        session.query(TopicClusteringRow.document_id)
        .filter(TopicClusteringRow.cluster_name.in_(topics))
        .distinct()
        .all()
    )
    doc_ids_str = [row.document_id for row in doc_id_rows]

    try:
        from uuid import UUID

        doc_ids = [UUID(did) for did in doc_ids_str]
    except (ValueError, TypeError):
        doc_ids = []

    # Fallback to TopicCluster table
    if not doc_ids:
        doc_id_rows = (
            session.query(DocumentClusterEdge.document_id)
            .join(TopicCluster, DocumentClusterEdge.cluster_id == TopicCluster.id)
            .filter(TopicCluster.name.in_(topics))
            .distinct()
            .all()
        )
        doc_ids = [row.document_id for row in doc_id_rows]

    if not doc_ids:
        return {"entities": [], "relationships": [], "claims": [], "sources": []}

    # Load entities
    entity_rows = (
        session.query(Entity)
        .join(DocumentEntity, Entity.id == DocumentEntity.entity_id)
        .filter(DocumentEntity.document_id.in_(doc_ids))
        .distinct()
        .all()
    )

    def entity_sort_key(e):
        is_matched = e.name in matched_entity_names
        return (not is_matched, -e.source_mentions)

    entity_rows.sort(key=entity_sort_key)
    entity_rows = entity_rows[: config.max_entities]

    entities = [
        {
            "name": e.name,
            "type": e.entity_type,
            "description": e.description or "",
            "matched": e.name in matched_entity_names,
        }
        for e in entity_rows
    ]

    entity_ids = [e.id for e in entity_rows]

    # Load relationships
    relationships = []
    if entity_ids:
        rel_rows = (
            session.query(EntityRelationship, Entity)
            .join(Entity, EntityRelationship.target_entity_id == Entity.id)
            .filter(
                EntityRelationship.source_entity_id.in_(entity_ids),
                EntityRelationship.target_entity_id.in_(entity_ids),
            )
            .order_by(EntityRelationship.confidence.desc())
            .limit(config.max_relationships)
            .all()
        )

        entity_id_to_name = {e.id: e.name for e in entity_rows}

        for rel, target_entity in rel_rows:
            source_name = entity_id_to_name.get(rel.source_entity_id, "?")
            relationships.append(
                {
                    "source": source_name,
                    "type": rel.relationship_type,
                    "target": target_entity.name,
                }
            )

    # Load claims
    claim_rows = (
        session.query(Claim, Entity, Document)
        .join(Entity, Claim.subject_entity_id == Entity.id)
        .join(Document, Claim.source_document_id == Document.id)
        .filter(Claim.source_document_id.in_(doc_ids))
        .order_by(Claim.overall_confidence.desc())
        .limit(config.max_claims)
        .all()
    )

    claims = [
        {
            "statement": c.statement,
            "type": c.claim_type.value if hasattr(c.claim_type, "value") else str(c.claim_type),
            "confidence": c.overall_confidence,
            "entity": e.name,
            "source_doc_title": d.title or "",
        }
        for c, e, d in claim_rows
    ]

    # Load sources
    doc_rows = (
        session.query(Document.id, Document.title, Document.source_url)
        .filter(Document.id.in_(doc_ids))
        .all()
    )

    sources = [
        {"doc_id": str(d.id), "title": d.title or "Untitled", "url": d.source_url or ""}
        for d in doc_rows
    ]

    return {
        "entities": entities,
        "relationships": relationships,
        "claims": claims,
        "sources": sources,
    }


def format_markdown(query: str, topics: list[str], context: dict) -> str:
    """Format context as markdown for agent system prompt."""
    lines = [
        "# Knowledge Context",
        "",
        f"**Query:** {query}",
        f"**Topics:** {', '.join(topics) if topics else 'None matched'}",
        "",
        f"*Retrieved: {len(context['entities'])} entities, "
        f"{len(context['relationships'])} relationships, "
        f"{len(context['claims'])} claims from {len(context['sources'])} documents*",
        "",
    ]

    # Entities section
    lines.append("## Knowledge Graph")
    lines.append("")
    lines.append("### Entities")

    matched = [e for e in context["entities"] if e.get("matched")]
    other = [e for e in context["entities"] if not e.get("matched")]

    if matched:
        lines.append("")
        lines.append("**Matched from query:**")
        for e in matched:
            desc = f": {e['description'][:100]}..." if e["description"] else ""
            lines.append(f"- **{e['name']}** ({e['type']}){desc}")

    if other:
        lines.append("")
        lines.append("**Related entities:**")
        for e in other[:20]:
            desc = f": {e['description'][:80]}..." if e["description"] else ""
            lines.append(f"- {e['name']} ({e['type']}){desc}")

    lines.append("")

    # Relationships
    if context["relationships"]:
        lines.append("### Relationships")
        for r in context["relationships"]:
            lines.append(f"- {r['source']} --[{r['type']}]--> {r['target']}")
        lines.append("")

    # Claims
    if context["claims"]:
        lines.append("## Claims")
        lines.append("")

        claims_by_entity: dict = {}
        for claim in context["claims"]:
            entity = claim["entity"]
            if entity not in claims_by_entity:
                claims_by_entity[entity] = []
            claims_by_entity[entity].append(claim)

        for entity, entity_claims in claims_by_entity.items():
            lines.append(f"### {entity}")
            for claim in entity_claims[:5]:
                conf = claim["confidence"]
                source = claim["source_doc_title"]
                source_ref = f" → [{source}]" if source else ""
                lines.append(f"- {claim['statement']} [conf: {conf:.2f}]{source_ref}")
            lines.append("")

    # Sources
    if context["sources"]:
        lines.append("## Sources")
        lines.append("")
        for i, src in enumerate(context["sources"], 1):
            if src["url"]:
                lines.append(f"[{i}] {src['title']} - {src['url']}")
            else:
                lines.append(f"[{i}] {src['title']}")

    return "\n".join(lines)


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

    # Step 2: Route to topics via entity similarity
    topics, matched_entities, _ = route_to_topics(
        query_embedding,
        top_k=config.top_k_entities,
        min_similarity=config.min_similarity,
    )

    logger.info(f"Matched {len(matched_entities)} entities, {len(topics)} topics")

    # Step 3: Load context (SQL only)
    context = load_context(topics, matched_entities, config)

    # Step 4: Format as markdown
    context_md = format_markdown(query, topics, context)
    token_estimate = len(context_md) // 4

    # Build telemetry
    telemetry = {
        "topics_matched": len(topics),
        "entities_matched": len(matched_entities),
        "entities_loaded": len(context["entities"]),
        "relationships_loaded": len(context["relationships"]),
        "claims_loaded": len(context["claims"]),
        "sources_loaded": len(context["sources"]),
        "token_estimate": token_estimate,
    }

    logger.info(f"CAG complete: {token_estimate} tokens, {len(context['claims'])} claims")

    # Write result
    row = CAGContextRow(
        query_id=ctx.workflow_id,
        query=query,
        matched_entities=json.dumps(matched_entities),
        topics=json.dumps(topics),
        context_markdown=context_md,
        token_estimate=token_estimate,
        sources=json.dumps(context["sources"]),
        telemetry=json.dumps(telemetry),
    )

    result = writer.write([row])
    result.update(telemetry)
    return result
