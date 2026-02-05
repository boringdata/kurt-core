"""Firecrawl fetch provider.

DEPRECATED: This module is deprecated. Use FirecrawlFetcher from
kurt.tools.fetch.engines.firecrawl instead.

This module is kept for backward compatibility and will be removed in a future release.
"""

from __future__ import annotations

import warnings

from .models import BatchFetchResult

# Import the canonical implementation
from .engines.firecrawl import FirecrawlFetcher

# Module-level singleton for backward compatibility
_fetcher: FirecrawlFetcher | None = None


def _get_fetcher() -> FirecrawlFetcher:
    """Get or create the module-level fetcher singleton."""
    global _fetcher
    if _fetcher is None:
        _fetcher = FirecrawlFetcher()
    return _fetcher


def fetch_with_firecrawl(urls: str | list[str]) -> BatchFetchResult:
    """
    Fetch content using Firecrawl API.

    DEPRECATED: Use FirecrawlFetcher.fetch() or FirecrawlFetcher.fetch_raw() instead.

    This function is kept for backward compatibility. New code should use:
        from kurt.tools.fetch.engines.firecrawl import FirecrawlFetcher
        fetcher = FirecrawlFetcher()
        result = fetcher.fetch(url)  # Returns FetchResult object
        # Or for batch operations with tuple format:
        results = fetcher.fetch_raw(urls)

    Args:
        urls: Single URL string or list of URLs

    Returns:
        Dict mapping URL -> (content_markdown, metadata_dict) or Exception
    """
    warnings.warn(
        "fetch_with_firecrawl() is deprecated. "
        "Use FirecrawlFetcher from kurt.tools.fetch.engines.firecrawl instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _get_fetcher().fetch_raw(urls)
