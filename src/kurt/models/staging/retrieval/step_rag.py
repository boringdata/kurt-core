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

import numpy as np
from sqlmodel import Field

from kurt.config import ConfigParam, ModelConfig
from kurt.core import PipelineContext, PipelineModelBase, TableWriter, model, table
from kurt.db.claim_models import Claim
from kurt.db.database import get_session
from kurt.db.graph_queries import find_documents_with_entity, get_document_knowledge_graph
from kurt.db.models import Document, Entity
from kurt.utils.embeddings import bytes_to_embedding, generate_embeddings

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
# Helper Functions
# ============================================================================


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def cosine_similarity_batch(query_emb: np.ndarray, embeddings: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between query and multiple embeddings."""
    if embeddings.size == 0:
        return np.array([])

    query_norm = np.linalg.norm(query_emb)
    if query_norm == 0:
        return np.zeros(len(embeddings))

    emb_norms = np.linalg.norm(embeddings, axis=1)
    emb_norms[emb_norms == 0] = 1  # Avoid division by zero

    similarities = np.dot(embeddings, query_emb) / (emb_norms * query_norm)
    return similarities


def extract_entities_from_query(
    query: str, query_embedding: list[float], top_k: int = 5
) -> list[str]:
    """Extract entities from query using embedding similarity."""
    session = get_session()
    query_vec = np.array(query_embedding, dtype=np.float32)

    entities = session.query(Entity).filter(Entity.embedding != b"").all()
    if not entities:
        return []

    similarities = []
    for entity in entities:
        try:
            entity_vec = np.array(bytes_to_embedding(entity.embedding), dtype=np.float32)
            sim = cosine_similarity(query_vec, entity_vec)
            if sim >= 0.3:
                similarities.append((entity.name, sim))
        except Exception:
            continue

    similarities.sort(key=lambda x: x[1], reverse=True)
    return [name for name, _ in similarities[:top_k]]


def graph_search(entities: list[str], top_k: int) -> list[tuple[str, float, list, list]]:
    """Search knowledge graph for documents mentioning entities.

    Returns list of (doc_id, score, entity_matches, relationships).
    """
    if not entities:
        return []

    doc_scores = {}
    doc_entities = {}
    doc_relationships = {}

    for entity_name in entities:
        # Find documents mentioning this entity
        docs = find_documents_with_entity(entity_name)

        for doc in docs:
            doc_id = str(doc.id)
            if doc_id not in doc_scores:
                doc_scores[doc_id] = 0
                doc_entities[doc_id] = []
                doc_relationships[doc_id] = []

            doc_scores[doc_id] += 1
            doc_entities[doc_id].append(entity_name)

            # Get relationships for this document
            kg = get_document_knowledge_graph(doc.id)
            if kg and "relationships" in kg:
                doc_relationships[doc_id].extend(kg["relationships"][:5])

    # Normalize scores
    max_score = len(entities) if entities else 1
    results = [
        (
            doc_id,
            doc_scores[doc_id] / max_score,
            doc_entities[doc_id],
            doc_relationships[doc_id][:10],
        )
        for doc_id in doc_scores
    ]

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


def semantic_search(
    query_embedding: list[float],
    top_k: int,
    min_similarity: float,
    max_docs: int,
) -> list[tuple[str, float, str, str]]:
    """Search documents by embedding similarity.

    Returns list of (doc_id, similarity, title, url).
    """
    session = get_session()
    query_vec = np.array(query_embedding, dtype=np.float32)

    # Load documents with embeddings
    docs = session.query(Document).filter(Document.embedding.isnot(None)).limit(max_docs).all()

    if not docs:
        return []

    # Batch compute similarities
    results = []
    for doc in docs:
        if doc.embedding:
            try:
                doc_vec = np.array(bytes_to_embedding(doc.embedding), dtype=np.float32)
                sim = cosine_similarity(query_vec, doc_vec)
                if sim >= min_similarity:
                    results.append((str(doc.id), sim, doc.title or "", doc.source_url or ""))
            except Exception:
                continue

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


def claim_search(
    query_embedding: list[float],
    entities: list[str],
    top_k: int,
    max_claims: int,
) -> list[dict]:
    """Search claims by semantic similarity with entity boost.

    Returns list of claim dicts.
    """
    session = get_session()
    query_vec = np.array(query_embedding, dtype=np.float32)

    # Load claims with embeddings
    claims = (
        session.query(Claim, Entity, Document)
        .join(Entity, Claim.subject_entity_id == Entity.id)
        .join(Document, Claim.source_document_id == Document.id)
        .filter(Claim.is_superseded == False)  # noqa: E712
        .limit(max_claims)
        .all()
    )

    if not claims:
        return []

    results = []
    for claim, entity, doc in claims:
        # Compute semantic similarity if claim has embedding
        sim = 0.0
        if hasattr(claim, "embedding") and claim.embedding:
            try:
                claim_vec = np.array(bytes_to_embedding(claim.embedding), dtype=np.float32)
                sim = cosine_similarity(query_vec, claim_vec)
            except Exception:
                pass

        # Entity boost
        entity_boost = 0.2 if entity.name in entities else 0.0

        # Combined score
        score = sim + claim.overall_confidence + entity_boost

        results.append(
            {
                "claim_id": str(claim.id),
                "statement": claim.statement,
                "claim_type": claim.claim_type.value
                if hasattr(claim.claim_type, "value")
                else str(claim.claim_type),
                "confidence": claim.overall_confidence,
                "similarity": sim,
                "score": score,
                "entity": entity.name,
                "doc_id": str(doc.id),
                "doc_title": doc.title or "",
            }
        )

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def reciprocal_rank_fusion(
    rankings: list[list[str]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Combine multiple rankings using RRF.

    RRF score = sum(1 / (k + rank)) for each ranking.
    """
    scores = {}
    for ranking in rankings:
        for i, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + i + 1)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def format_context(
    query: str,
    ranked_docs: list[tuple[str, float]],
    entities: list[str],
    relationships: list[dict],
    claims: list[dict],
    doc_metadata: dict,
) -> str:
    """Format retrieved context as text."""
    lines = [
        f"=== CONTEXT FOR: {query} ===",
        f"Retrieved: {len(ranked_docs)} documents, {len(claims)} claims",
        "",
    ]

    # Entities
    lines.append("## Entities")
    for entity in sorted(set(entities))[:30]:
        lines.append(f"- {entity}")
    lines.append("")

    # Relationships
    if relationships:
        lines.append("## Relationships")
        seen = set()
        for rel in relationships[:20]:
            if isinstance(rel, dict):
                key = (
                    rel.get("source_entity", ""),
                    rel.get("target_entity", ""),
                    rel.get("relationship_type", ""),
                )
                if key not in seen:
                    seen.add(key)
                    lines.append(f"- {key[0]} --[{key[2]}]--> {key[1]}")
        lines.append("")

    # Claims
    if claims:
        lines.append("## Claims")
        for claim in claims[:10]:
            entity = claim.get("entity", "")
            prefix = f"[{entity}] " if entity else ""
            lines.append(f"- {prefix}{claim['statement']} (confidence: {claim['confidence']:.2f})")
        lines.append("")

    # Citations
    lines.append("## Citations")
    for i, (doc_id, score) in enumerate(ranked_docs[:10]):
        meta = doc_metadata.get(doc_id, {})
        title = meta.get("title") or f"Document {doc_id[:8]}"
        url = meta.get("url", "")
        if url:
            lines.append(f"[{i + 1}] {title} ({url}) - score: {score:.3f}")
        else:
            lines.append(f"[{i + 1}] {title} - score: {score:.3f}")

    return "\n".join(lines)


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
    claims = claim_search(
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
    context_text = format_context(
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
