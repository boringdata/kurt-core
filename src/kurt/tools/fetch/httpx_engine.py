"""HTTPX fetch provider (proxy-friendly, uses trafilatura for extraction).

DEPRECATED: This module is deprecated. Use HttpxFetcher from
kurt.tools.fetch.engines.httpx instead.

This module is kept for backward compatibility and will be removed in a future release.
"""

from __future__ import annotations

import warnings

from .models import FetchResult

# Import the canonical implementation
from .engines.httpx import HttpxFetcher

# Module-level singleton for backward compatibility
_fetcher = HttpxFetcher()


def fetch_with_httpx(url: str) -> FetchResult:
    """
    Fetch content using httpx + trafilatura extraction (proxy-friendly).

    DEPRECATED: Use HttpxFetcher.fetch() or HttpxFetcher.fetch_raw() instead.

    This function is kept for backward compatibility. New code should use:
        from kurt.tools.fetch.engines.httpx import HttpxFetcher
        fetcher = HttpxFetcher()
        result = fetcher.fetch(url)  # Returns FetchResult object
        # Or for tuple format:
        content, metadata = fetcher.fetch_raw(url)

    Args:
        url: URL to fetch

    Returns:
        Tuple of (content_markdown, metadata_dict)

    Raises:
        ValueError: If fetch fails
    """
    warnings.warn(
        "fetch_with_httpx() is deprecated. "
        "Use HttpxFetcher from kurt.tools.fetch.engines.httpx instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _fetcher.fetch_raw(url)
