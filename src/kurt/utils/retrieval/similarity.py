"""Vector similarity utilities."""

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine similarity score between 0 and 1
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def cosine_similarity_batch(query_emb: np.ndarray, embeddings: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between query and multiple embeddings.

    Args:
        query_emb: Query embedding vector
        embeddings: Array of embeddings (n_embeddings, embedding_dim)

    Returns:
        Array of similarity scores
    """
    if embeddings.size == 0:
        return np.array([])

    query_norm = np.linalg.norm(query_emb)
    if query_norm == 0:
        return np.zeros(len(embeddings))

    emb_norms = np.linalg.norm(embeddings, axis=1)
    emb_norms[emb_norms == 0] = 1  # Avoid division by zero

    similarities = np.dot(embeddings, query_emb) / (emb_norms * query_norm)
    return similarities


def reciprocal_rank_fusion(
    rankings: list[list[str]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Combine multiple rankings using Reciprocal Rank Fusion.

    RRF score = sum(1 / (k + rank)) for each ranking.

    Args:
        rankings: List of rankings (each is a list of doc IDs)
        k: RRF constant (default 60)

    Returns:
        List of (doc_id, score) tuples sorted by score desc
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for i, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + i + 1)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
