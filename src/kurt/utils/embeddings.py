"""Embedding generation and storage utilities.

This module provides utilities for generating and manipulating embeddings
used throughout the Kurt indexing and knowledge graph systems.
"""

import struct
import time

import dspy
import numpy as np


def generate_embeddings(
    texts: list[str], module_name: str | None = None, step_name: str | None = None, step_config=None
) -> list[list[float]]:
    """Generate embeddings for a list of texts using configured model.

    Supports both cloud providers (OpenAI, etc.) and local
    OpenAI-compatible servers.

    Model resolution (module-first hierarchy):
        1. step_config.embedding_model (if provided)
        2. <MODULE>.<STEP>.EMBEDDING_MODEL (e.g., INDEXING.ENTITY_CLUSTERING.EMBEDDING_MODEL)
        3. <MODULE>.EMBEDDING_MODEL (e.g., INDEXING.EMBEDDING_MODEL)
        4. EMBEDDING_MODEL (global)

    API settings resolution:
        1. <MODULE>.<STEP>.EMBEDDING_API_BASE
        2. <MODULE>.EMBEDDING_API_BASE
        3. EMBEDDING_API_BASE (global)

    Example kurt.config:
        # Cloud provider (default)
        EMBEDDING_MODEL="openai/text-embedding-3-small"

        # Or local server (global)
        EMBEDDING_API_BASE="http://localhost:8080/v1/"
        EMBEDDING_MODEL="nomic-embed-text"

        # Module-level overrides
        INDEXING.EMBEDDING_MODEL="bge-large"
        INDEXING.EMBEDDING_API_BASE="http://localhost:8080/v1/"

        # Step-level overrides
        INDEXING.ENTITY_CLUSTERING.EMBEDDING_MODEL="bge-small"

    Args:
        texts: List of text strings to embed
        module_name: Optional module name - "INDEXING", "RETRIEVAL", etc.
        step_name: Optional step name - "ENTITY_CLUSTERING", etc.
        step_config: Optional step config with embedding_model attribute

    Returns:
        List of embedding vectors (each is a list of floats)

    Example:
        embeddings = generate_embeddings(["Python", "FastAPI"])
        # Returns: [[0.1, 0.2, ...], [0.3, 0.4, ...]]

        # With module-specific config
        embeddings = generate_embeddings(["query"], module_name="RETRIEVAL")
    """
    from kurt.config.base import resolve_model_settings

    # Use generic resolution
    settings = resolve_model_settings(
        model_category="EMBEDDING",
        module_name=module_name,
        step_name=step_name,
        step_config=step_config,
    )

    model = settings.model
    api_base = settings.api_base
    api_key = settings.api_key

    if api_base:
        # Local OpenAI-compatible server
        # Strip provider prefix if present since we're using a local server
        if "/" in model:
            model = model.split("/", 1)[1]
        embedder = dspy.Embedder(
            model=f"openai/{model}",
            api_base=api_base,
            api_key=api_key or "not_needed",
        )
    else:
        # Cloud provider
        embedder = dspy.Embedder(model=model)

    # Track embedding call for rate monitoring
    from kurt.core.llm_tracker import track_embedding_call

    start = time.time()
    result = embedder(texts)
    duration_ms = (time.time() - start) * 1000

    track_embedding_call(
        model=model,
        count=len(texts),
        step_name=step_name,
        duration_ms=duration_ms,
    )

    return result


def embedding_to_bytes(embedding: list[float]) -> bytes:
    """Convert embedding vector to bytes for database storage.

    Args:
        embedding: Embedding vector as list of floats

    Returns:
        Bytes representation (float32 array)

    Example:
        embedding = [0.1, 0.2, 0.3]
        bytes_data = embedding_to_bytes(embedding)
    """
    return np.array(embedding, dtype=np.float32).tobytes()


def bytes_to_embedding(embedding_bytes: bytes) -> list[float]:
    """Convert stored bytes back to embedding vector.

    Args:
        embedding_bytes: Bytes representation of embedding

    Returns:
        Embedding vector as list of floats

    Example:
        embedding = bytes_to_embedding(stored_bytes)
    """
    return struct.unpack(f"{len(embedding_bytes)//4}f", embedding_bytes)


def generate_document_embedding(content: str, max_chars: int = 1000) -> bytes:
    """Generate embedding for document content.

    EXPENSIVE LLM CALL (~$0.0001 per call) - use wisely!

    Uses first max_chars characters to avoid token limits.
    Returns bytes for direct database storage.

    Args:
        content: Document content
        max_chars: Maximum characters to use (default: 1000)

    Returns:
        Embedding as bytes (numpy float32 array)

    Raises:
        Exception: If embedding generation fails

    Example:
        >>> embedding = generate_document_embedding("Document content here...")
        >>> # Returns: b'\\x00\\x00\\x00...' (bytes)
        >>> # Can be stored directly in Document.embedding field
    """
    import logging

    logger = logging.getLogger(__name__)

    # Use first max_chars
    content_sample = content[:max_chars] if len(content) > max_chars else content

    # Generate embedding using configured model
    embeddings = generate_embeddings([content_sample])

    # Convert to bytes
    embedding_bytes = embedding_to_bytes(embeddings[0])

    logger.info(f"Generated embedding ({len(embeddings[0])} dimensions)")

    return embedding_bytes
