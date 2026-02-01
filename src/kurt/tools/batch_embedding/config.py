"""
Batch embedding tool configuration.

Config values can be set in kurt.config with BATCH_EMBEDDING.* prefix:

    BATCH_EMBEDDING.PROVIDER=openai
    BATCH_EMBEDDING.MODEL=text-embedding-3-small
    BATCH_EMBEDDING.BATCH_SIZE=100
    BATCH_EMBEDDING.MAX_CHARS=8000

Usage:
    # Load from config file
    config = BatchEmbeddingToolConfig.from_config("batch-embedding")

    # Or instantiate directly
    config = BatchEmbeddingToolConfig(provider="voyage")

    # Or merge: config file + CLI overrides
    config = BatchEmbeddingToolConfig.from_config("batch-embedding", batch_size=50)
"""

from __future__ import annotations

from typing import Literal

from kurt.config import ConfigParam, StepConfig


class BatchEmbeddingToolConfig(StepConfig):
    """Configuration for batch embedding generation tool.

    Loaded from kurt.config with BATCH_EMBEDDING.* prefix.
    Note: Named BatchEmbeddingToolConfig to avoid conflict with BatchEmbeddingConfig in __init__.py.
    """

    # Provider settings
    provider: Literal["openai", "cohere", "voyage"] = ConfigParam(
        default="openai",
        description="Embedding provider to use",
    )
    model: str = ConfigParam(
        default="text-embedding-3-small",
        description="Embedding model name",
    )

    # Processing settings
    batch_size: int = ConfigParam(
        default=100,
        ge=1,
        le=2048,
        description="Number of texts per API batch",
    )
    concurrency: int = ConfigParam(
        default=2,
        ge=1,
        le=10,
        description="Maximum parallel API calls",
    )
    max_chars: int = ConfigParam(
        default=8000,
        ge=100,
        le=100000,
        description="Maximum characters per text (truncated if exceeded)",
    )
