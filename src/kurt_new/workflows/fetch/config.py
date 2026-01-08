"""
Fetch workflow configuration.

Config values can be set in kurt.config with FETCH.* prefix:

    FETCH.FETCH_ENGINE=firecrawl
    FETCH.EMBEDDING_MAX_CHARS=2000
    FETCH.DRY_RUN=true

Usage:
    # Load from config file
    config = FetchConfig.from_config("fetch")

    # Or instantiate directly
    config = FetchConfig(fetch_engine="firecrawl", dry_run=True)

    # Or merge: config file + overrides
    config = FetchConfig.from_config("fetch", dry_run=True)
"""

from __future__ import annotations

from kurt_new.config import ConfigParam, StepConfig


class FetchConfig(StepConfig):
    """Configuration for fetch workflow.

    Loaded from kurt.config with FETCH.* prefix.
    """

    # Fetch settings
    fetch_engine: str = ConfigParam(
        default="trafilatura",
        fallback="INGESTION_FETCH_ENGINE",
        description="Fetch engine: trafilatura, httpx, firecrawl",
    )

    # Embedding settings
    embedding_max_chars: int = ConfigParam(
        default=1000,
        ge=100,
        le=5000,
        description="Maximum characters for embedding generation",
    )
    embedding_batch_size: int = ConfigParam(
        default=100,
        ge=1,
        le=500,
        description="Batch size for embedding generation",
    )
    embedding_concurrency: int = ConfigParam(
        default=3,
        ge=1,
        le=10,
        description="Concurrent batches for embedding generation",
    )

    # Behavior
    dry_run: bool = ConfigParam(default=False, description="Dry run mode")
