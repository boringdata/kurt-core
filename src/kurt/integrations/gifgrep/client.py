"""
GIF search client using Tenor API.

Provides programmatic access to search for GIFs via Tenor's free API.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


class GifgrepError(Exception):
    """Base exception for gifgrep errors."""

    pass


class GifgrepRateLimitError(GifgrepError):
    """Rate limit exceeded error."""

    pass


@dataclass
class GifResult:
    """A single GIF search result."""

    id: str
    title: str
    url: str
    preview_url: str
    mp4_url: str | None
    width: int
    height: int
    tags: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "preview_url": self.preview_url,
            "mp4_url": self.mp4_url,
            "width": self.width,
            "height": self.height,
            "tags": self.tags,
        }


class GifgrepClient:
    """
    GIF search client using Tenor API.

    Usage:
        client = GifgrepClient()
        results = client.search("funny cat")
        for gif in results:
            print(gif.url)
    """

    BASE_URL = "https://tenor.googleapis.com/v2"
    # Tenor provides a free demo key for testing
    DEFAULT_API_KEY = "AIzaSyAyimkuYQYF_FXVALexPuGQctUWRURdCYQ"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        """
        Initialize GIF search client.

        Args:
            api_key: Tenor API key. Falls back to TENOR_API_KEY env var,
                     then to a public demo key.
            timeout: Request timeout in seconds.
        """
        self.api_key = (
            api_key
            or os.environ.get("TENOR_API_KEY")
            or self.DEFAULT_API_KEY
        )
        self.timeout = timeout
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Lazy-initialized httpx client."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "GifgrepClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def search(
        self,
        query: str,
        limit: int = 10,
        content_filter: str = "medium",
        locale: str = "en_US",
    ) -> list[GifResult]:
        """
        Search for GIFs by keyword.

        Args:
            query: Search query string.
            limit: Maximum number of results (1-50).
            content_filter: Content safety filter (off, low, medium, high).
            locale: Language/region code (e.g., "en_US").

        Returns:
            List of GifResult objects.

        Raises:
            GifgrepRateLimitError: If rate limit exceeded.
            GifgrepError: For other API errors.
        """
        limit = min(max(limit, 1), 50)

        params = {
            "key": self.api_key,
            "q": query,
            "limit": limit,
            "contentfilter": content_filter,
            "locale": locale,
            "media_filter": "gif,tinygif,mp4",
        }

        try:
            response = self.client.get(f"{self.BASE_URL}/search", params=params)

            if response.status_code == 429:
                raise GifgrepRateLimitError(
                    "Tenor rate limit exceeded. Try again in 30 seconds."
                )

            response.raise_for_status()
            data = response.json()

            return self._parse_results(data.get("results", []))

        except httpx.HTTPStatusError as e:
            raise GifgrepError(
                f"Tenor API error: {e.response.status_code} - {e.response.text}"
            )
        except httpx.RequestError as e:
            raise GifgrepError(f"Failed to connect to Tenor: {e}")

    def trending(
        self,
        limit: int = 10,
        content_filter: str = "medium",
        locale: str = "en_US",
    ) -> list[GifResult]:
        """
        Get trending GIFs.

        Args:
            limit: Maximum number of results (1-50).
            content_filter: Content safety filter.
            locale: Language/region code.

        Returns:
            List of GifResult objects.
        """
        limit = min(max(limit, 1), 50)

        params = {
            "key": self.api_key,
            "limit": limit,
            "contentfilter": content_filter,
            "locale": locale,
            "media_filter": "gif,tinygif,mp4",
        }

        try:
            response = self.client.get(f"{self.BASE_URL}/featured", params=params)

            if response.status_code == 429:
                raise GifgrepRateLimitError(
                    "Tenor rate limit exceeded. Try again in 30 seconds."
                )

            response.raise_for_status()
            data = response.json()

            return self._parse_results(data.get("results", []))

        except httpx.HTTPStatusError as e:
            raise GifgrepError(
                f"Tenor API error: {e.response.status_code} - {e.response.text}"
            )
        except httpx.RequestError as e:
            raise GifgrepError(f"Failed to connect to Tenor: {e}")

    def random(
        self,
        query: str,
        content_filter: str = "medium",
        locale: str = "en_US",
    ) -> GifResult | None:
        """
        Get a random GIF for a search query.

        Args:
            query: Search query string.
            content_filter: Content safety filter.
            locale: Language/region code.

        Returns:
            A single random GifResult, or None if no results.
        """
        params = {
            "key": self.api_key,
            "q": query,
            "limit": 1,
            "contentfilter": content_filter,
            "locale": locale,
            "media_filter": "gif,tinygif,mp4",
            "random": "true",
        }

        try:
            response = self.client.get(f"{self.BASE_URL}/search", params=params)

            if response.status_code == 429:
                raise GifgrepRateLimitError(
                    "Tenor rate limit exceeded. Try again in 30 seconds."
                )

            response.raise_for_status()
            data = response.json()
            results = self._parse_results(data.get("results", []))

            return results[0] if results else None

        except httpx.HTTPStatusError as e:
            raise GifgrepError(
                f"Tenor API error: {e.response.status_code} - {e.response.text}"
            )
        except httpx.RequestError as e:
            raise GifgrepError(f"Failed to connect to Tenor: {e}")

    def _parse_results(self, results: list[dict]) -> list[GifResult]:
        """Parse Tenor API results into GifResult objects."""
        parsed = []
        for item in results:
            # Get media formats
            media = item.get("media_formats", {})
            gif_media = media.get("gif", {})
            preview_media = media.get("tinygif", {}) or gif_media
            mp4_media = media.get("mp4", {})

            parsed.append(
                GifResult(
                    id=item.get("id", ""),
                    title=item.get("content_description", "") or item.get("title", ""),
                    url=gif_media.get("url", ""),
                    preview_url=preview_media.get("url", ""),
                    mp4_url=mp4_media.get("url"),
                    width=gif_media.get("dims", [0, 0])[0],
                    height=gif_media.get("dims", [0, 0])[1] if len(gif_media.get("dims", [])) > 1 else 0,
                    tags=item.get("tags", []) or [],
                )
            )

        return parsed


def search_gifs(
    query: str,
    limit: int = 10,
    api_key: str | None = None,
    content_filter: str = "medium",
) -> list[GifResult]:
    """
    Convenience function to search for GIFs.

    Args:
        query: Search query string.
        limit: Maximum number of results.
        api_key: Optional Tenor API key.
        content_filter: Content safety filter.

    Returns:
        List of GifResult objects.
    """
    with GifgrepClient(api_key=api_key) as client:
        return client.search(query, limit=limit, content_filter=content_filter)
