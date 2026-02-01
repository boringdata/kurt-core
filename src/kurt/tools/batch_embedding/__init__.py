"""
BatchEmbeddingTool - Vector embedding generation tool for Kurt workflows.

Generates embeddings for text content using configurable providers (OpenAI, Cohere, Voyage).
Supports batch processing with concurrency control and exponential backoff retries.
"""

from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..core.base import ProgressCallback, Tool, ToolContext, ToolResult
from ..core.registry import register_tool
from .schema import BatchEmbeddingResult

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Maximum batch sizes per provider
PROVIDER_MAX_BATCH_SIZES = {
    "openai": 2048,
    "cohere": 96,
    "voyage": 128,
}

# Default models per provider
PROVIDER_DEFAULT_MODELS = {
    "openai": "text-embedding-3-small",
    "cohere": "embed-english-v3.0",
    "voyage": "voyage-2",
}

# HTTP status codes that should trigger a retry
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


# ============================================================================
# Pydantic Models
# ============================================================================


class BatchEmbeddingProvider(str, Enum):
    """Supported embedding providers."""

    OPENAI = "openai"
    COHERE = "cohere"
    VOYAGE = "voyage"


class BatchEmbeddingInput(BaseModel):
    """Input for a single text to embed."""

    text: str = Field(..., description="Text content to embed")


class BatchEmbeddingConfig(BaseModel):
    """Configuration for the batch embedding tool."""

    model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name",
    )
    text_field: str = Field(
        default="content",
        description="Field name in input containing text to embed",
    )
    provider: Literal["openai", "cohere", "voyage"] = Field(
        default="openai",
        description="Embedding provider to use",
    )
    batch_size: int = Field(
        default=100,
        ge=1,
        le=2048,
        description="Number of texts per API batch (1-2048)",
    )
    concurrency: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Maximum parallel API calls (1-10)",
    )
    max_chars: int = Field(
        default=8000,
        ge=100,
        le=100000,
        description="Maximum characters per text (truncated if exceeded)",
    )


class BatchEmbeddingOutput(BaseModel):
    """Output for an embedded text."""

    text: str = Field(..., description="Original text that was embedded")
    embedding: bytes | None = Field(default=None, description="Embedding as bytes (float32 array)")
    status: Literal["success", "error", "skipped"] = Field(
        default="success",
        description="Embedding status",
    )
    error: str | None = Field(default=None, description="Error message if failed")


class BatchEmbeddingParams(BaseModel):
    """Combined parameters for the batch embedding tool.

    Accepts two input styles:
    1. Executor style (flat): input_data + model, text_field, etc. at top level
    2. Direct API style (nested): inputs + config=BatchEmbeddingConfig(...)
    """

    # For executor style (flat)
    input_data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of input rows with text field (from upstream steps)",
    )

    # For direct API style (nested)
    inputs: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of input rows with text field (alternative to input_data)",
    )
    config: BatchEmbeddingConfig | None = Field(
        default=None,
        description="Batch embedding configuration (alternative to flat fields)",
    )

    # Flat config fields for executor compatibility
    model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name",
    )
    text_field: str = Field(
        default="content",
        description="Field name in input containing text to embed",
    )
    provider: Literal["openai", "cohere", "voyage"] = Field(
        default="openai",
        description="Embedding provider to use",
    )
    batch_size: int = Field(
        default=100,
        ge=1,
        le=2048,
        description="Number of texts per API batch",
    )
    concurrency: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Maximum parallel API calls",
    )
    max_chars: int = Field(
        default=8000,
        ge=100,
        le=100000,
        description="Maximum characters per text",
    )

    def get_inputs(self) -> list[dict[str, Any]]:
        """Get the input list from either input_data or inputs field."""
        if self.input_data:
            return self.input_data
        return self.inputs

    def get_config(self) -> BatchEmbeddingConfig:
        """Get config from nested config field or flat fields."""
        if self.config is not None:
            return self.config
        return BatchEmbeddingConfig(
            model=self.model,
            text_field=self.text_field,
            provider=self.provider,
            batch_size=self.batch_size,
            concurrency=self.concurrency,
            max_chars=self.max_chars,
        )


# ============================================================================
# Embedding Utilities
# ============================================================================


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
    import struct

    return list(struct.unpack(f"{len(embedding_bytes) // 4}f", embedding_bytes))


# ============================================================================
# Provider Functions
# ============================================================================


