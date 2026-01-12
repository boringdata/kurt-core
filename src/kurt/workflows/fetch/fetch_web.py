"""Web fetching - router for fetch providers."""

from __future__ import annotations

from .fetch_firecrawl import fetch_with_firecrawl
from .fetch_httpx import fetch_with_httpx
from .fetch_trafilatura import fetch_with_trafilatura


def fetch_from_web(source_url: str, fetch_engine: str) -> tuple[str, dict]:
    """
    Fetch content from web URL using specified engine.

    Args:
        source_url: Web URL to fetch
        fetch_engine: Engine to use ('firecrawl', 'trafilatura', 'httpx')

    Returns:
        Tuple of (markdown_content, metadata_dict)

    Raises:
        ValueError: If fetch fails
    """
    if fetch_engine == "firecrawl":
        return fetch_with_firecrawl(source_url)
    elif fetch_engine == "httpx":
        return fetch_with_httpx(source_url)
    else:
        return fetch_with_trafilatura(source_url)
