"""
Web fetching business logic.

This module provides business logic for fetching content from web URLs.
NO DATABASE OPERATIONS - pure Network I/O.
"""

import logging

from kurt.content.paths import parse_source_identifier
from kurt.integrations.fetch_engines import (
    fetch_with_firecrawl,
    fetch_with_httpx,
    fetch_with_trafilatura,
)

logger = logging.getLogger(__name__)


def fetch_from_web(source_url: str, fetch_engine: str) -> tuple[str, dict]:
    """
    Fetch content from web URL using specified engine.

    Pure business logic - Network I/O only, no DB operations.
    Workflows call this function and handle DB operations separately.

    Args:
        source_url: Web URL to fetch
        fetch_engine: Engine to use ('firecrawl', 'trafilatura', 'httpx')

    Returns:
        Tuple of (markdown_content, metadata_dict)

    Raises:
        ValueError: If URL looks like CMS pattern or fetch fails

    Example:
        >>> content, metadata = fetch_from_web(
        ...     "https://example.com/page1", "firecrawl"
        ... )
        >>> # Returns: ("# Title\n\nContent...", {"title": "...", ...})
    """
    # Check if it looks like a CMS URL pattern (legacy check)
    source_type, parsed_data = parse_source_identifier(source_url)

    if source_type == "cms":
        raise ValueError(
            f"CMS URL pattern detected but missing platform/instance fields. "
            f"URL: {source_url}. Please recreate this document using 'kurt content map cms'."
        )

    # Standard web fetch
    if fetch_engine == "firecrawl":
        return fetch_with_firecrawl(source_url)
    elif fetch_engine == "httpx":
        return fetch_with_httpx(source_url)
    else:
        return fetch_with_trafilatura(source_url)


__all__ = [
    "fetch_from_web",
]
