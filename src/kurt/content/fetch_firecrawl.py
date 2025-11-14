"""Firecrawl-based fetch engine.

This module provides the Firecrawl API-based fetch engine for premium content extraction.
"""

import os


def fetch_with_firecrawl(url: str) -> tuple[str, dict]:
    """
    Fetch content using Firecrawl API.

    Args:
        url: URL to fetch

    Returns:
        Tuple of (content_markdown, metadata_dict)

    Raises:
        ValueError: If fetch fails
    """
    from firecrawl import FirecrawlApp

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("[Firecrawl] FIRECRAWL_API_KEY not set in environment")

    try:
        app = FirecrawlApp(api_key=api_key)
        # Scrape the URL and get markdown using the v2 API
        result = app.scrape(url, formats=["markdown", "html"])
    except Exception as e:
        raise ValueError(f"[Firecrawl] API error: {type(e).__name__}: {str(e)}") from e

    if not result or not hasattr(result, "markdown"):
        raise ValueError(f"[Firecrawl] No content extracted from: {url}")

    content = result.markdown

    # Extract metadata from Firecrawl response
    metadata = {}
    if hasattr(result, "metadata") and result.metadata:
        metadata = result.metadata if isinstance(result.metadata, dict) else {}

    return content, metadata
