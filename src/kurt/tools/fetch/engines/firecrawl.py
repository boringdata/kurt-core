"""Firecrawl content extraction engine.

This is the canonical implementation for Firecrawl-based content fetching.
All other modules should import from here rather than duplicating implementation.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from kurt.tools.fetch.core import BaseFetcher, FetcherConfig, FetchResult


def _extract_firecrawl_metadata(result_item: Any) -> dict:
    """Extract and normalize metadata from Firecrawl response.

    Args:
        result_item: Firecrawl document object with metadata attribute

    Returns:
        Dict with normalized metadata including title if available
    """
    metadata = {}
    if hasattr(result_item, "metadata") and result_item.metadata:
        metadata = result_item.metadata if isinstance(result_item.metadata, dict) else {}

    # Normalize title from various OG/meta fields
    if "title" not in metadata and metadata:
        for key in ["ogTitle", "og:title", "twitter:title", "pageTitle"]:
            if key in metadata and metadata[key]:
                metadata["title"] = metadata[key]
                break

    return metadata


class FirecrawlFetcher(BaseFetcher):
    """Extracts content using Firecrawl API.

    Firecrawl is a paid API service that handles:
    - JavaScript rendering (headless browser)
    - Content extraction and conversion to Markdown
    - Batch scraping with automatic polling

    Requires FIRECRAWL_API_KEY environment variable to be set.

    This is the canonical implementation - use this class instead of
    the deprecated fetch_with_firecrawl() function.
    """

    name = "firecrawl"
    version = "1.0.0"
    url_patterns = ["*"]
    requires_env = ["FIRECRAWL_API_KEY"]

    from kurt.tools.fetch.providers.firecrawl.config import FirecrawlProviderConfig
    ConfigModel = FirecrawlProviderConfig

    def __init__(self, config: Optional[FetcherConfig] = None, api_key: Optional[str] = None):
        """Initialize Firecrawl fetcher.

        Args:
            config: Fetcher configuration
            api_key: Optional API key (if not provided, reads FIRECRAWL_API_KEY
                     from environment on each call)
        """
        super().__init__(config)
        self._explicit_api_key = api_key  # Only store if explicitly provided

    def _get_api_key(self) -> Optional[str]:
        """Get API key, re-reading from env if not explicitly provided.

        This allows long-lived processes to pick up env var changes.
        """
        return self._explicit_api_key or os.getenv("FIRECRAWL_API_KEY")

    def fetch(self, url: str) -> FetchResult:
        """Fetch and extract content using Firecrawl.

        Uses Firecrawl's batch_scrape_urls API for single URL fetching.
        This provides consistent behavior with batch operations.

        Args:
            url: URL to fetch

        Returns:
            FetchResult with extracted content and metadata.
            On success: content contains Markdown, metadata includes
                title and other OG tags, plus engine identifier.
            On failure: success=False, error contains description.
        """
        try:
            from firecrawl import FirecrawlApp
        except ImportError:
            return FetchResult(
                content="",
                metadata={"engine": "firecrawl"},
                success=False,
                error="[Firecrawl] firecrawl-py package not installed",
            )

        api_key = self._get_api_key()
        if not api_key:
            return FetchResult(
                content="",
                metadata={"engine": "firecrawl"},
                success=False,
                error="[Firecrawl] FIRECRAWL_API_KEY not set in environment",
            )

        try:
            app = FirecrawlApp(api_key=api_key)
            # Use batch scrape - poll_interval=2 means check every 2 seconds
            batch_result = app.batch_scrape_urls([url], {"formats": ["markdown", "html"]}, 2)
        except Exception as e:
            return FetchResult(
                content="",
                metadata={"engine": "firecrawl"},
                success=False,
                error=f"[Firecrawl] API error: {type(e).__name__}: {str(e)}",
            )

        # Process results from batch response
        if hasattr(batch_result, "data") and batch_result.data:
            for doc in batch_result.data:
                # Get URL from metadata or document
                doc_url = None
                if hasattr(doc, "metadata") and doc.metadata:
                    doc_url = doc.metadata.get("sourceURL") or doc.metadata.get("url")
                if not doc_url and hasattr(doc, "url"):
                    doc_url = doc.url

                # Check if this doc matches our URL
                if doc_url != url:
                    continue

                # Check for markdown content
                if not hasattr(doc, "markdown") or not doc.markdown:
                    return FetchResult(
                        content="",
                        metadata={"engine": "firecrawl"},
                        success=False,
                        error=f"[Firecrawl] No content from: {url}",
                    )

                content = doc.markdown
                metadata = _extract_firecrawl_metadata(doc)
                metadata["engine"] = "firecrawl"

                return FetchResult(
                    content=content,
                    metadata=metadata,
                    success=True,
                )

        # URL not found in results
        return FetchResult(
            content="",
            metadata={"engine": "firecrawl"},
            success=False,
            error=f"[Firecrawl] No result for: {url}",
        )

    def fetch_batch(self, urls: list[str]) -> dict[str, FetchResult]:
        """Fetch multiple URLs using Firecrawl batch API.

        This method provides efficient batch fetching using Firecrawl's
        native batch_scrape_urls API.

        Args:
            urls: List of URLs to fetch

        Returns:
            Dict mapping URL to FetchResult
        """
        results: dict[str, FetchResult] = {}

        if not urls:
            return results

        try:
            from firecrawl import FirecrawlApp
        except ImportError:
            for url in urls:
                results[url] = FetchResult(
                    content="",
                    metadata={"engine": "firecrawl"},
                    success=False,
                    error="[Firecrawl] firecrawl-py package not installed",
                )
            return results

        api_key = self._get_api_key()
        if not api_key:
            for url in urls:
                results[url] = FetchResult(
                    content="",
                    metadata={"engine": "firecrawl"},
                    success=False,
                    error="[Firecrawl] FIRECRAWL_API_KEY not set in environment",
                )
            return results

        try:
            app = FirecrawlApp(api_key=api_key)
            batch_result = app.batch_scrape_urls(urls, {"formats": ["markdown", "html"]}, 2)
        except Exception as e:
            for url in urls:
                results[url] = FetchResult(
                    content="",
                    metadata={"engine": "firecrawl"},
                    success=False,
                    error=f"[Firecrawl] API error: {type(e).__name__}: {str(e)}",
                )
            return results

        # Process batch results
        if hasattr(batch_result, "data") and batch_result.data:
            for doc in batch_result.data:
                doc_url = None
                if hasattr(doc, "metadata") and doc.metadata:
                    doc_url = doc.metadata.get("sourceURL") or doc.metadata.get("url")
                if not doc_url and hasattr(doc, "url"):
                    doc_url = doc.url

                if not doc_url:
                    continue

                if not hasattr(doc, "markdown") or not doc.markdown:
                    results[doc_url] = FetchResult(
                        content="",
                        metadata={"engine": "firecrawl"},
                        success=False,
                        error=f"[Firecrawl] No content from: {doc_url}",
                    )
                    continue

                content = doc.markdown
                metadata = _extract_firecrawl_metadata(doc)
                metadata["engine"] = "firecrawl"

                results[doc_url] = FetchResult(
                    content=content,
                    metadata=metadata,
                    success=True,
                )

        # Mark any missing URLs as failed
        for url in urls:
            if url not in results:
                results[url] = FetchResult(
                    content="",
                    metadata={"engine": "firecrawl"},
                    success=False,
                    error=f"[Firecrawl] No result for: {url}",
                )

        return results

    def fetch_raw(self, urls: str | list[str]) -> dict[str, tuple[str, dict] | Exception]:
        """Fetch content and return as dict of tuples (for backward compatibility).

        This method provides the same interface as the deprecated
        fetch_with_firecrawl() function for backward compatibility.

        Args:
            urls: Single URL string or list of URLs

        Returns:
            Dict mapping URL -> (content_markdown, metadata_dict) or Exception
        """
        # Normalize input
        if isinstance(urls, str):
            url_list = [urls]
        else:
            url_list = list(urls)

        if not url_list:
            return {}

        # Use batch fetch internally
        fetch_results = self.fetch_batch(url_list)

        # Convert to raw format
        raw_results: dict[str, tuple[str, dict] | Exception] = {}
        for url, result in fetch_results.items():
            if result.success:
                raw_results[url] = (result.content, result.metadata)
            else:
                raw_results[url] = ValueError(result.error or f"Fetch failed for {url}")

        return raw_results


# Backwards compatibility alias
FirecrawlEngine = FirecrawlFetcher