async def _embed_with_openai(
    texts: list[str],
    model: str,
    api_key: str | None = None,
) -> list[list[float]]:
    """
    Generate embeddings using OpenAI API.

    Args:
        texts: List of texts to embed
        model: Model name (e.g., 'text-embedding-3-small')
        api_key: Optional API key (uses OPENAI_API_KEY env var if not provided)

    Returns:
        List of embedding vectors

    Raises:
        ValueError: If embedding fails
    """
    try:
        import litellm
    except ImportError as e:
        raise ImportError(
            "litellm is required for embeddings. Install with: pip install litellm"
        ) from e

    kwargs: dict[str, Any] = {
        "model": model,
        "input": texts,
    }
    if api_key:
        kwargs["api_key"] = api_key

    response = litellm.embedding(**kwargs)
    return [item["embedding"] for item in response.data]


async def _embed_with_cohere(
    texts: list[str],
    model: str,
    api_key: str | None = None,
) -> list[list[float]]:
    """
    Generate embeddings using Cohere API.

    Args:
        texts: List of texts to embed
        model: Model name (e.g., 'embed-english-v3.0')
        api_key: Optional API key (uses COHERE_API_KEY env var if not provided)

    Returns:
        List of embedding vectors

    Raises:
        ValueError: If embedding fails
    """
    try:
        import litellm
    except ImportError as e:
        raise ImportError(
            "litellm is required for embeddings. Install with: pip install litellm"
        ) from e

    # LiteLLM uses 'cohere/' prefix for Cohere models
    full_model = model if model.startswith("cohere/") else f"cohere/{model}"

    kwargs: dict[str, Any] = {
        "model": full_model,
        "input": texts,
    }
    if api_key:
        kwargs["api_key"] = api_key

    response = litellm.embedding(**kwargs)
    return [item["embedding"] for item in response.data]


async def _embed_with_voyage(
    texts: list[str],
    model: str,
    api_key: str | None = None,
) -> list[list[float]]:
    """
    Generate embeddings using Voyage AI API.

    Args:
        texts: List of texts to embed
        model: Model name (e.g., 'voyage-2')
        api_key: Optional API key (uses VOYAGE_API_KEY env var if not provided)

    Returns:
        List of embedding vectors

    Raises:
        ValueError: If embedding fails
    """
    try:
        import litellm
    except ImportError as e:
        raise ImportError(
            "litellm is required for embeddings. Install with: pip install litellm"
        ) from e

    # LiteLLM uses 'voyage/' prefix for Voyage models
    full_model = model if model.startswith("voyage/") else f"voyage/{model}"

    kwargs: dict[str, Any] = {
        "model": full_model,
        "input": texts,
    }
    if api_key:
        kwargs["api_key"] = api_key

    response = litellm.embedding(**kwargs)
    return [item["embedding"] for item in response.data]


# Provider dispatcher
_EMBED_PROVIDERS = {
    "openai": _embed_with_openai,
    "cohere": _embed_with_cohere,
    "voyage": _embed_with_voyage,
}


# ============================================================================
# Retry Logic
# ============================================================================


