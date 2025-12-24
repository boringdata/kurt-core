"""CAG (Cache-Augmented Generation) retrieval for agent sessions.

This module provides a simplified retrieval approach optimized for bootstrapping
agent sessions. Instead of the full RAG pipeline (query analysis → 5 parallel
searches → RRF fusion), CAG uses:

1. Single embedding call to find similar entities
2. SQL-only context loading (no LLM calls)
3. Markdown formatting for agent system prompt

The result is faster, more deterministic retrieval suitable for agent bootstrap.

Usage:
    from kurt.retrieval.cag import retrieve_cag

    result = await retrieve_cag("How does Segment handle identity resolution?")
    print(result.context_markdown)  # Ready for agent system prompt
"""

import logging
from dataclasses import dataclass, field
from uuid import UUID

import numpy as np

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
# Types
# ============================================================================


@dataclass
class TopicContextData:
    """All context for a topic, ready to format."""

    topics: list[str]
    entities: list[dict]  # {name, type, description}
    relationships: list[dict]  # {source, type, target}
    claims: list[dict]  # {statement, confidence, type, source_doc}
    sources: list[dict]  # {doc_id, title, url}


@dataclass
class CAGResult:
    """Output from CAG retrieval.

    Attributes:
        query: Original query
        topics: Topics matched for this query
        context_markdown: Formatted context ready for agent system prompt
        token_estimate: Estimated token count
        sources: List of source documents
        telemetry: Performance metrics
    """

    query: str
    topics: list[str] = field(default_factory=list)
    matched_entities: list[str] = field(default_factory=list)
    context_markdown: str = ""
    token_estimate: int = 0
    sources: list[dict] = field(default_factory=list)
    telemetry: dict = field(default_factory=dict)


# ============================================================================
# Entity Similarity Routing
# ============================================================================


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def route_to_topics_via_entities(
    query: str,
    top_k_entities: int = 5,
    min_similarity: float = 0.3,
) -> tuple[list[str], list[str]]:
    """Route query to topics by finding similar entities.

    This is the core CAG routing:
    1. Embed the query (single API call)
    2. Find similar entities via vector search
    3. Get topics containing documents that mention those entities

    Args:
        query: User query
        top_k_entities: Max entities to match
        min_similarity: Minimum similarity threshold

    Returns:
        Tuple of (topic_names, matched_entity_names)
    """
    session = get_session()

    # Step 1: Embed query (single API call)
    logger.info("Embedding query for entity matching...")
    query_embedding = generate_embeddings([query])[0]
    query_vec = np.array(query_embedding, dtype=np.float32)

    # Step 2: Load all entities with embeddings
    entities = session.query(Entity).filter(Entity.embedding != b"").all()

    if not entities:
        logger.warning("No entities with embeddings found")
        return [], []

    # Step 3: Compute similarities
    similarities = []
    for entity in entities:
        try:
            entity_vec = np.array(bytes_to_embedding(entity.embedding), dtype=np.float32)
            sim = cosine_similarity(query_vec, entity_vec)
            if sim >= min_similarity:
                similarities.append((entity, sim))
        except Exception as e:
            logger.debug(f"Failed to compute similarity for {entity.name}: {e}")
            continue

    # Sort by similarity and take top_k
    similarities.sort(key=lambda x: x[1], reverse=True)
    top_entities = similarities[:top_k_entities]

    if not top_entities:
        logger.info("No entities matched above similarity threshold")
        return [], []

    matched_entity_names = [e.name for e, _ in top_entities]
    matched_entity_ids = [e.id for e, _ in top_entities]

    logger.info(
        f"Matched {len(top_entities)} entities: "
        f"{', '.join(f'{e.name} ({s:.2f})' for e, s in top_entities[:3])}..."
    )

    # Step 4: Get topics for these entities
    # First get document IDs from DocumentEntity
    doc_ids_with_entities = (
        session.query(DocumentEntity.document_id)
        .filter(DocumentEntity.entity_id.in_(matched_entity_ids))
        .distinct()
        .all()
    )
    doc_id_strs = [str(d.document_id) for d in doc_ids_with_entities]

    # Then get topics for those documents from staging table
    if doc_id_strs:
        topic_names = (
            session.query(TopicClusteringRow.cluster_name)
            .filter(TopicClusteringRow.document_id.in_(doc_id_strs))
            .filter(TopicClusteringRow.cluster_name.isnot(None))
            .distinct()
            .all()
        )
        topics = [t.cluster_name for t in topic_names if t.cluster_name]
    else:
        topics = []

    # Fallback: try via TopicCluster directly if staging table empty
    if not topics:
        topic_names = (
            session.query(TopicCluster.name)
            .distinct()
            .join(DocumentClusterEdge, TopicCluster.id == DocumentClusterEdge.cluster_id)
            .join(Document, DocumentClusterEdge.document_id == Document.id)
            .join(DocumentEntity, Document.id == DocumentEntity.document_id)
            .filter(DocumentEntity.entity_id.in_(matched_entity_ids))
            .all()
        )
        topics = [t.name for t in topic_names]

    logger.info(f"Routed to {len(topics)} topics: {topics[:3]}...")

    return topics, matched_entity_names


