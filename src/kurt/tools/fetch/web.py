"""Web fetching - router for fetch providers."""

from __future__ import annotations

from .firecrawl import fetch_with_firecrawl
from .httpx import fetch_with_httpx
from .models import BatchFetchResult
from .tavily import fetch_with_tavily
from .trafilatura import fetch_with_trafilatura


def fetch_from_web(urls: list[str], fetch_engine: str) -> BatchFetchResult:
    """
    Fetch content from web URLs using specified engine.

    Processing strategy depends on engine:
    - httpx/trafilatura: Sequential processing (no native batch support)
    - tavily/firecrawl: Native batch API (single call with all URLs)

    Note: For parallel processing of httpx/trafilatura, use DBOS Queue at
    the workflow level (see steps.py). This function is a simple router
    that can be called from anywhere.

    Args:
        urls: List of URLs to fetch
        fetch_engine: Engine to use ('trafilatura', 'httpx', 'firecrawl', 'tavily')

    Returns:
        Dict mapping URL -> (markdown_content, metadata_dict) or Exception
    """
    if not urls:
        return {}

    results: BatchFetchResult = {}

    if fetch_engine == "tavily":
        # Tavily has native batch API (up to 20 URLs)
        try:
            results = fetch_with_tavily(urls)
        except Exception as e:
            # Return all URLs as failed
            return {url: e for url in urls}
    elif fetch_engine == "firecrawl":
        # Firecrawl has native batch API
        try:
            results = fetch_with_firecrawl(urls)
        except Exception as e:
            # Return all URLs as failed
            return {url: e for url in urls}
    elif fetch_engine == "httpx":
        # httpx processes URLs sequentially
        for url in urls:
            try:
                results[url] = fetch_with_httpx(url)
            except Exception as e:
                results[url] = e
    else:
        # trafilatura (default) processes URLs sequentially
        for url in urls:
            try:
                results[url] = fetch_with_trafilatura(url)
            except Exception as e:
                results[url] = e

    return results
