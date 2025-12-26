"""RAG-specific search utilities.

Graph search, semantic search, and claim search with entity boost.
"""

import logging

import numpy as np

from kurt.db.claim_models import Claim
from kurt.db.database import get_session
from kurt.db.graph_queries import find_documents_with_entity, get_document_knowledge_graph
from kurt.db.models import Document, Entity
from kurt.utils.embeddings import bytes_to_embedding
from kurt.utils.retrieval.similarity import cosine_similarity

logger = logging.getLogger(__name__)


def extract_entities_from_query(
    query: str, query_embedding: list[float], top_k: int = 5
) -> list[str]:
    """Extract entities from query using embedding similarity.

    Args:
        query: Query text (unused, for signature compatibility)
        query_embedding: Query embedding vector
        top_k: Maximum entities to return

    Returns:
        List of entity names
    """
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

    Args:
        entities: List of entity names to search for
        top_k: Maximum documents to return

    Returns:
        List of (doc_id, score, entity_matches, relationships) tuples
    """
    if not entities:
        return []

    doc_scores: dict[str, int] = {}
    doc_entities: dict[str, list] = {}
    doc_relationships: dict[str, list] = {}

    for entity_name in entities:
        docs = find_documents_with_entity(entity_name)

        for doc_uuid in docs:
            doc_id = str(doc_uuid)
            if doc_id not in doc_scores:
                doc_scores[doc_id] = 0
                doc_entities[doc_id] = []
                doc_relationships[doc_id] = []

            doc_scores[doc_id] += 1
            doc_entities[doc_id].append(entity_name)

            kg = get_document_knowledge_graph(doc_id)
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

    Args:
        query_embedding: Query embedding vector
        top_k: Maximum documents to return
        min_similarity: Minimum similarity threshold
        max_docs: Maximum documents to scan

    Returns:
        List of (doc_id, similarity, title, url) tuples
    """
    session = get_session()
    query_vec = np.array(query_embedding, dtype=np.float32)

    docs = session.query(Document).filter(Document.embedding.isnot(None)).limit(max_docs).all()

    if not docs:
        return []

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


def claim_search_with_boost(
    query_embedding: list[float],
    entities: list[str],
    top_k: int,
    max_claims: int,
) -> list[dict]:
    """Search claims by semantic similarity with entity boost.

    Args:
        query_embedding: Query embedding vector
        entities: Entities to boost in scoring
        top_k: Maximum claims to return
        max_claims: Maximum claims to scan

    Returns:
        List of claim dicts with score, entity, doc_id, etc.
    """
    session = get_session()
    query_vec = np.array(query_embedding, dtype=np.float32)

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
