"""Firecrawl content extraction engine."""

from typing import Optional

from kurt.tools.fetch.core import BaseFetcher, FetcherConfig, FetchResult


class FirecrawlFetcher(BaseFetcher):
    """Extracts content using Firecrawl API.

    Supports single URL fetches. For batch operations,
    use fetch_with_firecrawl() directly from kurt.tools.fetch.firecrawl.

    Requires FIRECRAWL_API_KEY environment variable to be set.
    """

    def __init__(self, config: Optional[FetcherConfig] = None, api_key: Optional[str] = None):
        """Initialize Firecrawl fetcher.

        Args:
            config: Fetcher configuration
            api_key: Stored for compatibility (env var FIRECRAWL_API_KEY is used)
        """
        super().__init__(config)
        self.api_key = api_key

    def fetch(self, url: str) -> FetchResult:
        """Fetch and extract content using Firecrawl.

        Args:
            url: URL to fetch

        Returns:
            FetchResult with extracted content
        """
        from kurt.tools.fetch.firecrawl import fetch_with_firecrawl

        try:
            results = fetch_with_firecrawl(url)

            if url not in results:
                return FetchResult(
                    content="",
                    success=False,
                    error=f"[Firecrawl] No result for: {url}",
                    metadata={"engine": "firecrawl"},
                )

            result = results[url]

            # Check if result is an error
            if isinstance(result, Exception):
                return FetchResult(
                    content="",
                    success=False,
                    error=str(result),
                    metadata={"engine": "firecrawl"},
                )

            # Result is (content, metadata) tuple
            content, metadata = result
            metadata["engine"] = "firecrawl"

            return FetchResult(
                content=content,
                success=True,
                metadata=metadata,
            )

        except ValueError as e:
            return FetchResult(
                content="",
                success=False,
                error=str(e),
                metadata={"engine": "firecrawl"},
            )
        except Exception as e:
            return FetchResult(
                content="",
                success=False,
                error=f"[Firecrawl] Unexpected error: {type(e).__name__}: {str(e)}",
                metadata={"engine": "firecrawl"},
            )


# Backwards compatibility alias
FirecrawlEngine = FirecrawlFetcher
