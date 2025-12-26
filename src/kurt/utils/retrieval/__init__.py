"""Retrieval utilities for CAG and RAG strategies."""

from kurt.utils.retrieval.claim_search import search_claims_by_embedding
from kurt.utils.retrieval.context_loading import (
    TopicContextData,
    load_context_for_documents,
    load_context_from_claims,
)
from kurt.utils.retrieval.entity_search import (
    get_topics_for_entities,
    search_entities_by_embedding,
)
from kurt.utils.retrieval.formatting import (
    estimate_tokens,
    format_agent_context,
    format_context_structured,
    format_rag_context,
)
from kurt.utils.retrieval.rag_search import (
    claim_search_with_boost,
    extract_entities_from_query,
    graph_search,
    semantic_search,
)
from kurt.utils.retrieval.similarity import (
    cosine_similarity,
    cosine_similarity_batch,
    reciprocal_rank_fusion,
)

__all__ = [
    # Similarity
    "cosine_similarity",
    "cosine_similarity_batch",
    "reciprocal_rank_fusion",
    # Entity search
    "search_entities_by_embedding",
    "get_topics_for_entities",
    # Claim search
    "search_claims_by_embedding",
    # Context loading
    "load_context_for_documents",
    "load_context_from_claims",
    "TopicContextData",
    # Formatting
    "format_agent_context",
    "format_context_structured",
    "format_rag_context",
    "estimate_tokens",
    # RAG search
    "extract_entities_from_query",
    "graph_search",
    "semantic_search",
    "claim_search_with_boost",
]
