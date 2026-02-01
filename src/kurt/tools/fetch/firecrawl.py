"""Firecrawl fetch provider."""

from __future__ import annotations

import os
from typing import Any

from .models import BatchFetchResult


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


def fetch_with_firecrawl(urls: str | list[str]) -> BatchFetchResult:
    """
    Fetch content using Firecrawl API.

    Supports both single URL and batch operations.

    Args:
        urls: Single URL string or list of URLs

    Returns:
        Dict mapping URL -> (content_markdown, metadata_dict) or Exception

    Raises:
        ValueError: If FIRECRAWL_API_KEY not set
    """
    from firecrawl import FirecrawlApp

    # Normalize input
    if isinstance(urls, str):
        url_list = [urls]
    else:
        url_list = urls

    if not url_list:
        return {}

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("[Firecrawl] FIRECRAWL_API_KEY not set in environment")

    app = FirecrawlApp(api_key=api_key)
    results: BatchFetchResult = {}

    try:
        # Use batch scrape - poll_interval=2 means check every 2 seconds
        batch_result = app.batch_scrape_urls(url_list, {"formats": ["markdown", "html"]}, 2)
    except Exception as e:
        raise ValueError(f"[Firecrawl] API error: {type(e).__name__}: {str(e)}") from e

    # Process results from batch response
    if hasattr(batch_result, "data") and batch_result.data:
        for doc in batch_result.data:
            # Get URL from metadata or document
            doc_url = None
            if hasattr(doc, "metadata") and doc.metadata:
                doc_url = doc.metadata.get("sourceURL") or doc.metadata.get("url")
            if not doc_url and hasattr(doc, "url"):
                doc_url = doc.url

            if not doc_url:
                continue

            # Check for markdown content
            if not hasattr(doc, "markdown") or not doc.markdown:
                results[doc_url] = ValueError(f"[Firecrawl] No content from: {doc_url}")
                continue

            content = doc.markdown
            metadata = _extract_firecrawl_metadata(doc)
            results[doc_url] = (content, metadata)

    # Mark any URLs not in results as failed
    for url in url_list:
        if url not in results:
            results[url] = ValueError(f"[Firecrawl] No result for: {url}")

    return results