# ============================================================================
# Context Loading (SQL only, no LLM)
# ============================================================================


def load_topic_context(
    topics: list[str],
    matched_entity_names: list[str],
    max_claims: int = 50,
    max_entities: int = 50,
    max_relationships: int = 30,
) -> TopicContextData:
    """Load all context for given topics from database.

    Pure SQL - no LLM calls, no embeddings.

    Args:
        topics: List of topic names to load
        matched_entity_names: Entity names that matched the query
        max_claims: Maximum claims to include
        max_entities: Maximum entities to include
        max_relationships: Maximum relationships to include

    Returns:
        TopicContextData with all context
    """
    session = get_session()

    if not topics:
        return TopicContextData(
            topics=[],
            entities=[],
            relationships=[],
            claims=[],
            sources=[],
        )

    # Get document IDs in these topics (from staging table)
    doc_id_rows = (
        session.query(TopicClusteringRow.document_id)
        .filter(TopicClusteringRow.cluster_name.in_(topics))
        .distinct()
        .all()
    )

    doc_ids_str = [row.document_id for row in doc_id_rows]

    # Convert to UUIDs for queries
    try:
        doc_ids = [UUID(did) for did in doc_ids_str]
    except (ValueError, TypeError):
        doc_ids = []

    if not doc_ids:
        # Fallback to TopicCluster table
        doc_id_rows = (
            session.query(DocumentClusterEdge.document_id)
            .join(TopicCluster, DocumentClusterEdge.cluster_id == TopicCluster.id)
            .filter(TopicCluster.name.in_(topics))
            .distinct()
            .all()
        )
        doc_ids = [row.document_id for row in doc_id_rows]

    logger.info(f"Found {len(doc_ids)} documents in topics")

    if not doc_ids:
        return TopicContextData(
            topics=topics,
            entities=[],
            relationships=[],
            claims=[],
            sources=[],
        )

    # Load entities linked to these documents
    # Prioritize matched entities first
    entity_rows = (
        session.query(Entity)
        .join(DocumentEntity, Entity.id == DocumentEntity.entity_id)
        .filter(DocumentEntity.document_id.in_(doc_ids))
        .distinct()
        .all()
    )

    # Sort: matched entities first, then by source_mentions
    def entity_sort_key(e):
        is_matched = e.name in matched_entity_names
        return (not is_matched, -e.source_mentions)

    entity_rows.sort(key=entity_sort_key)
    entity_rows = entity_rows[:max_entities]

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

    # Load relationships between these entities
    if entity_ids:
        rel_rows = (
            session.query(EntityRelationship, Entity)
            .join(Entity, EntityRelationship.target_entity_id == Entity.id)
            .filter(
                EntityRelationship.source_entity_id.in_(entity_ids),
                EntityRelationship.target_entity_id.in_(entity_ids),
            )
            .order_by(EntityRelationship.confidence.desc())
            .limit(max_relationships)
            .all()
        )

        # Build entity ID to name map
        entity_id_to_name = {e.id: e.name for e in entity_rows}

        relationships = []
        for rel, target_entity in rel_rows:
            source_name = entity_id_to_name.get(rel.source_entity_id, "?")
            relationships.append(
                {
                    "source": source_name,
                    "type": rel.relationship_type,
                    "target": target_entity.name,
                }
            )
    else:
        relationships = []

    # Load claims from these documents
    claim_rows = (
        session.query(Claim, Entity, Document)
        .join(Entity, Claim.subject_entity_id == Entity.id)
        .join(Document, Claim.source_document_id == Document.id)
        .filter(Claim.source_document_id.in_(doc_ids))
        .order_by(Claim.overall_confidence.desc())
        .limit(max_claims)
        .all()
    )

    claims = [
        {
            "statement": c.statement,
            "type": c.claim_type.value if hasattr(c.claim_type, "value") else str(c.claim_type),
            "confidence": c.overall_confidence,
            "entity": e.name,
            "source_doc_id": str(d.id),
            "source_doc_title": d.title or "",
        }
        for c, e, d in claim_rows
    ]

    # Load document metadata for sources
    doc_rows = (
        session.query(Document.id, Document.title, Document.source_url)
        .filter(Document.id.in_(doc_ids))
        .all()
    )

    sources = [
        {
            "doc_id": str(d.id),
            "title": d.title or "Untitled",
            "url": d.source_url or "",
        }
        for d in doc_rows
    ]

    logger.info(
        f"Loaded context: {len(entities)} entities, "
        f"{len(relationships)} relationships, {len(claims)} claims, "
        f"{len(sources)} sources"
    )

    return TopicContextData(
        topics=topics,
        entities=entities,
        relationships=relationships,
        claims=claims,
        sources=sources,
    )


