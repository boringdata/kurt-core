"""Tavily search-based content retrieval engine."""

from typing import Optional

from kurt.tools.fetch.core.base import BaseFetcher, FetcherConfig, FetchResult
from kurt.tools.fetch.tavily import fetch_with_tavily


class TavilyFetcher(BaseFetcher):
    """Retrieves content using Tavily Extract API.

    Supports single URL fetches. For batch operations (up to 20 URLs),
    use fetch_with_tavily() directly from kurt.tools.fetch.tavily.

    Requires TAVILY_API_KEY environment variable to be set.

    Note:
        The api_key constructor parameter is stored for compatibility but
        the underlying implementation reads from the environment variable.
    """

    def __init__(self, config: Optional[FetcherConfig] = None, api_key: Optional[str] = None):
        """Initialize Tavily fetcher.

        Args:
            config: Fetcher configuration
            api_key: Stored for compatibility (env var TAVILY_API_KEY is used)
        """
        super().__init__(config)
        self.api_key = api_key

    def fetch(self, url: str) -> FetchResult:
        """Fetch content using Tavily Extract API.

        Args:
            url: URL to fetch

        Returns:
            FetchResult with retrieved content
        """
        try:
            results = fetch_with_tavily(url)

            if url not in results:
                return FetchResult(
                    content="",
                    success=False,
                    error=f"[Tavily] No result for: {url}",
                    metadata={"engine": "tavily"},
                )

            result = results[url]

            # Check if result is an error
            if isinstance(result, Exception):
                return FetchResult(
                    content="",
                    success=False,
                    error=str(result),
                    metadata={"engine": "tavily"},
                )

            # Result is (content, metadata) tuple
            content, metadata = result
            metadata["engine"] = "tavily"

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
                metadata={"engine": "tavily"},
            )
        except Exception as e:
            return FetchResult(
                content="",
                success=False,
                error=f"[Tavily] Unexpected error: {type(e).__name__}: {str(e)}",
                metadata={"engine": "tavily"},
            )


# Backwards compatibility alias
TavilyEngine = TavilyFetcher
