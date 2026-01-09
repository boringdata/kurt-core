"""Firecrawl fetch provider."""

from __future__ import annotations

import os
from typing import Any


def _extract_firecrawl_metadata(result_item: Any) -> dict:
    """Extract and normalize metadata from Firecrawl response."""
    metadata = {}
    if hasattr(result_item, "metadata") and result_item.metadata:
        metadata = result_item.metadata if isinstance(result_item.metadata, dict) else {}

    if "title" not in metadata and metadata:
        for key in ["ogTitle", "og:title", "twitter:title", "pageTitle"]:
            if key in metadata and metadata[key]:
                metadata["title"] = metadata[key]
                break

    return metadata


def fetch_with_firecrawl(url: str) -> tuple[str, dict]:
    """
    Fetch content using Firecrawl API.

    Args:
        url: URL to fetch

    Returns:
        Tuple of (content_markdown, metadata_dict)

    Raises:
        ValueError: If fetch fails or FIRECRAWL_API_KEY not set
    """
    from firecrawl import FirecrawlApp

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("[Firecrawl] FIRECRAWL_API_KEY not set in environment")

    app = FirecrawlApp(api_key=api_key)

    try:
        result = app.scrape(url, formats=["markdown", "html"])
    except Exception as e:
        raise ValueError(f"[Firecrawl] API error: {type(e).__name__}: {str(e)}") from e

    if not result or not hasattr(result, "markdown"):
        raise ValueError(f"[Firecrawl] No content extracted from: {url}")

    content = result.markdown
    metadata = _extract_firecrawl_metadata(result)

    return content, metadata
