"""Trafilatura content extraction engine.

This is the canonical implementation for Trafilatura-based content fetching.
All other modules should import from here rather than duplicating implementation.
"""

from __future__ import annotations

import trafilatura

from kurt.tools.fetch.core import BaseFetcher, FetchResult
from kurt.tools.fetch.utils import extract_with_trafilatura


class TrafilaturaFetcher(BaseFetcher):
    """Extracts content using Trafilatura library.

    Trafilatura is a free, local extraction library that handles:
    - HTTP fetching via trafilatura.fetch_url()
    - HTML content extraction and conversion to Markdown
    - Metadata extraction (title, author, date, description, fingerprint)

    Note: This fetcher does NOT perform pre-fetch content-type or size
    validation because trafilatura.fetch_url() handles the HTTP fetch
    internally. For validation before extraction, use HttpxFetcher instead.

    This is the canonical implementation - use this class instead of
    the deprecated fetch_with_trafilatura() function.
    """

    name = "trafilatura"
    version = "1.0.0"
    url_patterns = ["*"]
    requires_env: list[str] = []

    def fetch(self, url: str) -> FetchResult:
        """Fetch and extract content using Trafilatura.

        Downloads the URL using trafilatura.fetch_url() and extracts
        content using extract_with_trafilatura() from utils.

        Args:
            url: URL to fetch

        Returns:
            FetchResult with extracted content and metadata.
            On success: content contains Markdown, metadata includes
                title, author, date, description, fingerprint, engine.
            On failure: success=False, error contains description.
        """
        try:
            # Download the page using trafilatura's built-in fetcher
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return FetchResult(
                    content="",
                    metadata={"engine": "trafilatura"},
                    success=False,
                    error=f"[Trafilatura] No content from: {url}",
                )

            # Extract content and metadata using shared utility
            content, metadata = extract_with_trafilatura(downloaded, url)
            metadata["engine"] = "trafilatura"

            return FetchResult(
                content=content,
                metadata=metadata,
                success=True,
            )
        except ValueError as e:
            # ValueError from extract_with_trafilatura (no content extracted)
            return FetchResult(
                content="",
                metadata={"engine": "trafilatura"},
                success=False,
                error=str(e),
            )
        except Exception as e:
            return FetchResult(
                content="",
                metadata={"engine": "trafilatura"},
                success=False,
                error=f"[Trafilatura] Download error: {type(e).__name__}: {str(e)}",
            )

    def fetch_raw(self, url: str) -> tuple[str, dict]:
        """Fetch content and return as tuple (for backward compatibility).

        This method provides the same interface as the deprecated
        fetch_with_trafilatura() function for backward compatibility.

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
TrafilaturaEngine = TrafilaturaFetcher
