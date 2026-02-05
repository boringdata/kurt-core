"""Web fetching - router for fetch providers."""

from __future__ import annotations

import warnings

from .engines.firecrawl import FirecrawlFetcher
from .engines.httpx import HttpxFetcher
from .engines.tavily import TavilyFetcher
from .engines.trafilatura import TrafilaturaFetcher
from .models import BatchFetchResult


def fetch_from_web(urls: list[str], fetch_engine: str) -> BatchFetchResult:
    """
    Fetch content from web URLs using specified engine.

    DEPRECATED: This function is deprecated. Use the engine classes directly:
        from kurt.tools.fetch.engines import TavilyFetcher, FirecrawlFetcher, etc.

    Processing strategy depends on engine:
    - httpx/trafilatura: Sequential processing (no native batch support)
    - tavily/firecrawl: Native batch API (single call with all URLs)

    For parallel processing, use the workflow orchestration layer.
    This function is a simple router that can be called from anywhere.

    Args:
        urls: List of URLs to fetch
        fetch_engine: Engine to use ('trafilatura', 'httpx', 'firecrawl', 'tavily')

    Returns:
        Dict mapping URL -> (markdown_content, metadata_dict) or Exception
    """
    warnings.warn(
        "fetch_from_web() is deprecated. "
        "Use engine classes from kurt.tools.fetch.engines instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    if not urls:
        return {}

    results: BatchFetchResult = {}

    if fetch_engine == "tavily":
        # Tavily has native batch API (up to 20 URLs)
        fetcher = TavilyFetcher()
        try:
            results = fetcher.fetch_raw(urls)
        except Exception as e:
            # Return all URLs as failed
            return {url: e for url in urls}
    elif fetch_engine == "firecrawl":
        # Firecrawl has native batch API
        fetcher = FirecrawlFetcher()
        try:
            results = fetcher.fetch_raw(urls)
        except Exception as e:
            # Return all URLs as failed
            return {url: e for url in urls}
    elif fetch_engine == "httpx":
        # httpx processes URLs sequentially
        fetcher = HttpxFetcher()
        for url in urls:
            try:
                results[url] = fetcher.fetch_raw(url)
            except Exception as e:
                results[url] = e
    else:
        # trafilatura (default) processes URLs sequentially
        fetcher = TrafilaturaFetcher()
        for url in urls:
            try:
                results[url] = fetcher.fetch_raw(url)
            except Exception as e:
                results[url] = e

    return results
