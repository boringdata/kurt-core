"""Trafilatura fetch provider.

DEPRECATED: This module is deprecated. Use TrafilaturaFetcher from
kurt.tools.fetch.engines.trafilatura instead.

This module is kept for backward compatibility and will be removed in a future release.
"""

from __future__ import annotations

import warnings

from .models import FetchResult

# Import the canonical implementation
from .engines.trafilatura import TrafilaturaFetcher

# Module-level singleton for backward compatibility
_fetcher = TrafilaturaFetcher()


def fetch_with_trafilatura(url: str) -> FetchResult:
    """
    Fetch content using Trafilatura (free, local extraction).

    DEPRECATED: Use TrafilaturaFetcher.fetch() or TrafilaturaFetcher.fetch_raw() instead.

    This function is kept for backward compatibility. New code should use:
        from kurt.tools.fetch.engines.trafilatura import TrafilaturaFetcher
        fetcher = TrafilaturaFetcher()
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
        "fetch_with_trafilatura() is deprecated. "
        "Use TrafilaturaFetcher from kurt.tools.fetch.engines.trafilatura instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _fetcher.fetch_raw(url)