# ============================================================================
# Markdown Formatting
# ============================================================================


def estimate_tokens(text: str) -> int:
    """Rough token estimation (4 chars per token)."""
    return len(text) // 4


def format_agent_context(query: str, data: TopicContextData) -> str:
    """Format context data as markdown for agent system prompt.

    Args:
        query: Original user query
        data: Context data from load_topic_context

    Returns:
        Markdown-formatted context string
    """
    lines = [
        "# Knowledge Context",
        "",
        f"**Query:** {query}",
        f"**Topics:** {', '.join(data.topics) if data.topics else 'None matched'}",
        "",
    ]

    # Stats summary
    lines.append(
        f"*Retrieved: {len(data.entities)} entities, "
        f"{len(data.relationships)} relationships, "
        f"{len(data.claims)} claims from {len(data.sources)} documents*"
    )
    lines.append("")

    # Knowledge Graph section
    lines.append("## Knowledge Graph")
    lines.append("")

    # Entities - highlight matched ones
    lines.append("### Entities")
    matched = [e for e in data.entities if e.get("matched")]
    other = [e for e in data.entities if not e.get("matched")]

    if matched:
        lines.append("")
        lines.append("**Matched from query:**")
        for e in matched:
            desc = f": {e['description'][:100]}..." if e["description"] else ""
            lines.append(f"- **{e['name']}** ({e['type']}){desc}")

    if other:
        lines.append("")
        lines.append("**Related entities:**")
        for e in other[:20]:  # Limit display
            desc = f": {e['description'][:80]}..." if e["description"] else ""
            lines.append(f"- {e['name']} ({e['type']}){desc}")

    lines.append("")

    # Relationships
    if data.relationships:
        lines.append("### Relationships")
        for r in data.relationships:
            lines.append(f"- {r['source']} --[{r['type']}]--> {r['target']}")
        lines.append("")

    # Claims section
    if data.claims:
        lines.append("## Claims")
        lines.append("")

        # Group claims by entity
        claims_by_entity: dict[str, list] = {}
        for claim in data.claims:
            entity = claim["entity"]
            if entity not in claims_by_entity:
                claims_by_entity[entity] = []
            claims_by_entity[entity].append(claim)

        for entity, entity_claims in claims_by_entity.items():
            lines.append(f"### {entity}")
            for claim in entity_claims[:5]:  # Max 5 claims per entity
                conf = claim["confidence"]
                source = claim["source_doc_title"]
                source_ref = f" → [{source}]" if source else ""
                lines.append(f"- {claim['statement']} [conf: {conf:.2f}]{source_ref}")
            lines.append("")

    # Sources section
    if data.sources:
        lines.append("## Sources")
        lines.append("")
        for i, src in enumerate(data.sources, 1):
            if src["url"]:
                lines.append(f"[{i}] {src['title']} - {src['url']}")
            else:
                lines.append(f"[{i}] {src['title']}")

    return "\n".join(lines)


# ============================================================================
# Main Entry Point
# ============================================================================


async def retrieve_cag(
    query: str,
    top_k_entities: int = 5,
    min_similarity: float = 0.3,
    max_claims: int = 50,
) -> CAGResult:
    """CAG-style retrieval for agent session bootstrap.

    This is the main entry point for CAG retrieval:
    1. Embed query and find similar entities (single API call)
    2. Route to topics containing those entities
    3. Load all context for those topics (pure SQL)
    4. Format as markdown for agent system prompt

    Args:
        query: User query
        top_k_entities: Max entities to match for routing
        min_similarity: Minimum similarity threshold for entity matching
        max_claims: Maximum claims to include in context

    Returns:
        CAGResult with context_markdown ready for agent use
    """
    logger.info(f"CAG retrieval for: {query[:50]}...")

    # Step 1: Route to topics via entity similarity
    topics, matched_entities = route_to_topics_via_entities(
        query,
        top_k_entities=top_k_entities,
        min_similarity=min_similarity,
    )

    # Step 2: Load context (SQL only)
    context_data = load_topic_context(
        topics,
        matched_entities,
        max_claims=max_claims,
    )

    # Step 3: Format as markdown
    context_md = format_agent_context(query, context_data)
    token_est = estimate_tokens(context_md)

    logger.info(f"CAG retrieval complete: {token_est} estimated tokens")

    return CAGResult(
        query=query,
        topics=topics,
        matched_entities=matched_entities,
        context_markdown=context_md,
        token_estimate=token_est,
        sources=context_data.sources,
        telemetry={
            "topics_matched": len(topics),
            "entities_matched": len(matched_entities),
            "entities_loaded": len(context_data.entities),
            "relationships_loaded": len(context_data.relationships),
            "claims_loaded": len(context_data.claims),
            "sources_loaded": len(context_data.sources),
            "token_estimate": token_est,
        },
    )
