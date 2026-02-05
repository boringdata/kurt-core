"""Tavily extract fetch provider.

DEPRECATED: This module is deprecated. Use TavilyFetcher from
kurt.tools.fetch.engines.tavily instead.

This module is kept for backward compatibility and will be removed in a future release.
"""

from __future__ import annotations

import warnings

from .models import BatchFetchResult

# Import the canonical implementation
from .engines.tavily import TavilyFetcher

# Module-level singleton for backward compatibility
_fetcher: TavilyFetcher | None = None


def _get_fetcher() -> TavilyFetcher:
    """Get or create the module-level fetcher singleton."""
    global _fetcher
    if _fetcher is None:
        _fetcher = TavilyFetcher()
    return _fetcher


def fetch_with_tavily(urls: str | list[str]) -> BatchFetchResult:
    """
    Fetch content using Tavily Extract API.

    DEPRECATED: Use TavilyFetcher.fetch() or TavilyFetcher.fetch_raw() instead.

    This function is kept for backward compatibility. New code should use:
        from kurt.tools.fetch.engines.tavily import TavilyFetcher
        fetcher = TavilyFetcher()
        result = fetcher.fetch(url)  # Returns FetchResult object
        # Or for batch operations with tuple format:
        results = fetcher.fetch_raw(urls)

    Args:
        urls: Single URL string or list of URLs (max 20)

    Returns:
        Dict mapping URL -> (content_markdown, metadata_dict) or Exception

    Raises:
        ValueError: If TAVILY_API_KEY not set or batch exceeds 20 URLs
    """
    warnings.warn(
        "fetch_with_tavily() is deprecated. "
        "Use TavilyFetcher from kurt.tools.fetch.engines.tavily instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _get_fetcher().fetch_raw(urls)
