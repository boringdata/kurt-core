"""
Fetch workflow configuration.

Config values can be set in kurt.config with FETCH.* prefix:

    FETCH.FETCH_ENGINE=firecrawl
    FETCH.BATCH_SIZE=20
    FETCH.EMBEDDING_MAX_CHARS=2000

Usage:
    # Load from config file
    config = FetchConfig.from_config("fetch")

    # Or instantiate directly
    config = FetchConfig(fetch_engine="firecrawl")

    # Or merge: config file + CLI overrides
    config = FetchConfig.from_config("fetch", dry_run=True)
"""

from __future__ import annotations

from kurt.config import ConfigParam, StepConfig


class FetchConfig(StepConfig):
    """Configuration for fetch workflow.

    Loaded from kurt.config with FETCH.* prefix.
    """

    # Fetch settings
    fetch_engine: str = ConfigParam(
        default="trafilatura",
        fallback="INGESTION_FETCH_ENGINE",
        description="Fetch engine: trafilatura, httpx, firecrawl, tavily",
    )
    batch_size: int | None = ConfigParam(
        default=None,
        ge=1,
        le=100,
        description="Batch size for engines with batch support (tavily: max 20)",
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

    # Runtime flags (CLI only, not loaded from config file)
    dry_run: bool = False  # Preview mode - don't persist changes
