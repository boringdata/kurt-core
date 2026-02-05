"""HTTPX content fetching engine.

This is the canonical implementation for HTTPX-based content fetching.
All other modules should import from here rather than duplicating implementation.
"""

from __future__ import annotations

from typing import Optional

import httpx

from kurt.tools.fetch.core import BaseFetcher, FetcherConfig, FetchResult
from kurt.tools.fetch.utils import extract_with_trafilatura


class HttpxFetcher(BaseFetcher):
    """Fetches content using HTTPX library with trafilatura extraction.

    HTTPX is a free, local HTTP library that:
    - Supports HTTP/2 and connection pooling
    - Works well with proxies (useful when trafilatura is blocked)
    - Uses trafilatura for content extraction (same as TrafilaturaFetcher)

    Use this when you need proxy support or trafilatura.fetch_url() is failing.

    This is the canonical implementation - use this class instead of
    the deprecated fetch_with_httpx() function.
    """

    def __init__(self, config: Optional[FetcherConfig] = None):
        """Initialize HTTPX fetcher.

        Args:
            config: Fetcher configuration (timeout, etc.)
        """
        super().__init__(config)

    def fetch(self, url: str) -> FetchResult:
        """Fetch and extract content using HTTPX + trafilatura.

        Downloads the URL using httpx.get() and extracts content
        using trafilatura extraction utilities.

        Args:
            url: URL to fetch

        Returns:
            FetchResult with extracted content and metadata.
            On success: content contains Markdown, metadata includes
                title, author, date, description, fingerprint, engine.
            On failure: success=False, error contains description.
        """
        # Determine timeout from config or use default
        timeout = 30.0
        if self.config:
            timeout = self.config.timeout

        try:
            response = httpx.get(url, follow_redirects=True, timeout=timeout)
            response.raise_for_status()
            downloaded = response.text
        except httpx.HTTPStatusError as e:
            return FetchResult(
                content="",
                metadata={"engine": "httpx"},
                success=False,
                error=f"[httpx] HTTP {e.response.status_code}: {url}",
            )
        except httpx.TimeoutException:
            return FetchResult(
                content="",
                metadata={"engine": "httpx"},
                success=False,
                error=f"[httpx] Timeout fetching: {url}",
            )
        except httpx.RequestError as e:
            return FetchResult(
                content="",
                metadata={"engine": "httpx"},
                success=False,
                error=f"[httpx] Request error: {type(e).__name__}: {str(e)}",
            )
        except Exception as e:
            return FetchResult(
                content="",
                metadata={"engine": "httpx"},
                success=False,
                error=f"[httpx] Download error: {type(e).__name__}: {str(e)}",
            )

        if not downloaded:
            return FetchResult(
                content="",
                metadata={"engine": "httpx"},
                success=False,
                error=f"[httpx] No content from: {url}",
            )

        try:
            # Extract content and metadata using shared trafilatura utility
            content, metadata = extract_with_trafilatura(downloaded, url)
            metadata["engine"] = "httpx"

            return FetchResult(
                content=content,
                metadata=metadata,
                success=True,
            )
        except ValueError as e:
            # ValueError from extract_with_trafilatura (no content extracted)
            return FetchResult(
                content="",
                metadata={"engine": "httpx"},
                success=False,
                error=str(e),
            )
        except Exception as e:
            return FetchResult(
                content="",
                metadata={"engine": "httpx"},
                success=False,
                error=f"[httpx] Extraction error: {type(e).__name__}: {str(e)}",
            )

    def fetch_raw(self, url: str) -> tuple[str, dict]:
        """Fetch content and return as tuple (for backward compatibility).

        This method provides the same interface as the deprecated
        fetch_with_httpx() function for backward compatibility.

        Args:
            url: URL to fetch

        Returns:
            Tuple of (content_markdown, metadata_dict)

        Raises:
            ValueError: If fetch fails or no content extracted
        """
        result = self.fetch(url)
        if not result.success:
            raise ValueError(result.error or "Fetch failed")
        return result.content, result.metadata


# Backwards compatibility alias
HttpxEngine = HttpxFetcher
