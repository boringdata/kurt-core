"""Claim vector search utilities."""

import logging

import numpy as np

from kurt.db.claim_models import Claim
from kurt.db.database import get_session
from kurt.db.models import Document, Entity
from kurt.utils.embeddings import bytes_to_embedding
from kurt.utils.retrieval.similarity import cosine_similarity

logger = logging.getLogger(__name__)


def search_claims_by_embedding(
    query_embedding: list[float],
    top_k: int = 20,
    min_similarity: float = 0.3,
) -> list[tuple]:
    """Search claims by embedding similarity.

    Args:
        query_embedding: Query embedding vector
        top_k: Maximum number of claims to return
        min_similarity: Minimum similarity threshold

    Returns:
        List of (claim, entity, document, similarity) tuples sorted by similarity desc
    """
    session = get_session()
    query_vec = np.array(query_embedding, dtype=np.float32)

    # Load all claims with embeddings
    claim_rows = (
        session.query(Claim, Entity, Document)
        .join(Entity, Claim.subject_entity_id == Entity.id)
        .join(Document, Claim.source_document_id == Document.id)
        .filter(Claim.embedding.isnot(None))
        .all()
    )

    if not claim_rows:
        logger.debug("No claims with embeddings found")
        return []

    # Compute similarities
    results = []
    for claim, entity, doc in claim_rows:
        try:
            if not claim.embedding:
                continue
            claim_vec = np.array(bytes_to_embedding(claim.embedding), dtype=np.float32)
            sim = cosine_similarity(query_vec, claim_vec)
            if sim >= min_similarity:
                results.append((claim, entity, doc, sim))
        except Exception:
            continue

    # Sort by similarity and take top_k
    results.sort(key=lambda x: x[3], reverse=True)
    return results[:top_k]
