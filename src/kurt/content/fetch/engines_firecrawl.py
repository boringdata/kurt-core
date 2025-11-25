"""Firecrawl-based fetch engine.

This module provides the Firecrawl API-based fetch engine for premium content extraction.
"""

import logging
import os

logger = logging.getLogger(__name__)


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

    # Ensure we have a title - Firecrawl may use different keys
    # Try common metadata fields for title
    if "title" not in metadata and metadata:
        # Check alternate keys that might contain the title
        for key in ["ogTitle", "og:title", "twitter:title", "pageTitle"]:
            if key in metadata and metadata[key]:
                metadata["title"] = metadata[key]
                break

    return content, metadata


def fetch_batch_with_firecrawl(
    urls: list[str], max_concurrency: int = None, batch_size: int = 100
) -> dict[str, tuple[str, dict] | Exception]:
    """
    Fetch multiple URLs using Firecrawl's batch scrape API.

    This is more efficient than individual scrapes as it:
    - Uses a single API request for multiple URLs
    - Reduces rate limit issues
    - Processes URLs in parallel on Firecrawl's infrastructure

    Args:
        urls: List of URLs to fetch
        max_concurrency: Maximum concurrent scrapes (uses team default if None)
        batch_size: Maximum URLs per batch request (default: 100)

    Returns:
        Dict mapping URL to either:
            - (content_markdown, metadata_dict) on success
            - Exception on failure

    Example:
        >>> results = fetch_batch_with_firecrawl(["https://example.com", "https://example.org"])
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

    if not urls:
        return {}

    app = FirecrawlApp(api_key=api_key)
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
                    url = item.url if hasattr(item, "url") else None
                    if not url:
                        continue

                    # Extract content
                    if hasattr(item, "markdown") and item.markdown:
                        content = item.markdown

                        # Extract metadata
                        metadata = {}
                        if hasattr(item, "metadata") and item.metadata:
                            metadata = item.metadata if isinstance(item.metadata, dict) else {}

                        # Ensure we have a title - try alternate keys
                        if "title" not in metadata and metadata:
                            for key in ["ogTitle", "og:title", "twitter:title", "pageTitle"]:
                                if key in metadata and metadata[key]:
                                    metadata["title"] = metadata[key]
                                    break

                        results[url] = (content, metadata)
                        logger.debug(f"[Firecrawl] ✓ Fetched {url} ({len(content)} chars)")
                    else:
                        error = ValueError(f"[Firecrawl] No content extracted from: {url}")
                        results[url] = error
                        logger.warning(f"[Firecrawl] ✗ Failed {url}: No content")

            # Track invalid URLs
            if hasattr(batch_response, "invalid_urls") and batch_response.invalid_urls:
                for invalid_url in batch_response.invalid_urls:
                    error = ValueError(f"[Firecrawl] Invalid URL: {invalid_url}")
                    results[invalid_url] = error
                    logger.warning(f"[Firecrawl] ✗ Invalid URL: {invalid_url}")

        except Exception as e:
            # If batch fails, mark all URLs in this batch as failed
            logger.error(f"[Firecrawl] Batch {batch_num} failed: {type(e).__name__}: {str(e)}")
            for url in batch_urls:
                if url not in results:  # Don't override successful results
                    results[url] = ValueError(f"[Firecrawl] Batch error: {str(e)}")

    logger.info(
        f"[Firecrawl] Batch complete: {sum(1 for r in results.values() if not isinstance(r, Exception))}/{len(results)} successful"
    )

    return results
