"""Firecrawl-based fetch engine.

This module provides the Firecrawl API-based fetch engine for premium content extraction.
"""

import logging
import os
from typing import Any

from kurt.content.fetch.constants import FIRECRAWL_DEFAULT_BATCH_SIZE

logger = logging.getLogger(__name__)


def _extract_metadata(result_item: Any) -> dict:
    """Extract and normalize metadata from Firecrawl response."""
    metadata = {}
    if hasattr(result_item, "metadata") and result_item.metadata:
        metadata = result_item.metadata if isinstance(result_item.metadata, dict) else {}

    # Ensure we have a title - Firecrawl may use different keys
    if "title" not in metadata and metadata:
        for key in ["ogTitle", "og:title", "twitter:title", "pageTitle"]:
            if key in metadata and metadata[key]:
                metadata["title"] = metadata[key]
                break

    return metadata


def fetch_with_firecrawl(
    url: str | list[str],
    max_concurrency: int = None,
    batch_size: int = FIRECRAWL_DEFAULT_BATCH_SIZE,
) -> tuple[str, dict] | dict[str, tuple[str, dict] | Exception]:
    """
    Fetch content using Firecrawl API.

    Supports both single URL and batch fetching. When multiple URLs are provided,
    uses Firecrawl's batch API which is more efficient and reduces rate limiting.

    Args:
        url: Single URL string or list of URLs to fetch
        max_concurrency: For batch mode only - max concurrent scrapes (uses team default if None)
        batch_size: For batch mode only - max URLs per batch request (default: 100)

    Returns:
        - Single URL: Tuple of (content_markdown, metadata_dict)
        - Multiple URLs: Dict mapping URL to either (content_markdown, metadata_dict) or Exception

    Raises:
        ValueError: If single URL fetch fails or FIRECRAWL_API_KEY not set

    Examples:
        Single URL:
        >>> content, metadata = fetch_with_firecrawl("https://example.com")

        Multiple URLs (batch mode):
        >>> results = fetch_with_firecrawl(["https://example.com", "https://example.org"])
        >>> for url, result in results.items():
        ...     if isinstance(result, Exception):
        ...         print(f"Failed {url}: {result}")
        ...     else:
        ...         content, metadata = result
        ...         print(f"Success {url}: {len(content)} chars")
    """
    from firecrawl import FirecrawlApp

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("[Firecrawl] FIRECRAWL_API_KEY not set in environment")

    app = FirecrawlApp(api_key=api_key)

    # Single URL mode - use scrape API
    if isinstance(url, str):
        try:
            result = app.scrape(url, formats=["markdown", "html"])
        except Exception as e:
            raise ValueError(f"[Firecrawl] API error: {type(e).__name__}: {str(e)}") from e

        if not result or not hasattr(result, "markdown"):
            raise ValueError(f"[Firecrawl] No content extracted from: {url}")

        content = result.markdown
        metadata = _extract_metadata(result)

        return content, metadata

    # Batch mode - use batch_scrape API
    urls = url
    if not urls:
        return {}

    results = {}

    # Process URLs in batches to avoid potential size limits
    for i in range(0, len(urls), batch_size):
        batch_urls = urls[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(urls) + batch_size - 1) // batch_size

        logger.info(
            f"[Firecrawl] Batch {batch_num}/{total_batches}: Scraping {len(batch_urls)} URLs"
        )

        try:
            # Use batch_scrape (synchronous - waits for completion)
            batch_response = app.batch_scrape(
                urls=batch_urls,
                formats=["markdown", "html"],
                max_concurrency=max_concurrency,
                ignore_invalid_urls=True,
            )

            # Process successful results
            if hasattr(batch_response, "data") and batch_response.data:
                for item in batch_response.data:
                    item_url = item.url if hasattr(item, "url") else None
                    if not item_url:
                        continue

                    # Extract content
                    if hasattr(item, "markdown") and item.markdown:
                        content = item.markdown
                        metadata = _extract_metadata(item)

                        results[item_url] = (content, metadata)
                        logger.debug(f"[Firecrawl] ✓ Fetched {item_url} ({len(content)} chars)")
                    else:
                        error = ValueError(f"[Firecrawl] No content extracted from: {item_url}")
                        results[item_url] = error
                        logger.warning(f"[Firecrawl] ✗ Failed {item_url}: No content")

            # Track invalid URLs
            if hasattr(batch_response, "invalid_urls") and batch_response.invalid_urls:
                for invalid_url in batch_response.invalid_urls:
                    error = ValueError(f"[Firecrawl] Invalid URL: {invalid_url}")
                    results[invalid_url] = error
                    logger.warning(f"[Firecrawl] ✗ Invalid URL: {invalid_url}")

        except Exception as e:
            # If batch fails, mark all URLs in this batch as failed
            logger.error(f"[Firecrawl] Batch {batch_num} failed: {type(e).__name__}: {str(e)}")
            for batch_url in batch_urls:
                if batch_url not in results:  # Don't override successful results
                    results[batch_url] = ValueError(f"[Firecrawl] Batch error: {str(e)}")

    logger.info(
        f"[Firecrawl] Batch complete: {sum(1 for r in results.values() if not isinstance(r, Exception))}/{len(results)} successful"
    )

    return results
