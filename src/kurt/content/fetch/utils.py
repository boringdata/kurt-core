"""
Fetch configuration utilities.

Provides fetch engine selection based on config and API key availability.
"""

import os

from kurt.config import KurtConfig, load_config


def _get_fetch_engine(override: str = None) -> str:
    """Determine which fetch engine to use based on config and API key availability."""
    # Handle override
    if override:
        override = override.lower()
        if override not in KurtConfig.VALID_FETCH_ENGINES:
            raise ValueError(
                f"Invalid fetch engine: {override}. Must be one of {KurtConfig.VALID_FETCH_ENGINES}"
            )

        # Validate Firecrawl API key if using Firecrawl
        if override == "firecrawl":
            firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
            if not firecrawl_api_key or firecrawl_api_key == "your_firecrawl_api_key_here":
                raise ValueError(
                    "Cannot use Firecrawl: FIRECRAWL_API_KEY not set or invalid.\n"
                    f"Add your API key to .env file or use --fetch-engine={KurtConfig.VALID_FETCH_ENGINES[0]}"
                )
        return override

    # Priority 2: Use configured engine from kurt.config
    try:
        config = load_config()
        configured_engine = config.INGESTION_FETCH_ENGINE.lower()

        # Validate configured engine
        if configured_engine not in KurtConfig.VALID_FETCH_ENGINES:
            # Invalid engine in config - fall back to default
            return KurtConfig.DEFAULT_FETCH_ENGINE

        # If Firecrawl is configured, verify API key is available
        if configured_engine == "firecrawl":
            firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
            if not firecrawl_api_key or firecrawl_api_key == "your_firecrawl_api_key_here":
                # Silently fall back to trafilatura if Firecrawl configured but no API key
                return KurtConfig.DEFAULT_FETCH_ENGINE

        # Return the configured engine (httpx, trafilatura, or firecrawl with valid API key)
        return configured_engine

    except Exception:
        # Priority 3: Config file not found or failed to load → use default
        return KurtConfig.DEFAULT_FETCH_ENGINE


__all__ = [
    "_get_fetch_engine",
]
