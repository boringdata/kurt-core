"""Tavily content extraction engine.

This is the canonical implementation for Tavily-based content fetching.
All other modules should import from here rather than duplicating implementation.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

from kurt.tools.fetch.core.base import BaseFetcher, FetcherConfig, FetchResult


def _extract_tavily_metadata(result_item: dict[str, Any], response_data: dict) -> dict:
    """Extract and normalize metadata from Tavily extract response.

    Args:
        result_item: Single result item from Tavily response
        response_data: Full response data containing request metadata

    Returns:
        Dict with normalized metadata including source_url, favicon, images, etc.
    """
    metadata = {}

    if "url" in result_item:
        metadata["source_url"] = result_item["url"]

    if "favicon" in result_item and result_item["favicon"]:
        metadata["favicon"] = result_item["favicon"]

    if "images" in result_item and result_item["images"]:
        metadata["images"] = result_item["images"]

    # Add response-level metadata
    if "response_time" in response_data:
        metadata["response_time"] = response_data["response_time"]
    if "request_id" in response_data:
        metadata["request_id"] = response_data["request_id"]

    return metadata


class TavilyFetcher(BaseFetcher):
    """Retrieves content using Tavily Extract API.

    Tavily is a paid API service that provides:
    - Fast content extraction with Markdown formatting
    - Batch processing support (up to 20 URLs per request)
    - Image extraction and metadata

    Requires TAVILY_API_KEY environment variable to be set.

    This is the canonical implementation - use this class instead of
    the deprecated fetch_with_tavily() function.
    """

    name = "tavily"
    version = "1.0.0"
    url_patterns = ["*"]
    requires_env = ["TAVILY_API_KEY"]

    from kurt.tools.fetch.providers.tavily.config import TavilyProviderConfig
    ConfigModel = TavilyProviderConfig

    def __init__(self, config: Optional[FetcherConfig] = None, api_key: Optional[str] = None):
        """Initialize Tavily fetcher.

        Args:
            config: Fetcher configuration
            api_key: Optional API key (defaults to TAVILY_API_KEY env var)
        """
        super().__init__(config)
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")

    def fetch(self, url: str) -> FetchResult:
        """Fetch content using Tavily Extract API.

        Args:
            url: URL to fetch

        Returns:
            FetchResult with extracted content and metadata.
            On success: content contains Markdown, metadata includes
                source_url, favicon, images, response_time, etc.
            On failure: success=False, error contains description.
        """
        if not self.api_key:
            return FetchResult(
                content="",
                metadata={"engine": "tavily"},
                success=False,
                error="[Tavily] TAVILY_API_KEY not set in environment",
            )

        # Use batch fetch internally for consistency
        results = self._fetch_batch_internal([url])

        if url in results:
            return results[url]

        return FetchResult(
            content="",
            metadata={"engine": "tavily"},
            success=False,
            error=f"[Tavily] No result for: {url}",
        )

    def fetch_batch(self, urls: list[str]) -> dict[str, FetchResult]:
        """Fetch multiple URLs using Tavily Extract API.

        Tavily supports up to 20 URLs per request. If more URLs are provided,
        they will be split into batches.

        Args:
            urls: List of URLs to fetch (batched if > 20)

        Returns:
            Dict mapping URL to FetchResult
        """
        if not urls:
            return {}

        if not self.api_key:
            results: dict[str, FetchResult] = {}
            for url in urls:
                results[url] = FetchResult(
                    content="",
                    metadata={"engine": "tavily"},
                    success=False,
                    error="[Tavily] TAVILY_API_KEY not set in environment",
                )
            return results

        # Process in batches of 20 (Tavily limit)
        all_results: dict[str, FetchResult] = {}
        for i in range(0, len(urls), 20):
            batch = urls[i : i + 20]
            batch_results = self._fetch_batch_internal(batch)
            all_results.update(batch_results)

        return all_results

    def _fetch_batch_internal(self, url_list: list[str]) -> dict[str, FetchResult]:
        """Internal batch fetch implementation (max 20 URLs).

        Args:
            url_list: List of URLs to fetch (must be <= 20)

        Returns:
            Dict mapping URL to FetchResult
        """
        results: dict[str, FetchResult] = {}

        if not url_list:
            return results

        # Tavily extract API endpoint
        api_url = "https://api.tavily.com/extract"

        payload = {
            "urls": url_list if len(url_list) > 1 else url_list[0],
            "format": "markdown",
            "extract_depth": "advanced",
            "include_images": True,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Adjust timeout based on batch size
        timeout = 60.0 + (len(url_list) - 1) * 5.0  # 60s base + 5s per additional URL

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(api_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            error = self._map_http_error(e)
            for url in url_list:
                results[url] = FetchResult(
                    content="",
                    metadata={"engine": "tavily"},
                    success=False,
                    error=error,
                )
            return results
        except httpx.RequestError as e:
            error = f"[Tavily] Request error: {type(e).__name__}: {str(e)}"
            for url in url_list:
                results[url] = FetchResult(
                    content="",
                    metadata={"engine": "tavily"},
                    success=False,
                    error=error,
                )
            return results
        except Exception as e:
            error = f"[Tavily] Unexpected error: {type(e).__name__}: {str(e)}"
            for url in url_list:
                results[url] = FetchResult(
                    content="",
                    metadata={"engine": "tavily"},
                    success=False,
                    error=error,
                )
            return results

        # Process successful results
        for result in data.get("results", []):
            result_url = result.get("url", "")
            content = result.get("raw_content", "")

            if not result_url:
                continue

            if not content or not content.strip():
                results[result_url] = FetchResult(
                    content="",
                    metadata={"engine": "tavily"},
                    success=False,
                    error=f"[Tavily] Empty content from: {result_url}",
                )
                continue

            metadata = _extract_tavily_metadata(result, data)
            metadata["engine"] = "tavily"

            results[result_url] = FetchResult(
                content=content,
                metadata=metadata,
                success=True,
            )

        # Process failed results
        for failed in data.get("failed_results", []):
            if isinstance(failed, dict):
                failed_url = failed.get("url", "")
                error_msg = failed.get("error", "Unknown error")
                if failed_url:
                    results[failed_url] = FetchResult(
                        content="",
                        metadata={"engine": "tavily"},
                        success=False,
                        error=f"[Tavily] {failed_url}: {error_msg}",
                    )
            elif isinstance(failed, str):
                results[failed] = FetchResult(
                    content="",
                    metadata={"engine": "tavily"},
                    success=False,
                    error=f"[Tavily] Failed: {failed}",
                )

        # Mark any requested URLs not in results as failed
        for url in url_list:
            if url not in results:
                results[url] = FetchResult(
                    content="",
                    metadata={"engine": "tavily"},
                    success=False,
                    error=f"[Tavily] No result for: {url}",
                )

        return results

    def _map_http_error(self, e: httpx.HTTPStatusError) -> str:
        """Map HTTP status codes to user-friendly error messages."""
        status_code = e.response.status_code
        if status_code == 401:
            return "[Tavily] Invalid API key"
        elif status_code == 403:
            return "[Tavily] URL not supported"
        elif status_code == 429:
            return "[Tavily] Rate limit exceeded"
        elif status_code in (432, 433):
            return "[Tavily] Credit or plan limit exceeded"
        else:
            return f"[Tavily] API error ({status_code}): {e}"

    def fetch_raw(self, urls: str | list[str]) -> dict[str, tuple[str, dict] | Exception]:
        """Fetch content and return as dict of tuples (for backward compatibility).

        This method provides the same interface as the deprecated
        fetch_with_tavily() function for backward compatibility.

        Args:
            urls: Single URL string or list of URLs

        Returns:
            Dict mapping URL -> (content_markdown, metadata_dict) or Exception

        Raises:
            ValueError: If batch exceeds 20 URLs
        """
        # Normalize input
        if isinstance(urls, str):
            url_list = [urls]
        else:
            url_list = list(urls)

        if not url_list:
            return {}

        if len(url_list) > 20:
            raise ValueError("[Tavily] Maximum 20 URLs per request")

        if not self.api_key:
            raise ValueError("[Tavily] TAVILY_API_KEY not set in environment")

        # Use batch fetch internally
        fetch_results = self._fetch_batch_internal(url_list)

        # Convert to raw format
        raw_results: dict[str, tuple[str, dict] | Exception] = {}
        for url, result in fetch_results.items():
            if result.success:
                raw_results[url] = (result.content, result.metadata)
            else:
                raw_results[url] = ValueError(result.error or f"Fetch failed for {url}")

        return raw_results


# Backwards compatibility alias
TavilyEngine = TavilyFetcher
