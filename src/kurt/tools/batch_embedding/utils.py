"""Embedding utility functions.

Simple, synchronous functions for embedding generation.
These can be used directly without running a full workflow.
"""

from __future__ import annotations

import logging
import struct
import time
from typing import Any

logger = logging.getLogger(__name__)

# Import litellm at module level for test monkeypatching
try:
    import litellm
except ImportError:
    litellm = None  # type: ignore


def embedding_to_bytes(embedding: list[float]) -> bytes:
    """Convert embedding vector to bytes for database storage."""
    try:
        import numpy as np
    except ImportError as e:
        raise ImportError(
            "numpy is required for embeddings. Install with: pip install numpy"
        ) from e
    return np.array(embedding, dtype=np.float32).tobytes()


def bytes_to_embedding(embedding_bytes: bytes) -> list[float]:
    """Convert stored bytes back to embedding vector."""
    return list(struct.unpack(f"{len(embedding_bytes)//4}f", embedding_bytes))


def _extract_usage_tokens(response: Any) -> tuple[int, int]:
    """Extract token usage from litellm response."""
    usage = getattr(response, "usage", None)
    if isinstance(usage, dict):
        tokens_in = usage.get("prompt_tokens", usage.get("input_tokens"))
        tokens_out = usage.get("completion_tokens", usage.get("output_tokens", 0))
        if tokens_in is None:
            total_tokens = usage.get("total_tokens")
            if total_tokens is not None:
                tokens_in = total_tokens - (tokens_out or 0)
        return int(tokens_in or 0), int(tokens_out or 0)

    if usage is not None:
        tokens_in = getattr(usage, "prompt_tokens", None)
        if tokens_in is None:
            tokens_in = getattr(usage, "input_tokens", None)
        tokens_out = getattr(usage, "completion_tokens", None)
        if tokens_out is None:
            tokens_out = getattr(usage, "output_tokens", 0)
        if tokens_in is None:
            total_tokens = getattr(usage, "total_tokens", None)
            if total_tokens is not None:
                tokens_in = total_tokens - (tokens_out or 0)
        return int(tokens_in or 0), int(tokens_out or 0)

    return 0, 0


def _calculate_embedding_cost(response: Any, model: str | None) -> float:
    """Calculate cost for embedding API call."""
    if not model:
        return 0.0
    if litellm is None:
        return 0.0
    try:
        return float(
            litellm.response_cost_calculator(
                response_object=response,
                model=model,
                custom_llm_provider=None,
                call_type="embedding",
                optional_params={},
            )
        )
    except Exception:
        return 0.0


def generate_embeddings(
    texts: list[str],
    model: str | None = None,
    api_base: str | None = None,
    api_key: str | None = None,
    module_name: str | None = None,
    step_name: str | None = None,
    record_trace: bool = False,  # Disabled by default - no tracing dependency
) -> list[list[float]]:
    """
    Generate embeddings for a list of texts using LiteLLM.

    Model resolution (hierarchical):
        1. Explicit model parameter
        2. MODULE.STEP.EMBEDDING_MODEL
        3. MODULE.EMBEDDING_MODEL
        4. EMBEDDING_MODEL (global)

    Args:
        texts: List of text strings to embed
        model: Model name (optional, uses config resolution)
        api_base: API base URL (optional)
        api_key: API key (optional)
        module_name: Module name for config resolution
        step_name: Step name for config resolution
        record_trace: Whether to record the embedding call (requires tracing setup)

    Returns:
        List of embedding vectors
    """
    # Only resolve config if model not provided
    if model is None:
        from kurt.config import resolve_model_settings

        settings = resolve_model_settings(
            model_category="EMBEDDING",
            module_name=module_name,
            step_name=step_name,
        )
        model = settings.model
        if api_base is None:
            api_base = settings.api_base
        if api_key is None:
            api_key = settings.api_key

    start = time.time()

    if litellm is None:
        raise ImportError(
            "litellm is required for embeddings. Install with: pip install litellm"
        )

    kwargs = {"model": model, "input": texts}
    if api_base:
        kwargs["api_base"] = api_base
    if api_key:
        kwargs["api_key"] = api_key

    response = litellm.embedding(**kwargs)
    duration_ms = int((time.time() - start) * 1000)

    result = [item["embedding"] for item in response.data]
    logger.debug(f"Generated {len(texts)} embeddings in {duration_ms}ms (model={model})")

    return result


def generate_document_embedding(
    content: str,
    max_chars: int = 1000,
    module_name: str | None = None,
    step_name: str | None = None,
) -> bytes:
    """
    Generate embedding for document content.

    Args:
        content: Document content
        max_chars: Maximum characters to use
        module_name: Module name for config resolution
        step_name: Step name for config resolution

    Returns:
        Embedding as bytes
    """
    content_sample = content[:max_chars] if len(content) > max_chars else content
    embeddings = generate_embeddings(
        [content_sample],
        module_name=module_name,
        step_name=step_name,
    )
    return embedding_to_bytes(embeddings[0])


__all__ = [
    "embedding_to_bytes",
    "bytes_to_embedding",
    "generate_embeddings",
    "generate_document_embedding",
]