def _is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error should trigger a retry.

    Retryable:
    - Rate limit errors (429)
    - Server errors (500, 502, 503, 504)
    - Connection errors
    - Timeouts

    Not retryable:
    - Authentication errors
    - Invalid request errors
    - Content-related errors

    Args:
        error: The exception that occurred

    Returns:
        True if the error should be retried
    """
    error_msg = str(error).lower()

    # Rate limit errors
    if "rate" in error_msg and "limit" in error_msg:
        return True
    if "429" in error_msg:
        return True

    # Server errors
    if any(str(code) in error_msg for code in RETRYABLE_STATUS_CODES):
        return True

    # Connection/timeout errors
    if "timeout" in error_msg:
        return True
    if "connection" in error_msg:
        return True

    # Authentication errors - not retryable
    if "auth" in error_msg or "401" in error_msg or "403" in error_msg:
        return False

    # Invalid request - not retryable
    if "400" in error_msg or "invalid" in error_msg:
        return False

    # Default: don't retry unknown errors
    return False


async def _embed_with_retry(
    texts: list[str],
    provider: str,
    model: str,
    retries: int = 3,
    retry_backoff_ms: int = 1000,
    api_key: str | None = None,
) -> tuple[list[list[float]], int]:
    """
    Embed texts with exponential backoff retry.

    Args:
        texts: List of texts to embed
        provider: Provider name
        model: Model name
        retries: Maximum retry attempts
        retry_backoff_ms: Base backoff delay in milliseconds
        api_key: Optional API key

    Returns:
        Tuple of (embeddings, latency_ms)

    Raises:
        Exception: The last error if all retries fail
    """
    embed_fn = _EMBED_PROVIDERS[provider]
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        start_time = time.monotonic()
        try:
            embeddings = await embed_fn(texts, model, api_key)
            latency_ms = int((time.monotonic() - start_time) * 1000)
            return embeddings, latency_ms

        except Exception as e:
            last_error = e
            latency_ms = int((time.monotonic() - start_time) * 1000)

            # Check if we should retry
            if attempt < retries and _is_retryable_error(e):
                # Calculate backoff: delay * 2^attempt
                delay_ms = retry_backoff_ms * (2**attempt)
                logger.debug(
                    f"Retry {attempt + 1}/{retries} for embedding batch after {delay_ms}ms: {e}"
                )
                await asyncio.sleep(delay_ms / 1000)
            else:
                # No more retries or non-retryable error
                raise

    # Should not reach here, but just in case
    if last_error:
        raise last_error
    raise RuntimeError("Unexpected state in _embed_with_retry")


# ============================================================================
# BatchEmbeddingTool Implementation
# ============================================================================


@register_tool
class BatchEmbeddingTool(Tool[BatchEmbeddingParams, BatchEmbeddingOutput]):
    """
    Generate vector embeddings for text content.

    Substeps:
    - generate_embeddings: API calls to embedding provider (progress: texts embedded)

    Providers:
    - openai: OpenAI embeddings (text-embedding-3-small, text-embedding-3-large, etc.)
    - cohere: Cohere embeddings (embed-english-v3.0, etc.)
    - voyage: Voyage AI embeddings (voyage-2, voyage-large-2, etc.)
    """

    name = "batch-embedding"
    description = "Generate vector embeddings for text content"
    InputModel = BatchEmbeddingParams
    OutputModel = BatchEmbeddingOutput

    async def run(
        self,
        params: BatchEmbeddingParams,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        """
        Execute the batch embedding tool.

        Args:
            params: Batch embedding parameters (inputs and config)
            context: Execution context
            on_progress: Optional progress callback

        Returns:
            ToolResult with embedded texts
        """
        config = params.get_config()
        inputs = params.get_inputs()

        if not inputs:
            return ToolResult(
                success=True,
                data=[],
            )

        # Extract text from input rows
        texts: list[str] = []
        text_indices: list[int] = []
        skipped_indices: list[int] = []

        for i, row in enumerate(inputs):
            text = row.get(config.text_field, "")
            if not text or not isinstance(text, str):
                # Skip empty or non-string texts
                skipped_indices.append(i)
                logger.debug(f"Skipping row {i}: empty or invalid text field '{config.text_field}'")
            else:
                # Truncate if needed
                if len(text) > config.max_chars:
                    text = text[: config.max_chars]
                    logger.debug(f"Truncated text at row {i} to {config.max_chars} chars")
                texts.append(text)
                text_indices.append(i)

        total_texts = len(texts)
        total_inputs = len(inputs)

        # ----------------------------------------------------------------
        # Substep: generate_embeddings
        # ----------------------------------------------------------------
        self.emit_progress(
            on_progress,
            substep="generate_embeddings",
            status="running",
            current=0,
            total=total_texts,
            message=f"Generating embeddings for {total_texts} text(s) with {config.provider}",
        )

        # Adjust batch size to provider maximum
        max_batch = PROVIDER_MAX_BATCH_SIZES.get(config.provider, 100)
        batch_size = min(config.batch_size, max_batch)

        # Create batches
        batches: list[tuple[list[str], list[int]]] = []
        for i in range(0, total_texts, batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_indices = text_indices[i : i + batch_size]
            batches.append((batch_texts, batch_indices))

        # Get API key from context settings
        api_key = context.settings.get(f"{config.provider}_api_key")

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(config.concurrency)

        # Process batches
        embeddings_map: dict[int, bytes] = {}
        errors_map: dict[int, str] = {}
        embedded_count = 0

        async def process_batch(
            batch_texts: list[str],
            batch_indices: list[int],
            batch_idx: int,
        ) -> dict[str, Any]:
            """Process a single batch with semaphore."""
            async with semaphore:
                try:
                    embeddings, latency_ms = await _embed_with_retry(
                        texts=batch_texts,
                        provider=config.provider,
                        model=config.model,
                        retries=3,
                        retry_backoff_ms=1000,
                        api_key=api_key,
                    )
                    return {
                        "status": "success",
                        "batch_idx": batch_idx,
                        "indices": batch_indices,
                        "embeddings": embeddings,
                        "latency_ms": latency_ms,
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "batch_idx": batch_idx,
                        "indices": batch_indices,
                        "error": str(e),
                    }

        # Execute batches concurrently
        tasks = [
            process_batch(batch_texts, batch_indices, i)
            for i, (batch_texts, batch_indices) in enumerate(batches)
        ]
        batch_results = await asyncio.gather(*tasks)

        # Process results
        for batch_result in batch_results:
            batch_result["batch_idx"]

            if batch_result["status"] == "success":
                embeddings = batch_result["embeddings"]
                indices = batch_result["indices"]

                for idx, embedding in zip(indices, embeddings):
                    embeddings_map[idx] = embedding_to_bytes(embedding)
                    embedded_count += 1

                self.emit_progress(
                    on_progress,
                    substep="generate_embeddings",
                    status="progress",
                    current=embedded_count,
                    total=total_texts,
                    message=f"Embedded {embedded_count}/{total_texts}",
                )
            else:
                # Batch failed - mark all indices as errors
                for idx in batch_result["indices"]:
                    errors_map[idx] = batch_result["error"]

        self.emit_progress(
            on_progress,
            substep="generate_embeddings",
            status="completed",
            current=embedded_count,
            total=total_texts,
            message=f"Generated {embedded_count} embeddings",
        )

        # Build output data
        output_data: list[dict[str, Any]] = []

        for i, row in enumerate(inputs):
            text = row.get(config.text_field, "")

            if i in skipped_indices:
                # Skipped (empty text)
                output_data.append({
                    **row,
                    "embedding": None,
                    "status": "skipped",
                    "error": f"Empty or invalid text field '{config.text_field}'",
                })
            elif i in errors_map:
                # Error during embedding
                output_data.append({
                    **row,
                    "embedding": None,
                    "status": "error",
                    "error": errors_map[i],
                })
            elif i in embeddings_map:
                # Successfully embedded
                output_data.append({
                    **row,
                    "embedding": embeddings_map[i],
                    "status": "success",
                    "error": None,
                })
            else:
                # Should not happen, but handle gracefully
                output_data.append({
                    **row,
                    "embedding": None,
                    "status": "error",
                    "error": "Unknown error",
                })

        # Build result
        success_count = sum(1 for d in output_data if d["status"] == "success")
        error_count = sum(1 for d in output_data if d["status"] == "error")
        skipped_count = sum(1 for d in output_data if d["status"] == "skipped")

        result = ToolResult(
            success=success_count > 0 or (error_count == 0 and skipped_count == total_inputs),
            data=output_data,
        )

        result.add_substep(
            name="generate_embeddings",
            status="completed",
            current=embedded_count,
            total=total_texts,
        )

        # Add errors
        for i, d in enumerate(output_data):
            if d.get("error"):
                result.add_error(
                    error_type=d["status"],
                    message=d["error"],
                    row_idx=i,
                    details={"text_preview": str(d.get(config.text_field, ""))[:100]},
                )

        return result


# ============================================================================
# Public API
# ============================================================================

from .models import BatchEmbeddingRecord, BatchEmbeddingStatus  # noqa: E402
from .utils import (  # noqa: E402
    generate_document_embedding,
    generate_embeddings,
)

__all__ = [
    # Tool class
    "BatchEmbeddingTool",
    # Database models
    "BatchEmbeddingRecord",
    "BatchEmbeddingStatus",
    # Pydantic models
    "BatchEmbeddingConfig",
    "BatchEmbeddingInput",
    "BatchEmbeddingOutput",
    "BatchEmbeddingParams",
    "BatchEmbeddingProvider",
    "BatchEmbeddingResult",
    # Utilities
    "embedding_to_bytes",
    "bytes_to_embedding",
    "generate_embeddings",
    "generate_document_embedding",
    # Constants
    "PROVIDER_MAX_BATCH_SIZES",
    "PROVIDER_DEFAULT_MODELS",
    # Internal (for testing)
    "_is_retryable_error",
    "_embed_with_retry",
]
