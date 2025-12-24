"""Configuration for the retrieval pipeline steps.

This module defines RetrievalConfig, a ModelConfig subclass that provides
configurable parameters for all retrieval steps.

Configuration resolution order:
1. Step-specific: RETRIEVAL.<STEP>.<PARAM>
2. Global fallback: specified via ConfigParam.fallback
3. Default from ConfigParam
"""

from kurt.config import ConfigParam, ModelConfig


class RetrievalConfig(ModelConfig):
    """Configuration for retrieval pipeline steps.

    Attributes:
        default_query_type: Default retrieval mode ("graph", "semantic", "hybrid")
        max_context_tokens: Maximum tokens for the context output
        max_graph_iterations: Maximum rounds for iterative graph expansion (--deep)
        semantic_top_k: Number of documents to return from semantic search
        graph_top_k: Number of documents to return from graph search
        llm_model: LLM model to use for query analysis (falls back to INDEXING_LLM_MODEL)

    Example:
        config = RetrievalConfig.load("retrieval.query_analysis")
        print(config.llm_model)  # Uses INDEXING_LLM_MODEL from global config
    """

    default_query_type: str = ConfigParam(
        default="hybrid",
        description="Default retrieval mode: graph, semantic, or hybrid",
    )
    max_context_tokens: int = ConfigParam(
        default=4000,
        ge=500,
        le=16000,
        description="Maximum tokens for context output",
    )
    max_graph_iterations: int = ConfigParam(
        default=3,
        ge=1,
        le=10,
        description="Maximum rounds for iterative graph expansion (--deep mode)",
    )
    semantic_top_k: int = ConfigParam(
        default=10,
        ge=1,
        le=50,
        description="Number of documents to return from semantic search",
    )
    graph_top_k: int = ConfigParam(
        default=20,
        ge=1,
        le=100,
        description="Number of documents to return from graph search",
    )
    section_top_k: int = ConfigParam(
        default=10,
        ge=1,
        le=50,
        description="Number of sections to return from section search",
    )
    claim_top_k: int = ConfigParam(
        default=15,
        ge=1,
        le=50,
        description="Number of claims to return from claim search",
    )
    summary_top_k: int = ConfigParam(
        default=10,
        ge=1,
        le=30,
        description="Number of summaries to return from summary search",
    )
    # Search limits (to control memory usage)
    max_documents_to_search: int = ConfigParam(
        default=500,
        ge=50,
        le=5000,
        description="Maximum documents to load for semantic search",
    )
    max_sections_to_search: int = ConfigParam(
        default=500,
        ge=50,
        le=2000,
        description="Maximum sections to search",
    )
    max_claims_to_search: int = ConfigParam(
        default=500,
        ge=50,
        le=2000,
        description="Maximum claims to search",
    )
    max_summaries_to_search: int = ConfigParam(
        default=400,
        ge=50,
        le=1000,
        description="Maximum summaries to search (docs + entities)",
    )
    semantic_min_similarity: float = ConfigParam(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold for semantic search",
    )
    llm_model: str = ConfigParam(
        fallback="INDEXING_LLM_MODEL",
        description="LLM model for query analysis (falls back to indexing model)",
    )
    # Chain-of-thought settings
    cot_validation_rounds: int = ConfigParam(
        default=1,
        ge=0,
        le=3,
        description="Number of validation rounds for CoT retriever (0 to disable)",
    )
    cot_min_confidence: float = ConfigParam(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for CoT answers",
    )
