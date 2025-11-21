"""Embedding generation and storage utilities.

This module provides utilities for generating and manipulating embeddings
used throughout the Kurt indexing and knowledge graph systems.
"""

import struct

import dspy
import numpy as np


def get_embedding_model() -> str:
    """Get configured embedding model from Kurt config.

    Returns:
        Model identifier string (e.g., "openai/text-embedding-3-small")
    """
    from kurt.config import load_config

    config = load_config()
    return config.EMBEDDING_MODEL


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using configured model.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors (each is a list of floats)

    Example:
        embeddings = generate_embeddings(["Python", "FastAPI"])
        # Returns: [[0.1, 0.2, ...], [0.3, 0.4, ...]]
    """
    embedding_model = get_embedding_model()
    embedder = dspy.Embedder(model=embedding_model)
    return embedder(texts)


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
